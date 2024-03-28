import girderRest from 'platform/web-girder/plugins/girder';
import { StringKeyObject } from 'vue-media-annotator/BaseAnnotation';

export interface MetadataFilterItem {
    category: 'search' | 'categorical' | 'numerical' | 'boolean',
    value?: boolean | string | string[] | number | number[]
    range?: number[]
}

export interface FilterDisplayConfig {
    display: string[];
    hide: string[];
}

export interface MetadataFilterKeysItem {
    category: 'search' | 'categorical' | 'numerical' | 'boolean';
    count: number;
    set?: string[] | number[];
    range?: {
        min: number,
        max: number;
    };

}

export interface DIVEMetadataFilter {
    search?: string;
    metadataFilters?: Record<string, MetadataFilterItem>;
}

export interface DIVEMetadataFilterValueResults {
    _id: string;
    created: string;
    root: string;
    metadataKeys: Record<string, MetadataFilterKeysItem>;
}

export interface DIVEMetadataResults {
    pageResults: MetadataResultItem[];
    totalPages: number;
}

export interface MetadataResultItem {
    DIVEDataset: string;
    filename: string;
    root: string;
    metadata: StringKeyObject;
}

function getMetadataFilterValues(folderId: string, keys?: string[]) {
  return girderRest.get<DIVEMetadataFilterValueResults>(`dive_metadata/${folderId}/metadata_keys`, {
    params: { keys },
  });
}

function filterDiveMetadata(folderId: string, filters: DIVEMetadataFilter, offset = 0, limit = 50, sort = 'filename', sortdir = -1) {
  return girderRest.get<DIVEMetadataResults>(`dive_metadata/${folderId}/filter`, {
    params: {
      filters, offset, limit, sort, sortdir,
    },
  });
}

function createDiveMetadataClone(folder: string, filters: DIVEMetadataFilter, destFolder: string) {
  return girderRest.post<string>(`dive_metadata/${folder}/clone_filter`, null, {
    params: {
      baseFolder: folder, filters, destFolder,
    },
  });
}

export {
  getMetadataFilterValues,
  filterDiveMetadata,
  createDiveMetadataClone,
};
