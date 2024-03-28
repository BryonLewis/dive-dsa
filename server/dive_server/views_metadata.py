import json
import re
import math
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.file import File
from girder.exceptions import RestException
from girder.utility import path as path_util
import pymongo

from dive_utils import TRUTHY_META_VALUES, FALSY_META_VALUES
from dive_utils.constants import jsonRegex, ndjsonRegex, DIVEMetadataMarker, DIVEMetadataFilter, DIVEMetadataClonedFilter, DIVEMetadataClonedFilterBase
from dive_utils.metadata.models import DIVE_Metadata, DIVE_MetadataKeys
from . import crud_dataset


def python_to_javascript_type(py_type):
    type_mapping = {
        int: "number",
        float: "number",
        str: "string",
        list: "array",
        dict: "object",
        bool: "boolean",
        tuple: "array",  # You can map tuple to array, as JavaScript
        # doesn't have a built-in tuple type
        # Add more mappings as needed for other types
    }
    return type_mapping.get(py_type, "unknown")


def remove_before_folder(path, folder_name):
    index = path.find(folder_name)
    if index != -1:
        return path[index:]
    else:
        return None


def find_folder_by_path(folder, sibling_path, user):
    components = sibling_path.split('/')
    current_folder = folder
    for component in components:
        found = False
        current_folders = list(Folder().childFolders(current_folder, 'folder', user=user))
        for subfolder in current_folders:
            if subfolder['name'] == component:
                current_folder = subfolder
                found = True
        if not found:
            return None
    return current_folder


def load_ndjson_string(ndjson_string):
    # Split the string into lines and parse each line as JSON
    return [json.loads(line) for line in ndjson_string.splitlines()]


def load_metadata_json(search_folder, type='ndjson'):
    regex = ndjsonRegex
    if type == 'json':
        regex = jsonRegex
    json_items = list(
        Folder().childItems(
            search_folder,
            filters={"lowerName": {"$regex": regex}},
            sort=[("created", pymongo.ASCENDING)],
        )
    )
    if len(json_items) > 0:
        json_import_item = json_items[0]
        file = next(Item().childFiles(json_import_item), None)
        # Now lets convert the XML to TrackJSON
        if file is None:
            return None
        file_generator = File().download(file, headers=False)()
        file_string = b"".join(list(file_generator)).decode()
        json_data = {}
        if type == 'json':
            json_data = json.loads(file_string)
        elif type == 'ndjson':
            json_data = load_ndjson_string(file_string)
        # Now we determine data types from the array of data
        if not isinstance(json_data, list):
            print("JSON metadata isn't an array")
            return False
        return json_data


