<script lang="ts">
import {
  DIVEMetadataFilter, MetadataFilterItem, DIVEMetadataFilterValueResults, getMetadataFilterValues, FilterDisplayConfig,
} from 'platform/web-girder/api/divemetadata.service';
import {
  computed, defineComponent, onBeforeMount, PropType, Ref, ref, watch,
} from 'vue';
import DIVEMetadataFilterItemVue from './DIVEMetadataFilterItem.vue';
import DIVEMetadataCloneVue from './DIVEMetadataClone.vue';

export default defineComponent({
  name: 'DIVEMetadataFilter',
  components: { DIVEMetadataFilterItemVue, DIVEMetadataCloneVue },
  props: {
    currentPage: {
      type: Number,
      default: 0,
    },
    totalPages: {
      type: Number,
      default: 0,
    },
    id: {
      type: String,
      default: '',
    },
    displayConfig: {
      type: Object as PropType<FilterDisplayConfig>,
      required: true,
    },
    rootFilter: {
      type: Object as PropType<DIVEMetadataFilter>,
      default: () => {},

    },
  },
  setup(props, { emit }) {
    const search = ref(props.rootFilter.search || '');
    const filters: Ref<DIVEMetadataFilterValueResults['metadataKeys']> = ref({});
    const splitFilters = computed(() => {
      const advanced: DIVEMetadataFilterValueResults['metadataKeys'] = {};
      const displayed: DIVEMetadataFilterValueResults['metadataKeys'] = {};
      Object.entries(filters.value).forEach(([key, item]) => {
        if (props.displayConfig.display.includes(key)) {
          displayed[key] = item;
        } else if (!props.displayConfig.hide.includes(key)) {
          advanced[key] = item;
        }
      });
      return { advanced, displayed };
    });
    const filtersOn = ref(false);
    const currentFilter: Ref<DIVEMetadataFilter> = ref({});
    const pageList = computed(() => {
      const list = [];
      for (let i = 0; i < props.totalPages; i += 1) {
        list.push(i + 1);
      }
      return list;
    });

    const getFilters = async () => {
      const filterData = await getMetadataFilterValues(props.id);
      filters.value = filterData.data.metadataKeys;
    };
    onBeforeMount(async () => {
      await getFilters();
      loadCurrentFilter();
    });

    const loadCurrentFilter = () => {
      if (props.rootFilter.metadataFilters && Object.keys(props.rootFilter.metadataFilters).length) {
        currentFilter.value = props.rootFilter.metadataFilters;
      }
      if (props.rootFilter.search) {
        search.value = props.rootFilter.search;
      }
    };

    watch(() => props.rootFilter, () => {
      loadCurrentFilter();
    });

    watch(search, () => {
      currentFilter.value.search = search.value;
      emit('updateFilters', currentFilter.value);
    });

    const updateFilter = (key: string, { value, category } : {value: string | string[] | number | boolean | number[], category: MetadataFilterItem['category']}) => {
      if (!currentFilter.value.metadataFilters) {
        currentFilter.value.metadataFilters = {};
      }
      if (value === '' || (Array.isArray(value) && value.length === 0)) {
        if (currentFilter.value.metadataFilters && currentFilter.value.metadataFilters[key]) {
          delete currentFilter.value.metadataFilters[key];
        }
      } else if (category === 'numerical') {
        currentFilter.value.metadataFilters[key] = {
          category,
          range: value as [number, number],
        };
      } else {
        currentFilter.value.metadataFilters[key] = {
          category,
          value,
        };
      }

      emit('updateFilters', currentFilter.value);
    };

    const changePage = async (page: number) => {
      emit('update:currentPage', page - 1);
    };

    const getDefaultValue = (key: string) => {
      if (props.rootFilter?.metadataFilters && props.rootFilter.metadataFilters[key]) {
        return props.rootFilter.metadataFilters[key].value;
      }
      return undefined;
    };

    return {

      pageList,
      filters,
      splitFilters,
      filtersOn,
      search,
      currentFilter,
      changePage,
      updateFilter,
      getDefaultValue,
    };
  },
});
</script>

<template>
  <v-card class="pb-2">
    <v-container>
      <v-row>
        <v-btn
          class="ma-1 pa-0"
          :depressed="filtersOn"
          outlined
          :color="filtersOn ? 'success' : ''"
          text
          x-small
          @click.stop.prevent="filtersOn = !filtersOn"
        >
          <v-icon
            left
            class="mx-1"
          >
            mdi-filter
          </v-icon>
          Advanced Filters
        </v-btn>
      </v-row>
      <v-row
        no-wrap
        class="mt-3 mx-2"
      >
        <v-text-field
          v-model="search"
          label="search"
          clearable
          @change="updateFilter"
        />
      </v-row>
      <v-row
        no-wrap
        class="mt-3 mx-2"
      >
        <v-spacer />
        <div v-for="(filterItem, key) in splitFilters.displayed" :key="`filterItem_${key}`">
          <DIVEMetadataFilterItemVue :label="key" :default-value="getDefaultValue(key)" :filter-item="filterItem" @update-value="updateFilter(key, $event)" />
        </div>
        <v-spacer />
      </v-row>
      <v-row
        v-if="filtersOn"
        no-wrap
        class="
          mt-3"
      >
        <div v-for="(filterItem, key) in splitFilters.advanced" :key="`filterItem_${key}`">
          <DIVEMetadataFilterItemVue :label="key" :default-value="getDefaultValue(key)" :filter-item="filterItem" @update-value="updateFilter(key, $event, filterItem.category)" />
        </div>
      </v-row>
      <v-row class="mt-3">
        <slot name="leftOptions" />
        <v-spacer />
        <v-select
          class="mx-2 pa-0 fit"
          style="max-width: 50px"
          x-small
          :items="pageList"
          :value="currentPage + 1"
          dense
          label="Page"
          hide-details
          @change="changePage"
        />
      </v-row>
      <slot name="additionalOptions" />
    </v-container>
  </v-card>
</template>

<style scoped lang="scss">

</style>
