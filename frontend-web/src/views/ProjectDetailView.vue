<template>
  <div class="page-stack">
    <template v-if="project">
      <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Project</p>
        <h1 class="hero-title">{{ displayTitle(project.title, '项目') }}</h1>
        <p class="hero-copy">
          在这里查看项目设定、章节大纲和正文预览，也可以直接带着当前项目进入工作台、润色工具或续写助手。
        </p>
        <div class="hero-actions">
          <n-button type="primary" :disabled="backendStore.unavailable" @click="openWorkspace">继续创作</n-button>
          <n-button secondary @click="openTools('polish')">去润色工具</n-button>
          <n-button secondary @click="openTools('continuation')">去续写助手</n-button>
        </div>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">目标章节</div>
          <div class="metric-value">{{ targetChapterCount }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">已完成章节</div>
          <div class="metric-value">{{ completedChapters }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">正文总字数</div>
          <div class="metric-value">{{ totalWordsText }}</div>
        </div>
      </div>
      </section>

      <section class="split-grid">
      <article class="surface-card">
        <h2 class="section-heading">项目设定</h2>
        <div class="chapter-preview">
          <div class="chapter-preview__item">
            <strong>题材</strong>
            <p class="section-copy" style="margin-top:8px;">{{ project.genre || '未分类' }}</p>
          </div>
          <div class="chapter-preview__item">
            <strong>角色设定</strong>
            <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">
              {{ project.character_setting || '暂无内容' }}
            </p>
          </div>
          <div class="chapter-preview__item">
            <strong>世界观设定</strong>
            <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">
              {{ project.world_setting || '暂无内容' }}
            </p>
          </div>
          <div class="chapter-preview__item">
            <strong>剧情构思</strong>
            <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">
              {{ project.plot_idea || '暂无内容' }}
            </p>
          </div>
        </div>
      </article>

      <article class="surface-card surface-card--muted">
        <h2 class="section-heading">导出与操作</h2>
        <div class="stack">
          <div class="inline-note">
            <strong>最近更新时间：</strong>
            <span>{{ formatDate(project.updated_at) }}</span>
          </div>
          <div class="inline-note">
            <strong>平均每章字数：</strong>
            <span>{{ averageWordsText }}</span>
          </div>
          <n-select v-model:value="downloadFormat" :options="downloadOptions" />
          <n-button type="primary" :disabled="backendStore.unavailable" @click="downloadProject(downloadFormat)">下载项目</n-button>
          <n-button secondary @click="openTools('polish')">带项目去润色</n-button>
          <n-button secondary @click="openTools('continuation')">带项目去续写</n-button>
          <n-button secondary @click="router.push({ name: 'Projects' })">返回项目中心</n-button>
        </div>
      </article>
      </section>

      <section v-if="outlineItems.length" class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
        <div>
          <h2 class="section-heading">章节大纲</h2>
          <p class="section-copy">共 {{ outlineItems.length }} 章规划，可作为续写和编辑的结构参考。</p>
        </div>
        <n-tag type="info" round>大纲 {{ outlineItems.length }} 章</n-tag>
      </div>

      <div class="chapter-preview" style="margin-top:16px;">
        <div
          v-for="item in outlineItems"
          :key="`${item.number}-${item.title}`"
          class="chapter-preview__item"
        >
          <strong>{{ item.title }}</strong>
          <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">
            {{ item.description || '暂无大纲说明' }}
          </p>
        </div>
      </div>
      </section>

      <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">章节列表</h2>
          <p class="section-copy">
            当前共 {{ allChapters.length }} 章，筛选后显示 {{ filteredChapters.length }} 章。
          </p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="chapterFilter" :options="chapterFilterOptions" style="width: 160px;" />
          <n-input v-model:value="chapterSearchKeyword" clearable placeholder="搜索章节标题或摘要" />
        </div>
      </div>

      <div v-if="filteredChapters.length" class="chapter-preview" style="margin-top:16px;">
        <div v-for="chapter in filteredChapters" :key="chapter.num" class="chapter-preview__item">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <strong>{{ formatChapterTitle(chapter) }}</strong>
            <n-tag :type="chapter.content?.trim() ? 'success' : 'warning'" size="small" round>
              {{ chapter.content?.trim() ? '已完成' : '未写正文' }}
            </n-tag>
          </div>
          <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">
            {{ chapter.desc || '暂无章节说明' }}
          </p>
          <div class="project-card__meta">
            <n-tag size="small" :bordered="false">
              字数 {{ formatChapterWords(chapter) }}
            </n-tag>
            <n-tag size="small" :bordered="false">
              更新时间 {{ formatDate(chapter.generated_at) }}
            </n-tag>
          </div>
          <details style="margin-top:10px;">
            <summary style="cursor:pointer; color:#0f766e; font-weight:600;">查看正文预览</summary>
            <p class="section-copy" style="margin-top:10px; white-space: pre-wrap;">
              {{ chapter.content || '暂无正文内容' }}
            </p>
          </details>
        </div>
      </div>

      <div v-else class="empty-state">
        当前筛选条件下没有章节内容。可以调整筛选条件，或去工作台继续创作。
      </div>
      </section>
    </template>

    <BackendHelpCard
      v-else-if="backendStore.unavailable"
      title="项目详情暂不可用"
      detail="当前无法读取项目设定、章节和导出信息，请先启动后端服务后再返回本页。"
    />

    <div v-else class="empty-state">
      正在载入项目数据...
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NInput, NSelect, NTag, useMessage } from 'naive-ui'
import { apiClient } from '../api'
import { useBackendStore } from '../stores/backend'
import BackendHelpCard from '../components/BackendHelpCard.vue'
import { isBackendAvailabilityError, notifyError } from '../utils/errors'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const backendStore = useBackendStore()

const project = ref(null)
const downloadFormat = ref('txt')
const chapterFilter = ref('all')
const chapterSearchKeyword = ref('')

const downloadOptions = [
  { label: 'TXT', value: 'txt' },
  { label: 'Markdown', value: 'md' },
  { label: 'HTML', value: 'html' },
  { label: 'Word', value: 'docx' },
  { label: 'JSON', value: 'json' }
]

const chapterFilterOptions = [
  { label: '全部章节', value: 'all' },
  { label: '已完成', value: 'completed' },
  { label: '未写正文', value: 'empty' }
]

const allChapters = computed(() => project.value?.chapters || [])

const completedChapters = computed(() =>
  allChapters.value.filter(chapter => chapter.content?.trim()).length
)

const totalWords = computed(() =>
  allChapters.value.reduce((sum, chapter) => {
    const wordCount = Number(chapter.word_count) || chapter.content?.trim()?.length || 0
    return sum + wordCount
  }, 0)
)

const totalWordsText = computed(() => totalWords.value.toLocaleString('zh-CN'))

const averageWordsText = computed(() => {
  if (!completedChapters.value) return '暂无'
  return Math.round(totalWords.value / completedChapters.value).toLocaleString('zh-CN')
})

const targetChapterCount = computed(() =>
  project.value?.chapter_count || allChapters.value.length || 0
)

const outlineItems = computed(() =>
  (project.value?.outline || []).map((item, index) => ({
    number: item.num || item.number || index + 1,
    title: item.title || `第${item.num || item.number || index + 1}章`,
    description: item.description || item.desc || item.summary || ''
  }))
)

const filteredChapters = computed(() => {
  const keyword = chapterSearchKeyword.value.trim().toLowerCase()
  let list = [...allChapters.value]

  if (chapterFilter.value === 'completed') {
    list = list.filter(chapter => chapter.content?.trim())
  } else if (chapterFilter.value === 'empty') {
    list = list.filter(chapter => !chapter.content?.trim())
  }

  if (keyword) {
    list = list.filter(chapter => {
      const haystack = [
        chapter.title,
        chapter.desc
      ].join(' ').toLowerCase()
      return haystack.includes(keyword)
    })
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

function formatChapterTitle(chapter) {
  const number = chapter?.num ?? '?'
  const title = String(chapter?.title || '')
    .replace(/^\u7b2c\s*\d+\s*\u7ae0[\s:：\-—]*/i, '')
    .replace(/^Chapter\s*\d+[\s:：\-—]*/i, '')
    .trim()
  return title ? `第${number}章 · ${title}` : `第${number}章`
}

function formatChapterWords(chapter) {
  const count = Number(chapter?.word_count) || chapter?.content?.trim()?.length || 0
  return count.toLocaleString('zh-CN')
}

async function loadProject() {
  try {
    const response = await apiClient.getProject(route.params.projectId)
    project.value = response.data
  } catch (error) {
    notifyError(message, error)
    if (!isBackendAvailabilityError(error)) {
      router.push({ name: 'Projects' })
    }
  }
}

function openWorkspace() {
  router.push({
    name: 'Workspace',
    query: {
      projectId: String(route.params.projectId),
      mode: 'quick'
    }
  })
}

function openTools(tab) {
  router.push({
    name: 'Tools',
    query: {
      projectId: String(route.params.projectId),
      tab,
      autoload: '1'
    }
  })
}

function downloadProject(format) {
  window.open(apiClient.getProjectExportUrl(route.params.projectId, format), '_blank', 'noopener')
}

onMounted(loadProject)
</script>
