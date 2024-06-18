from datetime import datetime, timedelta

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.notification import Notification

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
        self.route("POST", ("ui_notification", ":id"), self.ui_notification)

    @access.user(scope=TokenScope.DATA_WRITE)
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
            "Whether to skip processing that might dispatch worker jobs.  \
            If if this is false it will skip transcoding items that have \
            already been processed indicated by having a metadata property 'codec'.",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "skipTranscoding",
            "If skipJobs is False and Skip Transcoding is true it will still \
            run a job and attempt to see if the video file meets \
            requirements (h264 encoding with .mp4 container) and \
            won't transcode unless it is necessary",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "additive",
            "Whether to add new annotations to existing ones.  Annotations \
            will be added with Ids starting at the last existing Id+1",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "additivePrepend",
            "When using additive the prepend to types: I.E. 'prepend_type' \
            so the string will be added to all types that are imported",
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
            "Whether to skip processing that might dispatch worker jobs.  \
            If if this is false it will skip transcoding items that have \
            already been processed indicated by having a metadata property 'codec'.",
            paramType="formData",
            dataType="boolean",
            default=False,
            required=False,
        )
        .param(
            "skipTranscoding",
            "If skipJobs is False and Skip Transcoding is true it will still \
            run a job and attempt to see if the video file meets \
            requirements (h264 encoding with .mp4 container) and \
            won't transcode unless it is necessary",
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


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description("Provide Notification to current User of a specific dataset")
        .modelParam(
            "id",
            description="DIVE Dataset to post noitifcation to",
            model=Folder,
            level=AccessType.READ,
        ).jsonParam(
            "body",
            "{text: string;, selectedFrame?: number, selectedTrack?: number, reloadAnnotations?: boolean }",
            paramType="body",
            requireObject=True,
            default='{"text": "Sample Notification to provide to user"}',
        )


    )
    def ui_notification(self, folder, body):

        body['datasetId'] = folder.get('_id', False),

        Notification().createNotification(
            type='ui_notification',
            data=body,
            user=self.getCurrentUser(),
            expires=datetime.now() + timedelta(seconds=300),
        )
        return 'Notification Sent'
