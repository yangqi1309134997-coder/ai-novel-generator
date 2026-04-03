<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Projects</p>
        <h1 class="hero-title">项目中心</h1>
        <p class="hero-copy">
          在这里创建项目、查看进度、进入详情页、跳转工具中心或继续创作。
          项目卡片不只是列表，而是客户进入项目详情、工作台和润色续写流程的统一入口。
        </p>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">项目总数</div>
          <div class="metric-value">{{ projects.length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">进行中项目</div>
          <div class="metric-value">{{ activeProjectCount }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">累计字数</div>
          <div class="metric-value">{{ totalWordsText }}</div>
        </div>
      </div>
    </section>

    <div class="split-grid">
      <section class="surface-card">
        <h2 class="section-heading">快速创建项目</h2>
        <p class="section-copy">
          适合先建立项目基础设定，再进入工作台继续写作，或去工具中心做润色与续写。
        </p>

        <div class="stack">
          <n-input v-model:value="form.title" placeholder="项目标题" />
          <n-select v-model:value="form.genre" :options="genreOptions" placeholder="项目题材" />
          <n-input-number v-model:value="form.chapter_count" :min="10" :max="1000" />
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
            <n-button type="primary" :loading="submitting" :disabled="backendStore.unavailable" @click="handleCreateProject">
              创建项目
            </n-button>
            <n-button secondary @click="goWorkspace">
              去工作台
            </n-button>
          </div>
        </div>
      </section>

      <section class="surface-card surface-card--muted">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:12px; flex-wrap:wrap;">
          <div>
            <h2 class="section-heading">已有项目</h2>
            <p class="section-copy">可直接进入项目详情、工作台、润色工具或续写助手。</p>
          </div>
          <div class="result-actions">
            <n-select v-model:value="downloadFormat" :options="downloadOptions" style="width: 160px;" />
            <n-select v-model:value="statusFilter" :options="statusOptions" style="width: 160px;" />
            <n-select v-model:value="sortMode" :options="sortOptions" style="width: 180px;" />
            <n-button secondary :disabled="backendStore.unavailable" @click="loadProjects">刷新</n-button>
          </div>
        </div>

        <div class="result-actions" style="margin-bottom:16px;">
          <n-input
            v-model:value="searchKeyword"
            placeholder="按标题、题材或最近章节搜索"
            clearable
          />
        </div>

        <n-spin :show="loading">
          <div v-if="filteredProjects.length" class="project-list">
            <article v-for="project in filteredProjects" :key="project.id" class="project-card">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                <div>
                  <h3 style="margin:0; font-size:1.08rem;">{{ displayTitle(project.title, '项目') }}</h3>
                  <p style="margin:8px 0 0; color:#64748b;">
                    {{ project.genre || '未分类' }} · 更新于 {{ formatDate(project.updated_at) }}
                  </p>
                </div>
                <n-tag type="info" round>{{ progressText(project) }}</n-tag>
              </div>

              <div class="project-card__meta">
                <n-tag size="small" :bordered="false" type="success">
                  已完成 {{ project.completed_chapters || 0 }} 章
                </n-tag>
                <n-tag size="small" :bordered="false">
                  目标 {{ project.total_chapters || 0 }} 章
                </n-tag>
                <n-tag size="small" :bordered="false" type="warning">
                  当前正文 {{ project.chapter_count || 0 }} 章
                </n-tag>
                <n-tag size="small" :bordered="false">
                  {{ formatWordCount(project.total_words) }}
                </n-tag>
                <n-tag size="small" :bordered="false">
                  大纲 {{ project.outline_count || 0 }} 章
                </n-tag>
              </div>

              <div class="inline-note">
                <strong>最近章节：</strong>
                <span>{{ formatLatestChapter(project) }}</span>
              </div>

              <ProjectQuickActions
                :project-id="project.id"
                :download-format="downloadFormat"
                :disable-download="backendStore.unavailable"
                :download-secondary="true"
              >
                <n-button secondary type="error" :disabled="backendStore.unavailable" @click="handleDeleteProject(project)">
                  删除
                </n-button>
              </ProjectQuickActions>
            </article>
          </div>

          <div v-else-if="backendStore.unavailable">
            <BackendHelpCard title="项目列表暂不可用" detail="当前无法从后端读取项目列表，请先启动后端服务。" />
          </div>

          <div v-else class="empty-state">
            当前筛选条件下没有项目。可以调整筛选条件，或先创建一个新项目。
          </div>
        </n-spin>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NInputNumber, NSelect, NSpin, NTag, useMessage } from 'naive-ui'
import { apiClient } from '../api'
import BackendHelpCard from '../components/BackendHelpCard.vue'
import ProjectQuickActions from '../components/ProjectQuickActions.vue'
import { useBackendStore } from '../stores/backend'
import { notifyError } from '../utils/errors'

const router = useRouter()
const message = useMessage()
const backendStore = useBackendStore()

const loading = ref(false)
const submitting = ref(false)
const projects = ref([])
const searchKeyword = ref('')
const statusFilter = ref('all')
const sortMode = ref('updated_desc')
const downloadFormat = ref('txt')

const form = reactive({
  title: '',
  genre: '玄幻',
  chapter_count: 50,
  character_setting: '',
  world_setting: '',
  plot_idea: ''
})

const genreOptions = [
  '玄幻', '仙侠', '武侠', '都市', '言情', '悬疑', '科幻', '历史'
].map(item => ({ label: item, value: item }))

const downloadOptions = [
  { label: 'TXT', value: 'txt' },
  { label: 'Markdown', value: 'md' },
  { label: 'HTML', value: 'html' },
  { label: 'Word', value: 'docx' },
  { label: 'JSON', value: 'json' }
]

const statusOptions = [
  { label: '全部状态', value: 'all' },
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'completed' },
  { label: '未开写', value: 'empty' }
]

const sortOptions = [
  { label: '最近更新', value: 'updated_desc' },
  { label: '总字数最高', value: 'words_desc' },
  { label: '进度最高', value: 'progress_desc' }
]

const activeProjectCount = computed(() =>
  projects.value.filter(project => {
    const total = Number(project.total_chapters) || 0
    const completed = Number(project.completed_chapters) || 0
    return total > 0 && completed < total
  }).length
)

const totalWordsText = computed(() => {
  const total = projects.value.reduce((sum, project) => sum + (Number(project.total_words) || 0), 0)
  if (!total) return '0'
  if (total >= 10000) return `${(total / 10000).toFixed(1)}w`
  return total.toLocaleString('zh-CN')
})

const filteredProjects = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  let list = [...projects.value]

  if (statusFilter.value === 'active') {
    list = list.filter(project => {
      const total = Number(project.total_chapters) || 0
      const completed = Number(project.completed_chapters) || 0
      return total > 0 && completed < total
    })
  } else if (statusFilter.value === 'completed') {
    list = list.filter(project => {
      const total = Number(project.total_chapters) || 0
      const completed = Number(project.completed_chapters) || 0
      return total > 0 && completed >= total
    })
  } else if (statusFilter.value === 'empty') {
    list = list.filter(project => (Number(project.completed_chapters) || 0) === 0)
  }

  if (keyword) {
    list = list.filter(project => {
      const haystack = [project.title, project.genre, project.latest_chapter_title].join(' ').toLowerCase()
      return haystack.includes(keyword)
    })
  }

  if (sortMode.value === 'words_desc') {
    list.sort((a, b) => (Number(b.total_words) || 0) - (Number(a.total_words) || 0))
  } else if (sortMode.value === 'progress_desc') {
    list.sort((a, b) => progressRatio(b) - progressRatio(a))
  } else {
    list.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')))
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

function formatDate(value) {
  if (!value) return '未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatWordCount(value) {
  const count = Number(value) || 0
  return count > 0 ? `总字数 ${count.toLocaleString('zh-CN')}` : '总字数 0'
}

function formatLatestChapter(project) {
  const number = project?.latest_chapter_num
  const title = String(project?.latest_chapter_title || '').trim()
  if (number && title) return `第${number}章 · ${title}`
  if (title) return title
  return '暂无正文章节'
}

function progressRatio(project) {
  const total = Number(project.total_chapters) || 0
  const completed = Number(project.completed_chapters) || 0
  if (!total) return 0
  return completed / total
}

function progressText(project) {
  return `${project.completed_chapters || 0}/${project.total_chapters || 0}`
}

function resetForm() {
  form.title = ''
  form.genre = '玄幻'
  form.chapter_count = 50
  form.character_setting = ''
  form.world_setting = ''
  form.plot_idea = ''
}

async function loadProjects() {
  loading.value = true
  try {
    const response = await apiClient.listProjects()
    projects.value = response.data || []
  } catch (error) {
    notifyError(message, error)
  } finally {
    loading.value = false
  }
}

async function handleCreateProject() {
  if (!form.title.trim()) {
    message.warning('请先填写项目标题')
    return
  }

  submitting.value = true
  try {
    const response = await apiClient.createProject(form)
    message.success(response.message || '项目已创建')
    resetForm()
    await loadProjects()
    if (response.data?.id) {
      router.push({
        name: 'ProjectDetail',
        params: { projectId: response.data.id }
      })
    }
  } catch (error) {
    notifyError(message, error)
  } finally {
    submitting.value = false
  }
}

function goWorkspace() {
  router.push({ name: 'Workspace' })
}

async function handleDeleteProject(project) {
  if (!window.confirm(`确认删除项目《${displayTitle(project.title, '项目')}》？`)) {
    return
  }

  try {
    const response = await apiClient.deleteProject(project.id)
    message.success(response.message || '项目已删除')
    await loadProjects()
  } catch (error) {
    notifyError(message, error)
  }
}

onMounted(loadProjects)
</script>
