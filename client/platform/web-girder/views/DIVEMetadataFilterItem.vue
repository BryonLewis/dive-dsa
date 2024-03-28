<script lang="ts">
import { MetadataFilterKeysItem } from 'platform/web-girder/api/divemetadata.service';
import {
  defineComponent, ref, PropType, watch, onMounted, Ref,
} from 'vue';

export default defineComponent({
  name: 'DIVEMetadataFilterItem',
  props: {
    filterItem: {
      type: Object as PropType<MetadataFilterKeysItem>,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    defaultValue: {
      type: [String, Number, Array, Boolean] as PropType<boolean | string | number | string[] | number[]>,
      default: undefined,
    },
  },
  setup(props, { emit }) {
    const set = ref(props.filterItem.set);
    const value: Ref<undefined | boolean | number | string | string[] | number[]> = ref(props.defaultValue);
    const rangeFilterEnabled = ref(false);
    const categoryLimit = ref(20);
    watch(value, () => {
      const update = {
        value: value.value,
        category: props.filterItem.category,
      };
      if (props.filterItem.category === 'categorical' && props.filterItem.count > categoryLimit.value) {
        update.category = 'search';
      }
      emit('update-value', update);
    });

    onMounted(() => {
      if (props.filterItem.category === 'numerical' && props.filterItem.range) {
        value.value = [props.filterItem.range.min, props.filterItem.range.max];
      }
    });

    return {
      set,
      value,
      rangeFilterEnabled,
      categoryLimit,
    };
  },
});
</script>

<template>
  <div class="mx-2">
    <div v-if="filterItem.category === 'categorical' && filterItem.count < categoryLimit && set">
      <v-select
        v-model="value"
        :items="set"
        multiple
        chips
        clearable
        deletable-chips
        :label="label"
      />
    </div>
    <div v-else-if="filterItem.category === 'search' || (filterItem.category === 'categorical' && filterItem.count >= categoryLimit)">
      <v-text-field v-model="value" :label="label" />
    </div>
    <div v-else-if="filterItem.category === 'boolean'">
      <v-checkbox v-model="value" :label="label" />
    </div>
    <div v-else-if="filterItem.category === 'numerical' && filterItem.range">
      <v-range-slider
        v-model="value"
        :min="filterItem.range.min"
        :max="filterItem.range.max"
        :label="label"
        style="min-width: 250px;"
        thumb-label="always"
        class="pt-7"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
</style>
