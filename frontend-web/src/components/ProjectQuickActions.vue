<template>
  <div class="project-card__actions">
    <n-button v-if="showDetail" secondary @click="openProjectDetail">
      查看详情
    </n-button>
    <n-button v-if="showWorkspace" tertiary type="primary" @click="openWorkspace">
      去工作台
    </n-button>
    <n-button v-if="showPolish" tertiary @click="openTools('polish')">
      去润色
    </n-button>
    <n-button v-if="showContinuation" tertiary @click="openTools('continuation')">
      去续写
    </n-button>
    <n-button
      v-if="showDownload"
      :secondary="downloadSecondary"
      tertiary
      :disabled="disableDownload"
      @click="downloadProject"
    >
      下载 {{ downloadLabel }}
    </n-button>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { apiClient } from '../api'

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  downloadFormat: {
    type: String,
    default: 'txt'
  },
  disableDownload: {
    type: Boolean,
    default: false
  },
  showDetail: {
    type: Boolean,
    default: true
  },
  showWorkspace: {
    type: Boolean,
    default: true
  },
  showPolish: {
    type: Boolean,
    default: true
  },
  showContinuation: {
    type: Boolean,
    default: true
  },
  showDownload: {
    type: Boolean,
    default: true
  },
  downloadSecondary: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()

const downloadLabel = computed(() => {
  const labels = {
    txt: 'TXT',
    md: 'Markdown',
    html: 'HTML',
    docx: 'Word',
    json: 'JSON'
  }
  return labels[props.downloadFormat] || 'TXT'
})

function openProjectDetail() {
  router.push({
    name: 'ProjectDetail',
    params: { projectId: props.projectId }
  })
}

function openWorkspace() {
  router.push({
    name: 'Workspace',
    query: {
      projectId: props.projectId,
      mode: 'quick'
    }
  })
}

function openTools(tab) {
  router.push({
    name: 'Tools',
    query: {
      projectId: props.projectId,
      tab,
      autoload: '1'
    }
  })
}

function downloadProject() {
  window.open(apiClient.getProjectExportUrl(props.projectId, props.downloadFormat), '_blank', 'noopener')
}
</script>
