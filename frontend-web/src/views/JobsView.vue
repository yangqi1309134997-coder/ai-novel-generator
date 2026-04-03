<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Jobs</p>
        <h1 class="hero-title">后台任务中心</h1>
        <p class="hero-copy">
          适合提交整本小说的长耗时生成任务。任务进入后台后可以离开页面，之后回到这里查看进度、
          失败原因、项目入口和下载结果。
        </p>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">运行中任务</div>
          <div class="metric-value">{{ runningCount }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">已完成任务</div>
          <div class="metric-value">{{ completedCount }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">失败任务</div>
          <div class="metric-value">{{ failedCount }}</div>
        </div>
      </div>
    </section>

    <n-alert v-if="generationBlocked" type="warning" :show-icon="false">
      {{ authStore.generationMessage || '当前账号暂无生成权限，请联系管理员开通会员或调整平台策略。' }}
    </n-alert>

    <div class="split-grid">
      <section class="surface-card">
        <h2 class="section-heading">提交整本后台任务</h2>
        <p class="section-copy">
          任务提交后会在后台持续执行，适合正式商用场景、长流程生成和多项目并行处理。
        </p>

        <div class="stack">
          <n-input v-model:value="form.title" placeholder="小说标题" />
          <n-select v-model:value="form.genre" :options="genreOptions" placeholder="小说题材" />
          <n-input-number v-model:value="form.chapter_count" :min="10" :max="1000" />
          <n-select v-model:value="form.export_format" :options="exportOptions" placeholder="默认导出格式" />
          <n-input
            v-model:value="form.character_setting"
            type="textarea"
            :rows="4"
            placeholder="角色设定"
          />
          <n-input
            v-model:value="form.world_setting"
            type="textarea"
            :rows="4"
            placeholder="世界观设定"
          />
          <n-input
            v-model:value="form.plot_idea"
            type="textarea"
            :rows="5"
            placeholder="剧情构思"
          />

          <div class="result-actions">
            <n-button type="primary" :loading="submitting" :disabled="backendStore.unavailable || generationBlocked" @click="submitJob">
              提交后台生成
            </n-button>
            <n-button secondary @click="router.push({ name: 'Workspace' })">
              去工作台
            </n-button>
          </div>
        </div>
      </section>

      <section class="surface-card surface-card--muted">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
          <div>
            <h2 class="section-heading">任务列表</h2>
            <p class="section-copy">任务按最近更新时间排序，并每 6 秒自动刷新一次。</p>
          </div>
          <div class="result-actions">
            <n-select v-model:value="downloadFormat" :options="exportOptions" style="width:180px;" />
            <n-button secondary :disabled="backendStore.unavailable" @click="refreshJobs">手动刷新</n-button>
            <n-tag type="info">自动刷新 6s</n-tag>
          </div>
        </div>

        <div class="result-actions" style="margin-top:16px;">
          <n-input v-model:value="searchKeyword" placeholder="按任务标题搜索" clearable />
          <n-button :type="activeFilter === 'all' ? 'primary' : 'default'" @click="activeFilter = 'all'">
            全部
          </n-button>
          <n-button
            :type="activeFilter === 'running' ? 'primary' : 'default'"
            @click="activeFilter = 'running'"
          >
            进行中
          </n-button>
          <n-button
            :type="activeFilter === 'completed' ? 'primary' : 'default'"
            @click="activeFilter = 'completed'"
          >
            已完成
          </n-button>
          <n-button
            :type="activeFilter === 'failed' ? 'primary' : 'default'"
            @click="activeFilter = 'failed'"
          >
            失败
          </n-button>
        </div>

        <div v-if="filteredJobs.length" class="project-list" style="margin-top:16px;">
          <article v-for="job in filteredJobs" :key="job.id" class="project-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
              <div>
                <h3 style="margin:0; font-size:1.05rem;">{{ displayTitle(job.title, '任务') }}</h3>
                <p style="margin:8px 0 0; color:#64748b;">
                  {{ formatStatus(job.status) }} · {{ formatStep(job.current_step) }}
                </p>
              </div>
              <n-tag :type="jobStatusType(job.status)" round>{{ job.progress || 0 }}%</n-tag>
            </div>

            <div class="stack" style="margin-top:12px; gap:10px;">
              <n-progress type="line" :percentage="job.progress || 0" :show-indicator="false" />
              <div class="inline-note">
                <strong>当前提示：</strong>
                <span>{{ job.message || '等待调度' }}</span>
              </div>
              <div class="inline-note">
                <strong>创建时间：</strong>
                <span>{{ formatDate(job.created_at) }}</span>
              </div>
              <div class="inline-note">
                <strong>更新时间：</strong>
                <span>{{ formatDate(job.updated_at) }}</span>
              </div>
              <div class="inline-note">
                <strong>导出格式：</strong>
                <span>{{ (job.export_format || 'txt').toUpperCase() }}</span>
              </div>
              <div v-if="job.error" class="inline-note inline-note--warning">
                <strong>失败原因：</strong>
                <span>{{ job.error }}</span>
              </div>
            </div>

            <div class="project-card__actions">
              <n-button tertiary :disabled="backendStore.unavailable" @click="refreshSingleJob(job.id)">
                刷新状态
              </n-button>
              <n-button
                v-if="job.project_id"
                secondary
                @click="openProjectDetail(job.project_id)"
              >
                查看项目
              </n-button>
              <n-button
                v-if="job.status === 'completed' && job.project_id"
                tertiary
                @click="openTools(job.project_id, 'polish')"
              >
                去润色
              </n-button>
              <n-button
                v-if="job.status === 'completed' && job.project_id"
                tertiary
                @click="openTools(job.project_id, 'continuation')"
              >
                去续写
              </n-button>
              <n-button
                v-if="job.download_ready && job.project_id"
                type="primary"
                :disabled="backendStore.unavailable"
                @click="downloadProject(job.project_id, downloadFormat)"
              >
                下载 {{ downloadLabel }}
              </n-button>
              <n-button
                v-if="job.retry_available"
                secondary
                type="warning"
                :disabled="backendStore.unavailable || generationBlocked"
                @click="handleRetryJob(job)"
              >
                重新提交
              </n-button>
              <n-button
                v-if="job.status === 'failed' || job.status === 'completed'"
                secondary
                type="error"
                :disabled="backendStore.unavailable"
                @click="handleDeleteJob(job)"
              >
                清理任务
              </n-button>
            </div>
          </article>
        </div>

        <div v-else-if="backendStore.unavailable">
          <BackendHelpCard title="任务列表暂不可用" detail="当前无法从后端读取任务列表，请先启动后端服务。" />
        </div>

        <div v-else class="empty-state">
          当前筛选条件下没有任务记录。可以先在左侧提交一个整本后台任务。
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NInputNumber, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import { BACKEND_STATUS_EVENT, apiClient } from '../api'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'
import { isBackendAvailabilityError, notifyError } from '../utils/errors'
import BackendHelpCard from '../components/BackendHelpCard.vue'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const backendStore = useBackendStore()

const jobs = ref([])
const submitting = ref(false)
const activeFilter = ref('all')
const searchKeyword = ref('')
const downloadFormat = ref('txt')
let timer = null

const form = reactive({
  title: '',
  genre: '玄幻',
  character_setting: '',
  world_setting: '',
  plot_idea: '',
  chapter_count: 50,
  export_format: 'txt'
})

const genreOptions = [
  '玄幻', '仙侠', '武侠', '都市', '言情', '悬疑', '科幻', '历史'
].map(item => ({ label: item, value: item }))

const exportOptions = [
  { label: '文本 TXT', value: 'txt' },
  { label: 'Markdown', value: 'md' },
  { label: 'HTML', value: 'html' },
  { label: 'Word DOCX', value: 'docx' },
  { label: 'JSON', value: 'json' }
]

const downloadLabel = computed(() =>
  exportOptions.find(option => option.value === downloadFormat.value)?.label || 'TXT'
)

const runningCount = computed(() =>
  jobs.value.filter(job => job.status === 'running' || job.status === 'queued').length
)
const completedCount = computed(() => jobs.value.filter(job => job.status === 'completed').length)
const failedCount = computed(() => jobs.value.filter(job => job.status === 'failed').length)
const generationBlocked = computed(() => !authStore.canGenerate && !authStore.isBackoffice)

const filteredJobs = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  let list = [...jobs.value]

  if (activeFilter.value === 'running') {
    list = list.filter(job => job.status === 'running' || job.status === 'queued')
  } else if (activeFilter.value === 'completed') {
    list = list.filter(job => job.status === 'completed')
  } else if (activeFilter.value === 'failed') {
    list = list.filter(job => job.status === 'failed')
  }

  if (keyword) {
    list = list.filter(job => String(job.title || '').toLowerCase().includes(keyword))
  }

  return list
})

