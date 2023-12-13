<script lang="ts">
import {
  computed, defineComponent, onBeforeUnmount, onMounted, ref, toRef, watch, Ref,
} from 'vue';

import Viewer from 'dive-common/components/Viewer.vue';
import NavigationTitle from 'dive-common/components/NavigationTitle.vue';
import ImportAnnotations from 'dive-common/components/ImportAnnotations.vue';
import DIVETools from 'dive-common/components/DIVETools.vue';
import SidebarContext from 'dive-common/components/SidebarContext.vue';
import context from 'dive-common/store/context';
import { useStore } from 'platform/web-girder/store/types';
import { usePrompt } from 'dive-common/vue-utilities/prompt-service';
import ConfigurationEditor from 'dive-common/components/ConfigurationEditor.vue';
import { UISettingsKey } from 'vue-media-annotator/ConfigurationManager';

import { useRouter } from 'vue-router/composables';
import { GirderSlicerTaskButton, GirderSlicerTaskCard } from '@bryonlewis/vue-girder-slicer-cli-ui';
import JobsTab from './JobsTab.vue';
import Export from './Export.vue';
import Clone from './Clone.vue';
import ViewerAlert from './ViewerAlert.vue';
import RevisionHistory from './RevisionHistory.vue';
import AnnotationDataBrowser from './AnnotationDataBrowser.vue';

const buttonOptions = {
  text: true,
  color: 'grey lighten-1',
  outlined: true,
  depressed: true,
  class: ['mx-1'],
};

const menuOptions = {
  offsetY: true,
  bottom: true,
};

context.register({
  component: RevisionHistory,
  description: 'Revision History',
});
context.register({
  component: GirderSlicerTaskCard,
  description: 'Slicer Tasks',
});

/**
 * ViewerLoader is responsible for loading
 * data from girder.
 */
export default defineComponent({
  components: {
    Clone,
    Export,
    JobsTab,
    NavigationTitle,
    Viewer,
    ImportAnnotations,
    RevisionHistory,
    SidebarContext,
    ViewerAlert,
    DIVETools,
    ConfigurationEditor,
    AnnotationDataBrowser,
    GirderSlicerTaskButton,
    ...context.getComponents(),
  },

  // TODO: This will require an import from vue-router for Vue3 compatibility
  async beforeRouteLeave(to, from, next) {
    if (await this.viewerRef.navigateAwayGuard()) {
      next();
    }
  },

  props: {
    id: {
      type: String,
      required: true,
    },
    revision: {
      type: String,
      default: undefined,
    },
  },

  setup(props) {
    const router = useRouter();
    const { prompt } = usePrompt();
    const viewerRef = ref();
    const store = useStore();
    const brandData = toRef(store.state.Brand, 'brandData');
    const revisionNum = computed(() => {
      const parsed = Number.parseInt(props.revision, 10);
      if (Number.isNaN(parsed)) return undefined;
      return parsed;
    });
    const { getters } = store;
    const currentJob = computed(() => getters['Jobs/datasetCompleteJobs'](props.id));
    const runningPipelines = computed(() => {
      const results: string[] = [];
      if (getters['Jobs/datasetRunningState'](props.id)) {
        results.push(props.id);
      }
      return results;
    });

    if (props.revision) {
      /* When a revision is loaded, toggle the revision history on */
      context.state.active = 'RevisionHistory';
    }

    watch(currentJob, async () => {
      if (currentJob.value !== false && currentJob.value !== undefined) {
        if (currentJob.value.success) {
          const result = await prompt({
            title: 'Pipeline Finished',
            text: [`Pipeline: ${currentJob.value.title}`,
              'finished running on the current dataset.  Click reload to load the annotations.  The current annotations will be replaced with the pipeline output.',
            ],
            confirm: true,
            positiveButton: 'Reload',
            negativeButton: '',
          });
          store.dispatch('Jobs/removeCompleteJob', { datasetId: props.id });
          if (result) {
            viewerRef.value.reloadAnnotations();
          }
        } else {
          await prompt({
            title: 'Pipeline Incomplete',
            text: [`Pipeline: ${currentJob.value.title}`,
              'either failed or was cancelled by the user',
            ],
          });
          store.dispatch('Jobs/removeCompleteJob', { datasetId: props.id });
        }
      }
    });

    onMounted(() => {
      window.addEventListener('beforeunload', viewerRef.value.warnBrowserExit);
    });

    onBeforeUnmount(() => {
      window.removeEventListener('beforeunload', viewerRef.value.warnBrowserExit);
    });

    function routeRevision(revisionId: number) {
      router.replace({
        name: 'revision viewer',
        params: { id: props.id, revision: revisionId.toString() },
      });
    }
    const configMan: Ref<Record<UISettingsKey | string,
    boolean | boolean[] | undefined> | null> = ref(null);
    const enabledUISettings = (map: Record<UISettingsKey | string,
    boolean | boolean[] | undefined>) => {
      configMan.value = map;
    };

    const getSetting = (key: UISettingsKey) => {
      if (configMan.value) {
        if (configMan.value[key] === undefined) {
          return true;
        }
        return configMan.value[key];
      }
      return true;
    };
    const enabledFeatures = computed(() => {
      if (configMan.value !== null) {
        const retData = {
          data: getSetting('UIData'),
          jobs: getSetting('UIJobs'),
          toolbox: getSetting('UIToolBox'),
          import: getSetting('UIImport'),
          export: getSetting('UIExport'),
          clone: getSetting('UIClone'),
        };
        return retData;
      }
      return {
        data: false,
        jobs: false,
        toolbox: false,
        import: false,
        export: false,
        clone: false,

      };
    });

    return {
      buttonOptions,
      brandData,
      context,
      menuOptions,
      revisionNum,
      viewerRef,
      getters,
      currentJob,
      runningPipelines,
      routeRevision,
      enabledFeatures,
      enabledUISettings,
      store,
    };
  },
});
</script>

