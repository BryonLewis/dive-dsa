<script lang="ts">
import {
  computed,
  defineComponent, onMounted, ref, Ref, PropType,
} from 'vue';
import {
  DIVEMetadataResults, DIVEMetadataFilter, filterDiveMetadata, MetadataResultItem, FilterDisplayConfig,
} from 'platform/web-girder/api/divemetadata.service';
import { getFolder } from 'platform/web-girder/api/girder.service';
import DIVEMetadataFilterVue from './DIVEMetadataFilter.vue';
import DIVEMetadataCloneVue from './DIVEMetadataClone.vue';

export default defineComponent({
  name: 'DIVEMetadataSearch',
  components: {
    DIVEMetadataFilterVue,
    DIVEMetadataCloneVue,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    filter: {
      type: Object as PropType<DIVEMetadataFilter>,
      default: () => { },
    },
  },
  setup(props) {
    const folderList: Ref<MetadataResultItem[]> = ref([]);
    const displayConfig: Ref<FilterDisplayConfig> = ref({ display: [], hide: [] });
    const totalPages = ref(0);
    const currentPage = ref(0);
    const filters: Ref<DIVEMetadataFilter> = ref(props.filter || {});
    const locationStore = {
      _id: props.id,
      _modelType: 'folder',
    };

    const currentFilter: Ref<DIVEMetadataFilter> = ref(props.filter || {});

    const processFilteredMetadataResults = (data: DIVEMetadataResults) => {
      folderList.value = data.pageResults;
      totalPages.value = data.totalPages;
    };
    const getData = async () => {
      const { data } = await filterDiveMetadata(props.id, { ...filters.value });
      processFilteredMetadataResults(data);
    };

    const getFolderInfo = async (id: string) => {
      const folder = (await getFolder(id)).data;
      if (folder.meta.DIVEMetadata) {
        displayConfig.value = folder.meta.DIVEMetadataFilter;
      }
    };

    onMounted(() => {
      getFolderInfo(props.id);
      getData();
    });

    const updateFilter = async (filter?: DIVEMetadataFilter) => {
      if (filter) {
        filters.value = filter;
        currentPage.value = 0;
        currentFilter.value = filter;
      }
      const sort = 'filename';
      const { data } = await filterDiveMetadata(props.id, { ...filters.value }, currentPage.value * 50, 50, sort);
      processFilteredMetadataResults(data);
    };

    const changePage = async (page: number) => {
      currentPage.value = page;
      await updateFilter();
    };

    const advanced = computed(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const advancedList: Record<string, any> = {};
      for (let i = 0; i < folderList.value.length; i += 1) {
        const item = folderList.value[i];
        Object.entries(item.metadata).forEach(([key, value]) => {
          if (!displayConfig.value.hide.includes(key)) {
            advancedList[key] = value;
          }
        });
      }
      return advancedList;
    });
    const openClone = ref(false);
    return {
      totalPages,
      currentPage,
      changePage,
      locationStore,
      updateFilter,
      folderList,
      displayConfig,
      advanced,
      filters,
      //Cloning
      openClone,
      currentFilter,
    };
  },
});
</script>

<template>
  <v-container>
    <DIVEMetadataFilterVue
      :id="id"
      :current-page="currentPage"
      :root-filter="filters"
      :total-pages="totalPages"
      :display-config="displayConfig"
      @update:currentPage="changePage($event)"
      @updateFilters="updateFilter($event)"
    >
      <template slot="leftOptions">
        <v-tooltip
          bottom
          open-delay="400"
        >
          <template #activator="{ on }">
            <v-btn
              :disabled="id === null"
              class="ml-2"
              v-on="on"
              @click="openClone = true"
            >
              <v-icon>
                mdi-content-copy
              </v-icon>
              <span
                class="pl-1 ,l-1"
              >
                Clone
              </span>
              <v-spacer />
            </v-btn>
            <v-dialog v-model="openClone" width="800">
              <DIVEMetadataCloneVue
                :base-id="id"
                :filter="currentFilter"
              />
            </v-dialog>
          </template>
          <span>Create a clone of this data</span>
        </v-tooltip>
      </template>
    </DIVEMetadataFilterVue>
    <span v-if="!openClone">
      <v-card
        v-for="(item, key) in folderList"
        :key="key"
        class="my-2 pa-2"
      >
        <v-row class="ma-4">
          <div>{{ item.filename }}</div>
          <div>
            <v-btn
              class="mx-2 mb-2"
              x-small
              color="primary"
              depressed
              :to="{ name: 'viewer', params: { id: item.DIVEDataset } }"
            >
              Launch Annotator
            </v-btn>
          </div>
        </v-row>
        <v-row v-for="display in displayConfig['display']" :key="display" class="ma-4">
          <b>{{ display }}:</b>
          <div class="mx-2">
            {{ item.metadata[display] }}
          </div>
        </v-row>
        <v-expansion-panels>
          <v-expansion-panel class="border">
            <v-expansion-panel-header>Advanced</v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row v-for="(data, dataKey) in advanced" :key="dataKey" class="border" dense>
                <v-col cols="2" class="border">
                  <b>{{ dataKey }}:</b>
                </v-col>
                <v-col cols="10">
                  <div class="mx-2">
                    {{ data }}
                  </div>
                </v-col>
                <v-spacer />
              </v-row>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>
    </span>
  </v-container>
</template>

<style scoped>
.border {
    border:1px solid white
}
.list {
    overflow-y: scroll;
}
</style>