function displayTitle(title, fallbackPrefix) {
  const text = String(title || '').trim()
  if (!text || /^\?+$/.test(text)) {
    return `${fallbackPrefix}记录`
  }
  return text
}

function jobStatusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'warning'
  return 'info'
}

function formatStatus(status) {
  return {
    queued: '排队中',
    running: '生成中',
    completed: '已完成',
    failed: '已失败'
  }[status] || status
}

function formatStep(step) {
  return {
    queued: '等待队列',
    outline: '生成大纲',
    project: '创建项目',
    chapters: '生成章节',
    completed: '任务完成',
    interrupted: '任务中断',
    error: '处理异常'
  }[step] || step || '等待调度'
}

function formatDate(value) {
  if (!value) return '未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function resetForm() {
  form.title = ''
  form.genre = '玄幻'
  form.character_setting = ''
  form.world_setting = ''
  form.plot_idea = ''
  form.chapter_count = 50
  form.export_format = 'txt'
}

async function refreshJobs() {
  try {
    const response = await apiClient.listJobs()
    jobs.value = response.data || []
  } catch (error) {
    notifyError(message, error)
    if (isBackendAvailabilityError(error)) {
      stopPolling()
    }
  }
}

function startPolling() {
  if (!timer) {
    timer = window.setInterval(refreshJobs, 6000)
  }
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

function handleBackendStatusEvent(event) {
  const reachable = event?.detail?.reachable !== false
  if (!reachable) {
    stopPolling()
    return
  }

  startPolling()
}

async function refreshSingleJob(jobId) {
  try {
    const response = await apiClient.getJob(jobId)
    const next = response.data
    const idx = jobs.value.findIndex(item => item.id === jobId)
    if (idx >= 0) {
      jobs.value[idx] = next
      jobs.value = [...jobs.value]
    } else {
      jobs.value.unshift(next)
    }
  } catch (error) {
    notifyError(message, error)
  }
}

async function submitJob() {
  if (!form.title.trim()) {
    message.warning('请先填写小说标题')
    return
  }

  submitting.value = true
  try {
    const response = await apiClient.createFullGenerationJob(form)
    message.success(response.message || '后台任务已提交')
    resetForm()
    await refreshJobs()
  } catch (error) {
    notifyError(message, error)
  } finally {
    submitting.value = false
  }
}

async function handleRetryJob(job) {
  try {
    const response = await apiClient.retryJob(job.id)
    message.success(response.message || '任务已重新提交')
    await refreshJobs()
  } catch (error) {
    notifyError(message, error)
  } finally {
    submitting.value = false
  }
}

async function handleDeleteJob(job) {
  if (!window.confirm(`确认清理任务《${displayTitle(job.title, '任务')}》？`)) {
    return
  }

  try {
    const response = await apiClient.deleteJob(job.id)
    message.success(response.message || '任务已移除')
    await refreshJobs()
  } catch (error) {
    notifyError(message, error)
  }
}

function openProjectDetail(projectId) {
  router.push({
    name: 'ProjectDetail',
    params: { projectId }
  })
}

function openTools(projectId, tab) {
  router.push({
    name: 'Tools',
    query: {
      projectId,
      tab,
      autoload: '1'
    }
  })
}

function downloadProject(projectId, format) {
  window.open(apiClient.getProjectExportUrl(projectId, format), '_blank', 'noopener')
}

onMounted(async () => {
  await refreshJobs()
  startPolling()
  window.addEventListener(BACKEND_STATUS_EVENT, handleBackendStatusEvent)
})

onUnmounted(() => {
  stopPolling()
  window.removeEventListener(BACKEND_STATUS_EVENT, handleBackendStatusEvent)
})
</script>