<template>
  <Viewer
    :id="id"
    :key="id"
    ref="viewerRef"
    :revision="revisionNum"
    :read-only-mode="!!getters['Jobs/datasetRunningState'](id)"
    @get-ui-settings="enabledUISettings($event)"
  >
    <template #title>
      <ViewerAlert />
      <NavigationTitle :name="brandData.name" />
      <v-tabs
        icons-and-text
        hide-slider
        class="mx-2"
        style="flex-basis:0; flex-grow:0;"
      >
        <v-tab
          v-if="enabledFeatures.data"
          :to="getters['Location/locationRoute']"
        >
          Data
          <v-icon>mdi-database</v-icon>
        </v-tab>
        <JobsTab v-if="enabledFeatures.jobs" />
      </v-tabs>
    </template>
    <template #prevnextmiddle>
      <annotation-data-browser
        :dataset-id="id"
      />
    </template>
    <template #title-right>
      <GirderSlicerTaskButton style="z-index:9999999" />
      <DIVETools
        v-if="enabledFeatures['toolbox']"
        :button-options="buttonOptions"
        :menu-options="menuOptions"
      />
      <ImportAnnotations
        v-if="enabledFeatures['import']"
        :button-options="buttonOptions"
        :menu-options="menuOptions"
        :read-only-mode="!!getters['Jobs/datasetRunningState'](id) || revisionNum !== undefined"
        :dataset-id="id"
        block-on-unsaved
      />
      <Export
        v-if="enabledFeatures['export']"
        v-bind="{ buttonOptions, menuOptions }"
        :dataset-ids="[id]"
        block-on-unsaved
      />
      <Clone
        v-if="store.state.Dataset.meta && enabledFeatures['clone']"
        v-bind="{ buttonOptions, menuOptions }"
        :dataset-id="id"
        :revision="revisionNum"
      />
      <ConfigurationEditor
        :button-options="buttonOptions"
        :menu-options="menuOptions"
      />
    </template>
    <template #right-sidebar>
      <SidebarContext>
        <template #default="{ name, subCategory }">
          <component
            :is="name"
            :sub-category="subCategory"
            @update:revision="routeRevision"
          />
        </template>
      </SidebarContext>
    </template>
  </Viewer>
</template>