class DIVEMetadata(Resource):
    """DIVE Metadata processing and filtering for parent folders"""

    def __init__(self, resourceName):
        super(DIVEMetadata, self).__init__()
        self.resourceName = resourceName
        self.route("POST", ("process_metadata", ":id"), self.process_metadata)
        self.route(
            "GET",
            (
                ':id',
                "filter",
            ),
            self.filter_folder,
        )
        self.route("POST", (':id', "clone_filter"), self.clone_filter)
        self.route("GET", (':id', 'metadata_keys'), self.get_metadata_keys)
        self.route("GET", (':id', 'metadata_filter_values'), self.get_metadata_filter)
        self.route("DELETE", (':rootId',), self.delete_metadata)

    @access.user
    @autoDescribeRoute(
        Description("Processing a folder and any children folder that have a specified format")
        .modelParam(
            "id",
            description="Folder containing the items to process",
            model=Folder,
            level=AccessType.WRITE,
        )
        .param(
            "sibling_path",
            description="Sibling folder path to look for CSV or JSON files.  Uses the format of sibling/child1/child2 if more folders, if blank it will look in the root folder",
            paramType="formData",
            dataType="string",
            default='info',
            required=False,
        )
        .param(
            "fileType",
            "FileType to process if the folder is not a DIVE dataset (json, ndjson))",
            paramType="formData",
            dataType="string",
            default='ndjson',
            required=False,
        )
        .param(
            "matcher",
            "What field to match with the DIVE Dataset filename to determine the linked folderId for each row/item",
            paramType="formData",
            dataType="string",
            default="Filename",
            required=True,
        )
        .param(
            "path_key",
            "What field to match attempt to match the folder hierarchy with",
            paramType="formData",
            dataType="string",
            default="Key",
            required=True,
        )
        .jsonParam(
            "displayKeys",
            "List of Main Display Keys for the metadata and keys to hide from the filter",
            required=True,
            default={
                "display": ['Batch', 'SampleDate', 'SubjectId', 'StudyId', 'ExperimentTag'],
                "hide": ["ETag", "ETagDuplicated", "Size"],
            },
        )
    )
    def process_metadata(self, folder, sibling_path, fileType, matcher, path_key, displayKeys):
        # Process the current folder for the specified fileType using the matcher to generate DIVE_Metadata
        # make sure the folder is set to a DIVE Metadata folder using DIVE_METADATA = True
        user = self.getCurrentUser()
        # first determine the search folder for the system
        search_folder = folder
        if sibling_path:
            found_folder = find_folder_by_path(folder, sibling_path, user)
            if found_folder:
                search_folder = found_folder
        # lets first search for JSON files in the folder
        data = None
        errorLog = []
        added = 0
        if fileType in ['json', 'ndjson']:
            data = load_metadata_json(search_folder, fileType)
        if not data:
            return False
        else:
            metadataKeys = {}
            root_name = folder['name']
            for item in data:
                # need to use the matcher to try to find the DIVE dataset that matches the name

                query = {
                    '$and': [
                        {'name': {'$in': [f"Video {item[matcher]}", item[matcher]]}},
                        {"meta.annotate": {'$in': TRUTHY_META_VALUES}},
                        {"baseParentId": folder['baseParentId']},
                    ]
                }
                results = list(Folder().findWithPermissions(query=query, user=user))
                print(query)
                print(f"RESULTS LENGTH: {len(results)}")
                if len(results) > 0:
                    matched = False
                    key_path = item.get(path_key, False)
                    modified_key_path = remove_before_folder(key_path, root_name)
                    for datasetFolder in results:
                        resource_path = path_util.getResourcePath(
                            'folder', datasetFolder, user=user
                        )
                        # lets modify the path so it contains only the root folder down
                        resource_path = remove_before_folder(resource_path, root_name)
                        resource_path = resource_path.replace(
                            f'/Video {item[matcher]}', f'/{item[matcher]}'
                        )
                        # now we check to see if the path matches the DIVE dataset item found.
                        if modified_key_path:
                            if modified_key_path == resource_path:
                                item['pathMatches'] = True
                                DIVE_Metadata().createMetadata(datasetFolder, folder, user, item)
                                added += 1
                                matched = True
                            else:
                                item['pathMatches'] = False

                    if not matched:
                        errorLog.append(
                            f"using matcher: {matcher} and key_path: {key_path} Could not find any matching key file path for Video file {item[matcher]} with path: {modified_key_path}"
                        )

                else:
                    errorLog.append(f"Could not find any results for Video file {item[matcher]}")
                for key in item.keys():
                    if key not in metadataKeys.keys():
                        datatype = python_to_javascript_type(type(item[key]))
                        metadataKeys[key] = {"type": datatype, "set": set(), "count": 1}
                    if metadataKeys[key]['type'] == 'string':
                        metadataKeys[key]['set'].add(item[key])
                        metadataKeys[key]['count'] += 1
                    if metadataKeys[key]['type'] == 'array':
                        for arrayitem in item[key]:
                            if python_to_javascript_type(type(arrayitem)) == 'string':
                                metadataKeys[key]['set'].add(arrayitem)
                        metadataKeys[key]['count'] += 1
                    if metadataKeys[key]['type'] == 'number':
                        if 'range' not in metadataKeys[key].keys():
                            metadataKeys[key]['range'] = {"min": item[key], "max": item[key]}
                        metadataKeys[key]['range'] = {
                            "min": min(item[key], metadataKeys[key]["range"]["min"]),
                            "max": max(item[key], metadataKeys[key]["range"]["max"]),
                        }
            # now we need to determine what is categorical vs what is a search field
            for key in metadataKeys.keys():
                item = metadataKeys[key]
                if item["type"] in ['string', 'array'] and (
                    item["count"] < 50 or item["count"] < len(item["set"])
                ):
                    metadataKeys[key]["category"] = "categorical"
                    metadataKeys[key]['set'] = list(metadataKeys[key]['set'])
                elif item["type"] == 'string':
                    metadataKeys[key]["category"] = "search"
                    del metadataKeys[key]['set']
                elif item["type"] == 'number':
                    metadataKeys[key]["category"] = "numerical"
                    del metadataKeys[key]['set']
                else:
                    del metadataKeys[key]['set']
            DIVE_MetadataKeys().createMetadataKeys(datasetFolder, folder, user, metadataKeys)
            # add metadata to root folder for
            folder['meta'][DIVEMetadataMarker] = True
            folder['meta'][DIVEMetadataFilter] = displayKeys
            Folder().save(folder)

        return {"results": f"added {added} folders", "errors": errorLog}

    @access.user
    @autoDescribeRoute(
        Description("Get a list of filter keys for a specific folder").modelParam(
            "id",
            description="Base folder ID",
            model=Folder,
            level=AccessType.READ,
        )
    )
    def get_metadata_keys(
        self,
        folder,
    ):
        user = self.getCurrentUser()
        query = {'root': str(folder['_id'])}
        metadata_key = DIVE_MetadataKeys().findOne(
            query=query,
            user=user,
        )
        return metadata_key

    @access.user
    @autoDescribeRoute(
        Description("Filter DIVE Datasets based on metadata")
        .modelParam(
            "id",
            description="Base root Folder to filter on",
            model=Folder,
            level=AccessType.READ,
        )
        .jsonParam(
            "filters",
            "JSON Settings for the filtering",
            required=False,
        )
        .pagingParams(defaultSort='created')
    )
    def filter_folder(self, folder, filters, limit, offset, sort):
        if folder['meta'].get(DIVEMetadataMarker, False) is False:
            raise RestException('Folder is not a DIVE Metadata folder', code=404)

        user = self.getCurrentUser()
        query = self.get_filter_query(folder, user, filters)
        metadata_items = DIVE_Metadata().find(
            query, offset=offset, limit=limit, sort=sort, user=self.getCurrentUser()
        )
        if metadata_items is not None:
            pages = math.ceil(metadata_items.count() / limit)
            structured_results = {
                'totalPages': pages,
                'pageResults': list(metadata_items),
            }
            return structured_results

        return metadata_items

    @access.user
    @autoDescribeRoute(
        Description("Filter DIVE Datasets based on metadata")
        .modelParam(
            "id",
            destName="baseFolder",
            description="Base root Folder to filter on",
            model=Folder,
            level=AccessType.READ,
            required=True,
        )
        .modelParam(
            "destFolder",
            destName="destFolder",
            paramType="formData",
            description="Destination folder to clone into",
            model=Folder,
            level=AccessType.READ,
            required=True,
        )
        .jsonParam(
            "filters",
            "JSON Settings for the filtering",
            required=False,
        )
    )
    def clone_filter(
        self,
        baseFolder,
        destFolder,
        filters,
    ):
        if baseFolder['meta'].get(DIVEMetadataMarker, False) is False:
            raise RestException('Folder is not a DIVE Metadata folder', code=404)

        user = self.getCurrentUser()
        query = self.get_filter_query(baseFolder, user, filters)
        metadata_items = DIVE_Metadata().find(query, user=self.getCurrentUser())
        Folder().setMetadata(destFolder, {DIVEMetadataClonedFilter: json.dumps(filters), DIVEMetadataClonedFilterBase: baseFolder["_id"]})
        if metadata_items is not None:
            for item in list(metadata_items):
                print(item)
                item_folder = Folder().load(item['DIVEDataset'], level=AccessType.READ, user=user)
                crud_dataset.createSoftClone(
                    self.getCurrentUser(),
                    item_folder,
                    destFolder,
                    item_folder['name'],
                    None,
                )
            return str(destFolder['_id'])
        else:
            raise RestException('Filter is empty can not clone', code=404)

    def get_filter_query(self, folder, user, filters):
        query = {'root': str(folder['_id'])}
        if filters is not None:
            query = {'$and': [query]}
            if 'search' in filters.keys():
                query["$and"].append(
                    {
                        '$or': [
                            {'filename': {'$regex': re.escape(filters['search'])}},
                            {'Probes': {'$regex': re.escape(filters['search'])}},
                        ]
                    }
                )
            # Now we need to go through the other filters and create querys for them
            # each filter in metadataFilters will have a type associated with it
            if 'metadataFilters' in filters.keys():
                for key in filters['metadataFilters'].keys():
                    filter = filters['metadataFilters'][key]
                    if filter['category'] == 'categorical':
                        query["$and"].append({f'metadata.{key}': {'$in': filter['value']}})
                    if filter['category'] == 'boolean':
                        test_val = TRUTHY_META_VALUES
                        if not filter['value']:
                            test_val = FALSY_META_VALUES
                        query["$and"].append({f'metadata.{key}': {'$in': test_val}})
                    if filter['category'] == 'numerical':
                        query["$and"].append(
                            {
                                '$and': [
                                    {f'metadata.{key}': {'$gte': filter['range'][0]}},
                                    {f'metadata.{key}': {'$lte': filter['range'][1]}},
                                ]
                            }
                        )
                    if filter['category'] == 'search':
                        query["$and"].append(
                            {f'metadata.{key}': {'$regex': re.escape(filter['value'])}}
                        )
        print(query)
        return query

    @access.user
    @autoDescribeRoute(
        Description("Get a list of filter values for DIVE Metadata")
        .modelParam(
            "id",
            description="Base folder ID",
            model=Folder,
            level=AccessType.READ,
        )
        .jsonParam(
            "keys",
            "JSON keys for the filtering in an array ['key1', 'key2']",
            required=False,
        )
    )
    def get_metadata_filter(self, folder, keys=None):
        # Create initial Meva State based off of information
        query = {'root': str(folder['_id'])}
        metadata_items = list(
            DIVE_Metadata().find(
                query,
                user=self.getCurrentUser(),
            )
        )
        metadata_items.sort(key=lambda d: d["created"], reverse=True)
        # Compile a list of dates/ times and start/end Pairs
        results = {}
        if keys is not None:
            for key in keys:
                results[key] = set()
        for item in metadata_items:
            if 'metadata' in item.keys():
                for key in item['metadata'].keys():
                    print(item['metadata'][key])
                    if keys is None and key not in results.keys():
                        results[key] = set()
                    if item['metadata'].get(key, None) is not None and not isinstance(
                        item['metadata'][key], list
                    ):
                        results[key].add(item['metadata'][key])
                    elif item['metadata'].get(key, None) is not None and isinstance(
                        item['metadata'][key], list
                    ):
                        for array_item in item['metadata'][key]:
                            results[key].add(array_item)

        for key in results.keys():
            results[key] = sorted(results[key])

        return results

    @access.user
    @autoDescribeRoute(
        Description("Delete Folder VideoState").modelParam(
            "rootId",
            description="FolderId to get state from",
            model=Folder,
            level=AccessType.READ,
            destName="rootId",
        )
    )
    def delete_metadata(self, rootId):
        user = self.getCurrentUser()
        query = {"root": str(rootId["_id"])}
        found = DIVE_Metadata().findOne(query=query, user=user)
        if found:
            DIVE_Metadata().removeWithQuery(query)
            DIVE_MetadataKeys().removeWithQuery(query)
            rootId = Folder().setMetadata(
                rootId, {DIVEMetadataMarker: None, DIVEMetadataFilter: None}
            )
            Folder().save(rootId)
        else:
            raise RestException('Could not find a state to delete')
