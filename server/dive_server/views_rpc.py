from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item

from dive_utils import asbool, fromMeta
from dive_utils.constants import DatasetMarker, FPSMarker, MarkForPostProcess, TypeMarker

from . import crud_rpc


class RpcResource(Resource):
    """Remote procedure calls to celery and other non-RESTful operations"""

    def __init__(self, resourceName):
        super(RpcResource, self).__init__()
        self.resourceName = resourceName
        self.route("POST", ("postprocess", ":id"), self.postprocess)
        self.route("POST", ("convert_dive", ":id"), self.convert_dive)
        self.route("POST", ("batch_postprocess", ":id"), self.batch_postprocess)

    @access.user
    @autoDescribeRoute(
        Description("Post-processing to be run after media/annotation import")
        .modelParam(
            "id",
            description="Folder containing the items to process",
            model=Folder,
            level=AccessType.WRITE,
        )
        .param(
            "skipJobs",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "skipTranscoding",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "additive",
            "Whether to add new annotations to existing ones",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "additivePrepend",
            "When using additive the prepend to types: 'prepend_type'",
            paramType="formData",
            dataType="string",
            default='',
            required=False,
        )
    )
    def postprocess(self, folder, skipJobs, skipTranscoding, additive, additivePrepend):
        return crud_rpc.postprocess(
            self.getCurrentUser(), folder, skipJobs, skipTranscoding, additive, additivePrepend
        )

    @access.user
    @autoDescribeRoute(
        Description("Post-processing to be run after media/annotation import")
        .modelParam(
            "id",
            description="Item ID containing the file to process",
            model=Item,
            level=AccessType.WRITE,
        )
        .param(
            "skipJobs",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "skipTranscoding",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=True,
            required=False,
        )
    )
    def convert_dive(self, item, skipJobs, skipTranscoding):
        # Get the parent folder and create a new subFolder then move the item into that folder.
        parentFolder = Folder().findOne({"_id": item["folderId"]})
        user = self.getCurrentUser()
        if parentFolder:
            foldername = f'Video {item["name"]}'
            destFolder = Folder().createFolder(
                parentFolder, foldername, creator=user, reuseExisting=True
            )
            Item().move(item, destFolder)
            if not asbool(fromMeta(destFolder, DatasetMarker)):
                destFolder["meta"].update(
                    {
                        TypeMarker: 'video',
                        FPSMarker: -1,  # auto calculate the FPS from import
                    }
                )
                Folder().save(destFolder)
                crud_rpc.postprocess(self.getCurrentUser(), destFolder, skipJobs, skipTranscoding)
            return str(destFolder['_id'])
        return ''

    def get_marked_for_postprocess(self, folder, user, datasets, limit):
        subFolders = list(Folder().childFolders(folder, 'folder', user))
        for child in subFolders:
            if child.get('meta', {}).get(MarkForPostProcess, False):
                if len(datasets) < limit:
                    datasets.append(child)
                else:
                    return
            self.get_marked_for_postprocess(child, user, datasets, limit)

    @access.user
    @autoDescribeRoute(
        Description("Post-processing for after S3 Imports")
        .modelParam(
            "id",
            description="Folder containing the items to process",
            model=Folder,
            level=AccessType.WRITE,
        )
        .param(
            "skipJobs",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "skipTranscoding",
            "Whether to skip processing that might dispatch worker jobs",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "limit",
            "Number of Jobs to start to attempt to convert to DIVE format",
            paramType="formData",
            dataType="integer",
            default=100,
            required=False,
        )
    )
    def batch_postprocess(self, folder, skipJobs, skipTranscoding, limit):
        # get a list of possible Datasets
        datasets = []
        self.get_marked_for_postprocess(folder, self.getCurrentUser(), datasets, limit)
        for subFolder in datasets:
            Folder().save(subFolder)
            crud_rpc.postprocess(self.getCurrentUser(), subFolder, skipJobs, skipTranscoding)
