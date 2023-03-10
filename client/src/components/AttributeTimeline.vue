<script lang="ts">
import {
  computed,
  ref,
  defineComponent,
  Ref,
  set as VueSet, del as VueDel,
} from '@vue/composition-api';
import AttributeKeyFilterVue from 'vue-media-annotator/components/AttributeFilter/AttributeKeyFilter.vue';
import {
  AttributeKeyFilter, TimeLineFilter, TimelineGraph, TimelineGraphSettings,
} from 'vue-media-annotator/use/useAttributes';
import { LineChartData } from 'vue-media-annotator/use/useLineChart';
import { useAttributesFilters, useAttributes } from '../provides';
import TooltipBtn from './TooltipButton.vue';


/* Magic numbers involved in height calculation */
export default defineComponent({
  name: 'AttributeTimeline',

  props: {
    height: {
      type: Number,
      default: 200,
    },
    width: {
      type: Number,
      default: 300,
    },
  },

  components: {
    TooltipBtn,
    AttributeKeyFilter: AttributeKeyFilterVue,
  },

  setup() {
    const {
      setTimelineEnabled, setTimelineGraph, removeTimelineFilter,
      timelineGraphs,
    } = useAttributesFilters();
    const attributesList = useAttributes();
    const addEditTimelineDialog = ref(false);
    const showGraphSettings = ref(false);
    const defaultTimelineFilter = {
      appliedTo: ['all'],
      active: true, // if this filter is active
      value: true,
      type: 'key' as 'key',
    };
    const editTimelineFilter: Ref<TimeLineFilter> = ref({
      appliedTo: ['all'],
      active: true, // if this filter is active
      value: true,
      type: 'key' as 'key',
    });
    const editTimelineSettings: Ref<Record<string, TimelineGraphSettings>> = ref({});
    const editTimelineEnabled = ref(false);
    const editTimelineDefault = ref(false);
    let originalName = 'default';
    let originalDefault = false;
    const editTimelineName = ref('default');
    const filterNames = computed(() => {
      const data = ['all'];
      return data.concat(attributesList.value.filter((item) => item.belongs === 'detection').map((item) => item.name));
    });
    const editingGraphSettings = ref(false);
    const addEditTimeline = (item?: TimelineGraph) => {
      addEditTimelineDialog.value = true;
      editTimelineName.value = item ? item.name : 'default';
      originalName = editTimelineName.value;
      originalDefault = item?.default || false;
      editTimelineDefault.value = originalDefault;
      editTimelineFilter.value = item ? item.filter : defaultTimelineFilter;
      editTimelineSettings.value = item && item.settings ? item.settings : {};
      editTimelineEnabled.value = item ? item.enabled : false;
      editingGraphSettings.value = false;
    };

    const saveChanges = () => {
      if (editTimelineName.value !== originalName) {
        removeTimelineFilter(originalName);
      }
      let setDefault = false;
      if (editTimelineDefault.value && editTimelineDefault.value !== originalDefault) {
        // Go through the other timelines and make sure only one is set as the default
        setDefault = true;
      }
      const updateObject = {
        name: editTimelineName.value,
        filter: editTimelineFilter.value,
        enabled: editTimelineEnabled.value,
        settings: editTimelineSettings.value,
        default: setDefault,
      };
      console.log(updateObject);
      setTimelineGraph(editTimelineName.value, updateObject);
      setTimelineEnabled(editTimelineName.value, editTimelineEnabled.value);
      addEditTimelineDialog.value = false;
    };

    const deleteFilter = (item: TimelineGraph) => {
      removeTimelineFilter(item.name);
    };
    const graphTypes = ref(['Linear', 'Step', 'StepAfter', 'StepBefore', 'Natural']);
    const graphArea = ref(false);
    const graphAreaOpacity = ref(0.2);
    const graphType: Ref<LineChartData['type']> = ref('Linear');
    const graphAreaColor = ref('');
    const graphMax = ref(false);
    const graphLineOpacity = ref(1.0);
    const editTimelineKey = ref('');
    const editGraphSettings = (key: string) => {
      // set the defaults:
      editTimelineKey.value = key;
      editingGraphSettings.value = true;
      graphType.value = 'Linear';
      graphMax.value = false;
      graphArea.value = false;
      graphAreaOpacity.value = 0.2;
      graphAreaColor.value = attributesList.value.find((item) => key === item.name)?.color || '';
      graphLineOpacity.value = 1.0;
      if (editTimelineSettings.value[key]) {
        graphType.value = editTimelineSettings.value[key].type || 'Linear';
        graphArea.value = editTimelineSettings.value[key].area || false;
        graphAreaOpacity.value = (editTimelineSettings.value[key].areaOpacity as number);
        graphAreaColor.value = editTimelineSettings.value[key].areaColor || '';
        graphMax.value = editTimelineSettings.value[key].max || false;
        graphLineOpacity.value = editTimelineSettings.value[key].lineOpacity !== undefined
          ? editTimelineSettings.value[key].lineOpacity : 1.0;
        if (graphAreaOpacity.value === undefined) {
          graphAreaOpacity.value = 0.2;
        }
      }
    };

    const saveGraphSettings = () => {
      // Don't set if default values
      if (!graphType.value && graphType.value === 'Linear') {
        if (editTimelineSettings.value && editTimelineSettings.value[editTimelineKey.value]) {
          VueDel(editTimelineSettings.value, editTimelineKey.value);
        }
      } else {
        const data: TimelineGraphSettings = {
          type: graphType.value,
          area: graphArea.value,
          areaOpacity: graphAreaOpacity.value,
          areaColor: graphAreaColor.value,
          max: graphMax.value,
          lineOpacity: graphLineOpacity.value,
        };
        editTimelineSettings.value[editTimelineKey.value] = data;
      }
      editingGraphSettings.value = false;
      showGraphSettings.value = false;
    };

    return {
      setTimelineEnabled,
      setTimelineGraph,
      editTimelineDefault,
      addEditTimelineDialog,
      editTimelineFilter,
      editTimelineName,
      editTimelineEnabled,
      filterNames,
      saveChanges,
      addEditTimeline,
      deleteFilter,
      //Graph Settings
      saveGraphSettings,
      editGraphSettings,
      editingGraphSettings,
      editTimelineSettings,
      graphType,
      graphTypes,
      graphArea,
      graphMax,
      graphAreaOpacity,
      graphLineOpacity,
      graphAreaColor,
      timelineGraphs,
      showGraphSettings,
      editTimelineKey,
    };
  },
});
</script>

