from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator
from typing_extensions import Literal

from dive_utils import constants


class PydanticObjectId(str):
    """https://stackoverflow.com/a/69431643"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return ObjectId(v)


class GeoJSONGeometry(BaseModel):
    type: str
    # support point, line, or polygon,
    coordinates: Union[List[float], List[List[float]], List[List[List[float]]]]


class GeoJSONFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: Dict[str, Union[bool, float, str]]


class GeoJSONFeatureCollection(BaseModel):
    type: str
    features: List[GeoJSONFeature]


class Feature(BaseModel):
    """Feature represents a single detection in a track."""

    frame: int
    flick: Optional[int]
    bounds: List[int]
    attributes: Optional[Dict[str, Any]] = {}
    geometry: Optional[GeoJSONFeatureCollection] = None
    head: Optional[Tuple[float, float]] = None
    tail: Optional[Tuple[float, float]] = None
    fishLength: Optional[float] = None
    interpolate: Optional[bool] = None
    keyframe: Optional[bool] = None


class BaseAnnotation(BaseModel):
    begin: Optional[int]
    end: Optional[int]
    id: int
    confidencePairs: List[Tuple[str, float]] = Field(default_factory=lambda: [])
    attributes: Dict[str, Any] = Field(default_factory=lambda: {})
    meta: Optional[Dict[str, Any]]

    def exceeds_thresholds(self, thresholds: Dict[str, float]) -> bool:
        defaultThresh = thresholds.get('default', 0)
        return any(
            [
                confidence >= thresholds.get(field, defaultThresh)
                for field, confidence in self.confidencePairs
            ]
        )

    def __hash__(self):
        return self.id


class Track(BaseAnnotation):
    begin: int
    end: int
    features: List[Feature] = Field(default_factory=lambda: [])

    @validator('features')
    @classmethod
    def validateFeatures(cls, v: List[Feature], values: dict):
        if len(v) > 0:
            trackId = values.get('id')
            begin = values.get('begin')
            end = values.get('end')
            if v[0].frame != begin:
                raise ValueError(
                    f'trackId={trackId} begin={begin} does not match features[0]={v[0].frame}'
                )
            if v[-1].frame != end:
                raise ValueError(
                    f'trackId={trackId} end={end} does not match features[-1]={v[-1].frame}'
                )
        return v


class GroupMember(BaseModel):
    ranges: List[List[int]]


class Group(BaseAnnotation):
    # Mongo keys must be strings, but the members key is an int.
    # The client is responsible for converting it.
    members: Dict[str, GroupMember]


class TrackItemSchema(Track):
    dataset: PydanticObjectId
    rev_created: int = 0
    rev_deleted: Optional[int]


class GroupItemSchema(Group):
    dataset: PydanticObjectId
    rev_created: int = 0
    rev_deleted: Optional[int]


class RevisionLog(BaseModel):
    dataset: PydanticObjectId
    author_id: PydanticObjectId
    author_name: str
    revision: int
    additions: int = 0
    deletions: int = 0
    created: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str]


class ShortcutAttributeOptions(BaseModel):
    key: str  # keyboard key
    modifiers: Optional[List[str]]
    value: Union[str, float, bool]
    description: Optional[str]
    type: Literal['set', 'dialog', 'remove']


class NumericAttributeOptions(BaseModel):
    type: Literal['combo', 'slider']
    range: Optional[List[float]]
    steps: Optional[float]


class StringAttributeOptions(BaseModel):
    type: Literal['locked', 'freeform']


class Attribute(BaseModel):
    belongs: Literal['track', 'detection']
    datatype: Literal['text', 'number', 'boolean']
    values: Optional[List[str]]
    name: str
    key: str
    color: Optional[str]
    editor: Optional[Union[NumericAttributeOptions, StringAttributeOptions]]
    shortcuts: Optional[List[ShortcutAttributeOptions]]

class AttributeNumberFilter(BaseModel):
    type: Literal['range', 'top']
    comp: Literal['>' ,'<', '>=', '<=']
    value: float
    active: bool
    range: List[float]
    appliedTo: List[str]

class AttributeKeyFilter(BaseModel):
    appliedTo: List[str]
    active: bool
    value: bool
    type: Literal['key']

class AttributeBoolFilter(BaseModel):
    value: bool
    type: Literal['is', 'not']
    appliedTo: List[str]
    active: bool

class AttributeStringFilter(BaseModel):
    comp: Literal['=', '!=', 'contains', 'starts']
    value: List[str]
    appliedTo: List[str]
    active: bool


class AttributeFilter(BaseModel):
    belongsTo: Literal['track', 'detection']
    dataType: Literal['text', 'number', 'boolean', 'key']
    filterData: Union[AttributeKeyFilter, AttributeStringFilter, AttributeBoolFilter, AttributeNumberFilter]

class TimeLineGraph(BaseModel):
    enabled: bool
    name: str
    filter: AttributeKeyFilter
    default: Optional[bool]

class CustomStyle(BaseModel):
    color: Optional[str]
    strokeWidth: Optional[float]
    opacity: Optional[float]
    fill: Optional[bool]
    showLabel: Optional[bool]
    showConfidence: Optional[bool]

class ConfigurationSettings(BaseModel):
    addTypes: Optional[bool]
    editTypes: Optional[bool]
    addTracks: Optional[bool]
    editTracks: Optional[bool]
    addTrackAttributes: Optional[bool]
    editTrackAttributes: Optional[bool]
    addDetectionAttributes: Optional[bool]
    editDetectionAttributes: Optional[bool]


class GeneralSettings(BaseModel):
    configurationMerge: Optional[Literal['merge up', 'merge down', 'disabled']]
    baseConfiguration: Optional[str]  # the folderId to use as the current write to configuration
    disableConfigurationEditing: Optional[bool]
    configurationSettings: Optional[ConfigurationSettings]


class UITopBar(BaseModel):
    UIData: Optional[bool]
    UIJobs: Optional[bool]
    UINextPrev: Optional[bool]
    UIToolBox: Optional[bool]
    UIImport: Optional[bool]
    UIExport: Optional[bool]
    UIClone: Optional[bool]
    UIConfiguration: Optional[bool]
    UIKeyboardShortcuts: Optional[bool]
    UISave: Optional[bool]

class UIToolBar(BaseModel):
    UIEditingInfo: Optional[bool]
    UIEditingTypes: Optional[List[bool]]  # Rectangle, Polygon, Line by default
    UIVisibility: Optional[List[bool]]  # Rectnagle, Polygon, Line by default
    UITrackTrails: Optional[bool]

class UISideBar(BaseModel):
    UITrackTypes: Optional[bool]
    UIConfidenceThreshold: Optional[bool]
    UITrackList: Optional[bool]
    UITrackDetails: Optional[bool]
    UIAttributeSettings: Optional[bool]
    UIAttributeAdding: Optional[bool]

class UIContextBar(BaseModel):
    UIThresholdControls: Optional[bool]
    UIImageEnhancements: Optional[bool]
    UIGroupManager: Optional[bool]
    UIAttributeDetails: Optional[bool]
    UIRevisionHistory: Optional[bool]

class UITrackDetails(BaseModel):
    UITrackBrowser: Optional[bool]
    UITrackMerge: Optional[bool]
    UIConfidencePairs: Optional[bool]
    UITrackAttributes: Optional[bool]
    UIDetectionAttributes: Optional[bool]

class UIControls(BaseModel):
    UIPlaybackControls: Optional[bool]
    UIAudioControls: Optional[bool]
    UISpeedControls: Optional[bool]
    UITimeDisplay: Optional[bool]
    UIFrameDisplay: Optional[bool]
    UIImageNameDisplay: Optional[bool]
    UILockCamera: Optional[bool]

class UITimeline(BaseModel):
    UIDetections: Optional[bool]
    UIEvents: Optional[bool]

class UISettings(BaseModel):
    UITopBar: Optional[Union[bool, UITopBar]]
    UIToolBar: Optional[Union[bool, UIToolBar]]
    UISideBar: Optional[Union[bool, UISideBar]]
    UIContextBar: Optional[Union[bool, UIContextBar]]
    UITrackDetails: Optional[Union[bool, UITrackDetails]]
    UIControls: Optional[Union[bool, UIControls]]
    UITimeline: Optional[Union[bool, UITimeline]]


class DIVEConfiguration(BaseModel):
    general: Optional[GeneralSettings]
    UISettings: Optional[UISettings]


class MetadataMutable(BaseModel):
    version = (
        constants.JsonMetaCurrentVersion
    )  # maintain compatibility with desktop for the subset of fields that overlap.
    customTypeStyling: Optional[Dict[str, CustomStyle]]
    customGroupStyling: Optional[Dict[str, CustomStyle]]
    confidenceFilters: Optional[Dict[str, float]]
    attributes: Optional[Dict[str, Attribute]]
    timelines: Optional[Dict[str, TimeLineGraph]]
    filters: Optional[Dict[str, AttributeFilter]]
    configuration: Optional[DIVEConfiguration]

    @staticmethod
    def is_dive_configuration(value: dict):
        """
        Check if value is a configuration file if at lease one of the config options is populated
        """
        keys = list(MetadataMutable.schema()['properties'].keys())

        # Remove version: its appearance is not enough to indicate that
        # the value is actually a configuration object.
        keys.remove("version")

        return any([value.get(key, False) for key in keys])


class GirderMetadataStatic(MetadataMutable):
    # Required
    id: str
    name: str
    createdAt: str
    type: str
    # Casting order matters, float first, then fall back to int
    fps: Union[float, int]
    annotate: bool

    # Optional
    # Casting order matters, float first, then fall back to int
    originalFps: Optional[Union[float, int]]
    ffprobe_info: Optional[Dict[str, Any]]
    foreign_media_id: Optional[str]


class MediaResource(BaseModel):
    url: str
    id: str
    filename: str


class DatasetSourceMedia(BaseModel):
    imageData: List[MediaResource]
    video: Optional[MediaResource]


class PrivateQueueEnabledResponse(BaseModel):
    enabled: bool
    token: Optional[dict]


class CocoMetadata(BaseModel):
    categories: Dict[int, dict]
    keypoint_categories: Dict[int, dict]
    images: Dict[int, dict]
    videos: Dict[int, dict]


class BrandData(BaseModel):
    vuetify: Optional[dict]
    favicon: Optional[str]
    logo: Optional[str]
    name: Optional[str]
    loginMessage: Optional[str]
    alertMessage: Optional[str]
    trainingMessage: Optional[str]

    class Config:
        extra = 'forbid'


# interpolate all features [a, b)
def interpolate(a: Feature, b: Feature) -> List[Feature]:
    if a.interpolate is False:
        raise ValueError('Cannot interpolate feature without interpolate enabled')
    if b.frame <= a.frame:
        raise ValueError('b.frame must be larger than a.frame')
    feature_list = [a]
    frame_range = b.frame - a.frame
    for frame in range(1, frame_range):
        delta = frame / frame_range
        inverse_delta = 1 - delta
        bounds: List[float] = [
            round((abox * inverse_delta) + (bbox * delta))
            for (abox, bbox) in zip(a.bounds, b.bounds)
        ]
        feature_list.append(Feature(frame=a.frame + frame, bounds=bounds, keyframe=False))
    return feature_list