<template>
  <div>
    <v-card>
      <ul>
        <li>
          Display the selected attributes numberical values in the timeline
          for the currently selected track.
        </li>
        <li>Click on the Cog wheel to change which attributes to graph.</li>
        <li>
          The attributes graph button will be displayed near the "Detections" and
          "Events" button on the timeline.
        </li>
      </ul>
      <v-card-text>
        <v-row
          v-for="item in timelineGraphs"
          :key="item.name"
          dense
        >
          <v-checkbox
            class="my-0 ml-1 pt-0 mr-2"
            dense
            hide-details
            :input-value="item.enabled"
            @click="setTimelineEnabled(item.name, !item.enabled)"
          />
          <span>{{ item.name }}</span>
          <v-spacer />
          <tooltip-btn
            icon="mdi-cog"
            size="x-small"
            tooltip-text="Edit Settings of Filter"
            @click="addEditTimeline(item)"
          />
          <tooltip-btn
            icon="mdi-delete"
            color="error"
            size="x-small"
            tooltip-text="Delete Filter"
            @click="deleteFilter(item)"
          />
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="success"
          tooltip-text="Add Filter"
          @click="addEditTimeline()"
        >
          Add Timeline
        </v-btn>
      </v-card-actions>
    </v-card>
    <v-dialog
      v-model="addEditTimelineDialog"
      width="800"
    >
      <v-card>
        <v-card-title> Add Timeline </v-card-title>
        <v-card-text>
          <v-row>
            <v-text-field
              v-model="editTimelineName"
              label="Timeline Name"
            />
          </v-row>
          <v-row>
            <v-switch
              v-model="editTimelineEnabled"
              label="Enabled"
            />
          </v-row>
          <v-row>
            <attribute-key-filter
              :attribute-filter="editTimelineFilter"
              :filter-names="filterNames"
              timeline
              @save-changes="editTimelineFilter = ($event)"
            />
          </v-row>
          <div class="mt-4">
            <h2>
              Graph Settings <v-icon @click="showGraphSettings = !showGraphSettings">
                {{ showGraphSettings ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
              </v-icon>
            </h2>
            <div
              v-if="showGraphSettings"
              class="graph-settings-area"
            >
              <v-row
                v-for="key in editTimelineFilter.appliedTo"
                :key="`graph_details_${key}`"
                class="graph-settings-list my-2"
                :class="{'selected-setting': key === editTimelineKey}"
              >
                <v-col><b>{{ key }}</b></v-col>
                <v-col
                  v-if="editTimelineSettings[key]"
                  class="graphsetting"
                >
                  <b>Type</b>:{{ editTimelineSettings[key].type }}
                </v-col>

                <v-col
                  v-if="editTimelineSettings[key]"
                  class="graphsetting"
                >
                  <b>Line %</b>:
                  {{ (editTimelineSettings[key].lineOpacity
                    ? editTimelineSettings[key].lineOpacity : 1).toFixed(2) }}
                </v-col>

                <v-col
                  v-if="editTimelineSettings[key]"
                  class="graphsetting"
                >
                  <b>Max</b>:{{ editTimelineSettings[key].max }}
                </v-col>

                <v-col
                  v-if="editTimelineSettings[key]"
                  class="graphsetting"
                >
                  <b>Area</b>:{{ editTimelineSettings[key].area }}
                </v-col>

                <v-col
                  v-if="editTimelineSettings[key]
                    && editTimelineSettings[key].area"
                  class="graphsetting"
                >
                  <b>Area %</b>:{{ editTimelineSettings[key].areaOpacity }}
                </v-col>
                <v-col
                  v-if="editTimelineSettings[key]
                    && editTimelineSettings[key].areaColor"
                  class="graphsetting"
                >
                  <b>Area col:</b>:<div
                    class="type-color-box"
                    :style="{
                      backgroundColor:editTimelineSettings[key].areaColor,
                    }"
                  />
                </v-col>

                <v-icon
                  class="mr-4"
                  @click="editGraphSettings(key)"
                >
                  mdi-cog
                </v-icon>
              </v-row>
            </div>
          </div>
          <v-card
            v-if="editingGraphSettings"
            class="editGraphCard"
          >
            <v-card-title>
              Editing Graph Line:
              <b class="pl-2"><i> {{ editTimelineKey }}</i></b>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col>
                  <v-select
                    v-model="graphType"
                    :items="graphTypes"
                    label="Graph Type"
                  />
                  <v-slider
                    v-model="graphLineOpacity"
                    :label="`Line Opacity ${graphLineOpacity.toFixed(2)}`"
                    min="0"
                    max="1"
                    step="0.01"
                  />

                  <v-checkbox
                    v-model="graphMax"
                    label="Max Graph"
                    persistent-hint
                    hint="Any value other than 0 is the Max value"
                  />
                  <v-checkbox
                    v-model="graphArea"
                    label="Graph Area"
                    persistent-hint
                    hint="Shade the area under the graph"
                  />
                  <v-slider
                    v-if="graphArea"
                    v-model="graphAreaOpacity"
                    :label="`Area Opacity ${graphAreaOpacity.toFixed(2)}`"
                    min="0"
                    max="1"
                    step="0.01"
                  />
                  <h3
                    v-if="graphArea"
                  >
                    Area Color
                  </h3>
                  <v-color-picker
                    v-if="graphArea"
                    v-model="graphAreaColor"
                    hide-inputs
                  />
                </v-col>
              </v-row>
              <v-row v-if="editingGraphSettings">
                <v-spacer />
                <v-btn
                  color="success"
                  @click="saveGraphSettings"
                >
                  Save Graph Settings
                </v-btn>
              </v-row>
            </v-card-text>
          </v-card>
          <v-row
            class="pt-2"
          >
            <p>
              One Timeline can be labeled ad the Default timeline which will
              automatically be open when loading the dataset
            </p>
            <v-switch
              v-model="editTimelineDefault"
              label="Default Visible Timeline"
              class="pa-0 ma-0"
            />
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            depressed
            text
            @click="addEditTimelineDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="saveChanges"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped lang='scss'>

.border-highlight {
   border-bottom: 1px solid gray;
 }

.type-checkbox {
  max-width: 80%;
  overflow-wrap: anywhere;
}

.hover-show-parent {
  .hover-show-child {
    display: none;
  }

  &:hover {
    .hover-show-child {
      display: inherit;
    }
  }
}
.outlined {
  background-color: gray;
  color: #222;
  font-weight: 600;
  border-radius: 6px;
  padding: 0 5px;
  font-size: 12px;
}

.graph-settings-area {
  padding: 5px;
}

.graph-settings-list{
 border: 1px solid gray;

 .selected-setting {
  background-color: darkgray;
 }
}
.graphsetting {
  font-size:0.75em;
}

.type-color-box {
    margin: 7px;
    margin-top: 4px;
    min-width: 15px;
    max-width: 15px;
    min-height: 15px;
    max-height: 15px;
}

.editGraphCard {
  border: 2px solid gray;
}
</style>
