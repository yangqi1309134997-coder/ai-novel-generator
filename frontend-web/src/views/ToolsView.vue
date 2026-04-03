<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Tools</p>
        <h1 class="hero-title">创作工具中心</h1>
        <p class="hero-copy">
          这里提供文本润色、续写分析与生成、提示词模板管理等辅助能力。
          你可以直接输入文本，也可以从现有项目载入正文后继续处理。
        </p>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">工具分区</div>
          <div class="metric-value">3</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">可用项目</div>
          <div class="metric-value">{{ projectOptions.length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">当前标签</div>
          <div class="metric-value">{{ activeTabLabel }}</div>
        </div>
      </div>
    </section>

    <section v-if="currentProjectSummary" class="surface-card surface-card--muted">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">当前项目摘要</h2>
          <p class="section-copy">
            {{ currentProjectSummary.title }} · {{ currentProjectSummary.genre || '未分类' }}
          </p>
        </div>
        <div class="project-card__meta" style="margin:0;">
          <n-tag size="small" :bordered="false" type="info">
            {{ currentProjectSummary.completed_chapters || 0 }}/{{ currentProjectSummary.total_chapters || 0 }}
          </n-tag>
          <n-tag size="small" :bordered="false">
            {{ formatWordCount(currentProjectSummary.total_words) }}
          </n-tag>
          <n-tag size="small" :bordered="false" type="warning">
            {{ formatLatestChapter(currentProjectSummary) }}
          </n-tag>
        </div>
      </div>

      <div class="result-actions" style="margin-top:16px;">
        <n-button secondary @click="openProjectDetail(currentProjectSummary.id)">查看详情</n-button>
        <n-button tertiary @click="openWorkspace(currentProjectSummary.id)">去工作台</n-button>
        <n-button tertiary @click="reloadCurrentProjectText">重新载入正文</n-button>
      </div>
    </section>

    <BackendHelpCard
      v-if="backendStore.unavailable"
      title="工具中心当前无法连到后端"
      detail="润色、续写、项目载入和提示词管理都依赖后端服务。界面仍可浏览，但执行按钮会被禁用。"
    />

    <n-alert v-if="generationBlocked" type="warning" :show-icon="false">
      {{ authStore.generationMessage || '当前账号暂无生成权限，请联系管理员开通会员或调整平台策略。' }}
    </n-alert>

    <section class="surface-card">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="polish" tab="润色工作台">
          <div class="split-grid">
            <section class="surface-card">
              <h2 class="section-heading">文本润色</h2>
              <div class="stack">
                <n-select
                  v-model:value="polishForm.project_id"
                  :options="projectOptions"
                  placeholder="从项目载入内容（可选）"
                />
                <label class="file-trigger">
                  <span>导入本地文件</span>
                  <input type="file" accept=".txt,.md,.json" @change="handlePolishFileChange" />
                </label>
                <div class="result-actions">
                  <n-button tertiary :disabled="backendStore.unavailable || generationBlocked" @click="loadProjectIntoPolish">载入项目正文</n-button>
                  <n-button
                    v-if="polishForm.project_id"
                    tertiary
                    @click="openProjectDetail(polishForm.project_id)"
                  >
                    查看项目
                  </n-button>
                </div>
                <n-select v-model:value="polishForm.polish_type" :options="polishOptions" />
                <n-input
                  v-model:value="polishForm.custom_req"
                  type="textarea"
                  :rows="3"
                  placeholder="额外要求"
                />
                <n-input
                  v-model:value="polishForm.text"
                  type="textarea"
                  :rows="14"
                  placeholder="输入需要润色的文本"
                />

                <div class="result-actions">
                  <n-button type="primary" :loading="polishLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handlePolish">
                    开始润色
                  </n-button>
                  <n-button secondary :loading="suggestionLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handlePolishSuggestions">
                    润色并给建议
                  </n-button>
                  <n-button
                    v-if="polishForm.project_id && polishOutput"
                    tertiary
                    :loading="polishSaving"
                    :disabled="backendStore.unavailable || generationBlocked"
                    @click="handleSavePolish"
                  >
                    保存润色结果到项目
                  </n-button>
                  <n-button
                    v-if="polishForm.project_id"
                    tertiary
                    @click="openWorkspace(polishForm.project_id)"
                  >
                    去工作台
                  </n-button>
                  <n-button
                    v-if="polishOutput"
                    tertiary
                    @click="downloadTextResult(polishOutput, 'polish-result.txt')"
                  >
                    下载润色结果
                  </n-button>
                </div>
              </div>
            </section>

            <section class="surface-card surface-card--muted">
              <h2 class="section-heading">输出结果</h2>
              <div class="stack">
                <div class="inline-note">
                  <strong>保存提示：</strong>
                  <span>保存回项目时，请保留“第 N 章”或“Chapter N”这样的章节标题。</span>
                </div>
                <n-input
                  v-model:value="polishOutput"
                  type="textarea"
                  :rows="14"
                  placeholder="润色结果会显示在这里"
                />
                <n-input
                  v-model:value="polishSuggestions"
                  type="textarea"
                  :rows="8"
                  placeholder="建议会显示在这里"
                />
              </div>
            </section>
          </div>
        </n-tab-pane>

        <n-tab-pane name="continuation" tab="续写助手">
          <div class="split-grid">
            <section class="surface-card">
              <h2 class="section-heading">续写分析与规划</h2>
              <div class="stack">
                <n-select
                  v-model:value="continuationForm.project_id"
                  :options="projectOptions"
                  placeholder="选择项目后自动载入正文（可选）"
                />
                <label class="file-trigger">
                  <span>导入本地文件</span>
                  <input type="file" accept=".txt,.md,.json" @change="handleContinuationFileChange" />
                </label>
                <div class="result-actions">
                  <n-button tertiary :disabled="backendStore.unavailable || generationBlocked" @click="loadProjectIntoContinuation">载入项目正文</n-button>
                  <n-button
                    v-if="continuationForm.project_id"
                    tertiary
                    @click="openProjectDetail(continuationForm.project_id)"
                  >
                    查看项目
                  </n-button>
                </div>
                <n-input-number v-model:value="continuationForm.current_chapters" :min="1" :max="10000" />
                <n-input-number
                  v-model:value="continuationForm.target_words"
                  :min="500"
                  :max="10000"
                  :step="100"
                />
                <n-input
                  v-model:value="continuationForm.content"
                  type="textarea"
                  :rows="14"
                  placeholder="输入已有小说内容"
                />

                <div class="result-actions">
                  <n-button type="primary" :loading="analyzeLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handleAnalyzeContinuation">
                    分析小说
                  </n-button>
                  <n-button secondary :loading="continuationLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handleGenerateContinuation">
                    生成下一章
                  </n-button>
                  <n-button
                    v-if="continuationForm.project_id && continuationOutput"
                    tertiary
                    :loading="continuationSaving"
                    :disabled="backendStore.unavailable || generationBlocked"
                    @click="handleSaveContinuation"
                  >
                    保存到项目
                  </n-button>
                  <n-button
                    v-if="continuationForm.project_id"
                    tertiary
                    @click="openWorkspace(continuationForm.project_id)"
                  >
                    去工作台
                  </n-button>
                  <n-button
                    v-if="continuationOutput"
                    tertiary
                    @click="downloadTextResult(continuationOutput, 'continuation-result.txt')"
                  >
                    下载续写结果
                  </n-button>
                </div>
              </div>
            </section>

            <section class="surface-card surface-card--muted">
              <h2 class="section-heading">分析输出</h2>
              <div class="stack">
                <n-input
                  v-model:value="continuationAnalysis"
                  type="textarea"
                  :rows="10"
                  placeholder="剧情分析"
                />
                <n-input
                  v-model:value="continuationPlanning"
                  type="textarea"
                  :rows="10"
                  placeholder="后续规划"
                />
                <n-input
                  v-model:value="continuationOutput"
                  type="textarea"
                  :rows="12"
                  placeholder="续写结果"
                />
              </div>
            </section>
          </div>
        </n-tab-pane>

        <n-tab-pane v-if="canManagePrompts" name="prompts" tab="提示词中心">
          <div class="split-grid">
            <section class="surface-card">
              <h2 class="section-heading">提示词模板管理</h2>
              <div class="stack">
                <n-select
                  v-model:value="promptForm.category"
                  :options="promptCategories"
                  @update:value="handlePromptCategoryChange"
                />
                <n-input v-model:value="promptSearchKeyword" clearable placeholder="搜索模板名" />
                <n-select
                  v-model:value="promptForm.name"
                  :options="filteredPromptNameOptions"
                  @update:value="handlePromptSelect"
                />
                <n-input
                  v-model:value="promptForm.content"
                  type="textarea"
                  :rows="18"
                  placeholder="提示词内容"
                />
                <div class="result-actions">
                  <n-button type="primary" :loading="promptSaving" :disabled="backendStore.unavailable" @click="handleSavePrompt">
                    保存模板
                  </n-button>
                  <n-button secondary :loading="promptResetting" :disabled="backendStore.unavailable" @click="handleResetPrompt">
                    重置为预设
                  </n-button>
                </div>
              </div>
            </section>

            <section class="surface-card surface-card--muted">
              <h2 class="section-heading">当前分类模板</h2>
              <div class="inline-note" style="margin-bottom:16px;">
                <strong>可见模板：</strong>
                <span>{{ filteredPromptNameOptions.length }} / {{ promptNameOptions.length }}</span>
              </div>
              <div class="chapter-preview">
                <div v-for="item in filteredPromptNameOptions" :key="item.value" class="chapter-preview__item">
                  <strong>{{ item.label }}</strong>
                  <p class="section-copy" style="margin-top:8px;">分类：{{ currentPromptCategoryLabel }}</p>
                </div>
              </div>
            </section>
          </div>
        </n-tab-pane>
      </n-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NInput, NInputNumber, NSelect, NTabPane, NTabs, useMessage } from 'naive-ui'
import { apiClient } from '../api'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'
import BackendHelpCard from '../components/BackendHelpCard.vue'
import { notifyError } from '../utils/errors'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const backendStore = useBackendStore()

const activeTab = ref('polish')
const polishLoading = ref(false)
const suggestionLoading = ref(false)
const polishSaving = ref(false)
const analyzeLoading = ref(false)
const continuationLoading = ref(false)
const continuationSaving = ref(false)
const promptSaving = ref(false)
const promptResetting = ref(false)

const polishOutput = ref('')
const polishSuggestions = ref('')
const continuationAnalysis = ref('')
const continuationPlanning = ref('')
const continuationOutput = ref('')
const projectOptions = ref([])
const projectCatalog = ref([])
const promptNameOptions = ref([])
const promptSearchKeyword = ref('')

const polishForm = reactive({
  project_id: '',
  text: '',
  polish_type: '全面润色',
  custom_req: ''
})

const continuationForm = reactive({
  project_id: '',
  content: '',
  current_chapters: 30,
  target_words: 3000
})

const promptForm = reactive({
  category: 'generation',
  name: '',
  content: ''
})

const polishOptions = [
  '全面润色',
  '查找错误',
  '改进建议',
  '直接修改',
  '去除 AI 味',
  '增强细节',
  '优化对话',
  '改善节奏'
].map(item => ({ label: item, value: item }))

const promptCategories = [
  { label: '章节生成', value: 'generation' },
  { label: '内容重写', value: 'rewrite' },
  { label: '大纲生成', value: 'outline' },
  { label: '角色提取', value: 'character' },
  { label: '剧情分析', value: 'plot' },
  { label: '世界设定', value: 'world' },
  { label: '对话优化', value: 'dialogue' },
  { label: '风格调整', value: 'style' }
]

const activeTabLabel = computed(() =>
  ({
    polish: '润色工作台',
    continuation: '续写助手',
    prompts: '提示词中心'
  })[activeTab.value] || '润色工作台'
)

const currentPromptCategoryLabel = computed(() =>
  promptCategories.find(item => item.value === promptForm.category)?.label || promptForm.category
)

const currentProjectSummary = computed(() => {
  const projectId = activeTab.value === 'continuation' ? continuationForm.project_id : polishForm.project_id
  return projectCatalog.value.find(project => project.id === projectId) || null
})
const generationBlocked = computed(() => !authStore.canGenerate && !authStore.isBackoffice)
const canManagePrompts = computed(() => authStore.hasPermission('prompts.view'))

const filteredPromptNameOptions = computed(() => {
  const keyword = promptSearchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return promptNameOptions.value
  }
  return promptNameOptions.value.filter(item => item.label.toLowerCase().includes(keyword))
})

function displayTitle(title, fallbackPrefix) {
  const text = String(title || '').trim()
  if (!text || /^\?+$/.test(text)) {
    return `${fallbackPrefix}记录`
  }
  return text
}

function normalizeToolTab(tab) {
  return ['polish', 'continuation', 'prompts'].includes(tab) ? tab : 'polish'
}

function formatWordCount(value) {
  const count = Number(value) || 0
  return count > 0 ? `总字数 ${count.toLocaleString('zh-CN')}` : '总字数 0'
}

function formatLatestChapter(project) {
  const number = project?.latest_chapter_num
  const title = String(project?.latest_chapter_title || '').trim()
  if (number && title) return `最近章节 第${number}章`
  if (title) return `最近章节 ${title}`
  return '最近章节 暂无'
}

function stripChapterPrefix(title) {
  return String(title || '')
    .replace(/^\u7b2c\s*\d+\s*\u7ae0[\s:：\-—]*/i, '')
    .replace(/^Chapter\s*\d+[\s:：\-—]*/i, '')
    .trim()
}

function buildProjectText(chapters) {
  return (chapters || [])
    .filter(ch => ch.content?.trim())
    .map(ch => `第${ch.num}章 ${stripChapterPrefix(ch.title) || ''}\n\n${ch.content}`.trim())
    .join('\n\n')
}

function hasStructuredChapters(text) {
  const normalized = String(text || '')
  return /(^|\n)(?:#+\s*)?(?:第\s*\d+\s*章|Chapter\s*\d+)/i.test(normalized)
}

function downloadTextResult(text, filename) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function openProjectDetail(projectId) {
  router.push({
    name: 'ProjectDetail',
    params: { projectId }
  })
}

function openWorkspace(projectId) {
  router.push({
    name: 'Workspace',
    query: {
      projectId,
      mode: 'quick'
    }
  })
}

async function readLocalTextFile(event) {
  const file = event?.target?.files?.[0]
  if (!file) return ''

  const text = await file.text()
  try {
    if (file.name.toLowerCase().endsWith('.json')) {
      const data = JSON.parse(text)
      if (Array.isArray(data?.chapters)) {
        return buildProjectText(data.chapters)
      }
    }
  } catch {
    // fall through
  }
  return text
}

async function handlePolishFileChange(event) {
  try {
    polishForm.text = await readLocalTextFile(event)
    if (polishForm.text) {
      message.success('文件内容已载入润色工作台')
    }
  } catch (error) {
    notifyError(message, error)
  } finally {
    event.target.value = ''
  }
}

async function handleContinuationFileChange(event) {
  try {
    continuationForm.content = await readLocalTextFile(event)
    if (continuationForm.content) {
      message.success('文件内容已载入续写助手')
    }
  } catch (error) {
    notifyError(message, error)
  } finally {
    event.target.value = ''
  }
}

async function loadProjects() {
  const response = await apiClient.listProjects()
  projectCatalog.value = response.data || []
  projectOptions.value = projectCatalog.value.map(project => ({
    label: displayTitle(project.title, '项目'),
    value: project.id
  }))
}

async function reloadCurrentProjectText() {
  if (activeTab.value === 'continuation') {
    await loadProjectIntoContinuation()
    return
  }

  if (activeTab.value === 'polish') {
    await loadProjectIntoPolish()
  }
}

async function loadProjectIntoPolish() {
  if (!polishForm.project_id) {
    message.warning('请先选择项目')
    return
  }

  try {
    const response = await apiClient.getProject(polishForm.project_id)
    polishForm.text = buildProjectText(response.data?.chapters || [])
    message.success('项目正文已载入润色工作台')
  } catch (error) {
    notifyError(message, error)
  }
}

async function loadProjectIntoContinuation() {
  if (!continuationForm.project_id) {
    message.warning('请先选择项目')
    return
  }

  try {
    const response = await apiClient.getProject(continuationForm.project_id)
    const chapters = (response.data?.chapters || []).filter(ch => ch.content?.trim())
    continuationForm.content = buildProjectText(chapters)
    continuationForm.current_chapters = Math.max(chapters.length, 1)
    message.success('项目正文已载入续写助手')
  } catch (error) {
    notifyError(message, error)
  }
}

async function applyRouteContext() {
  activeTab.value = normalizeToolTab(typeof route.query.tab === 'string' ? route.query.tab : '')

  const projectId = typeof route.query.projectId === 'string' ? route.query.projectId : ''
  if (!projectId) {
    return
  }

  polishForm.project_id = projectId
  continuationForm.project_id = projectId

  if (route.query.autoload !== '1') {
    return
  }

  if (activeTab.value === 'continuation') {
    await loadProjectIntoContinuation()
    return
  }

  if (activeTab.value === 'polish') {
    await loadProjectIntoPolish()
  }
}

async function handlePolish() {
  if (!polishForm.text.trim()) {
    message.warning('请先输入需要润色的文本')
    return
  }

  polishLoading.value = true
  try {
    const response = await apiClient.polishText({
      text: polishForm.text,
      polish_type: polishForm.polish_type,
      custom_req: polishForm.custom_req
    })
    polishOutput.value = response.data.content || ''
    message.success(response.message || '润色完成')
  } catch (error) {
    notifyError(message, error)
  } finally {
    polishLoading.value = false
  }
}

async function handlePolishSuggestions() {
  if (!polishForm.text.trim()) {
    message.warning('请先输入需要润色的文本')
    return
  }

  suggestionLoading.value = true
  try {
    const response = await apiClient.polishWithSuggestions({
      text: polishForm.text,
      polish_type: polishForm.polish_type,
      custom_req: polishForm.custom_req
    })
    polishOutput.value = response.data.content || ''
    polishSuggestions.value = response.data.suggestions || ''
    message.success(response.message || '润色建议已生成')
  } catch (error) {
    notifyError(message, error)
  } finally {
    suggestionLoading.value = false
  }
}

async function handleSavePolish() {
  if (!polishForm.project_id) {
    message.warning('请先选择项目')
    return
  }
  if (!polishOutput.value.trim()) {
    message.warning('请先生成润色结果')
    return
  }
  if (!hasStructuredChapters(polishOutput.value)) {
    message.warning('保存回项目前，请保留“第 N 章”或 “Chapter N” 的章节标题格式')
    return
  }

  polishSaving.value = true
  try {
    const response = await apiClient.replaceProjectContent(polishForm.project_id, {
      text: polishOutput.value
    })
    await loadProjects()
    message.success(response.message || '项目正文已更新')
  } catch (error) {
    notifyError(message, error)
  } finally {
    polishSaving.value = false
  }
}

async function handleAnalyzeContinuation() {
  if (!continuationForm.content.trim()) {
    message.warning('请先输入已有小说内容')
    return
  }

  analyzeLoading.value = true
  try {
    const response = await apiClient.analyzeContinuation({
      content: continuationForm.content,
      current_chapters: continuationForm.current_chapters
    })
    continuationAnalysis.value = response.data.analysis || ''
    continuationPlanning.value = response.data.planning || ''
    message.success(response.message || '续写分析完成')
  } catch (error) {
    notifyError(message, error)
  } finally {
    analyzeLoading.value = false
  }
}

async function handleGenerateContinuation() {
  if (!continuationForm.content.trim()) {
    message.warning('请先输入已有小说内容')
    return
  }

  continuationLoading.value = true
  try {
    const response = await apiClient.generateContinuation({
      content: continuationForm.content,
      planning: continuationPlanning.value,
      current_chapters: continuationForm.current_chapters,
      target_words: continuationForm.target_words
    })
    continuationOutput.value = response.data.content || ''
    message.success(response.message || '续写生成完成')
  } catch (error) {
    notifyError(message, error)
  } finally {
    continuationLoading.value = false
  }
}

function extractContinuationTitle() {
  const firstLine = (continuationOutput.value || '').split('\n').find(line => line.trim())
  if (!firstLine) {
    return `续写章节 ${continuationForm.current_chapters + 1}`
  }
  const cleaned = firstLine
    .replace(/^#+\s*/, '')
    .replace(/^\u7b2c\s*\d+\s*\u7ae0[\s:：\-—]*/i, '')
    .replace(/^Chapter\s*\d+[\s:：\-—]*/i, '')
    .trim()
  return cleaned || `续写章节 ${continuationForm.current_chapters + 1}`
}

async function handleSaveContinuation() {
  if (!continuationForm.project_id) {
    message.warning('请先选择项目')
    return
  }
  if (!continuationOutput.value.trim()) {
    message.warning('请先生成续写内容')
    return
  }

  continuationSaving.value = true
  try {
    const response = await apiClient.appendProjectChapter(continuationForm.project_id, {
      title: extractContinuationTitle(),
      content: continuationOutput.value,
      desc: continuationPlanning.value || '由续写助手生成'
    })
    continuationForm.current_chapters += 1
    await loadProjects()
    message.success(response.message || '章节已保存到项目')
  } catch (error) {
    notifyError(message, error)
  } finally {
    continuationSaving.value = false
  }
}

async function handlePromptCategoryChange() {
  try {
    promptSearchKeyword.value = ''
    const response = await apiClient.listPromptTemplates(promptForm.category)
    const names = response.data?.[promptForm.category] || []
    promptNameOptions.value = names.map(name => ({ label: name, value: name }))
    promptForm.name = names[0] || ''
    if (promptForm.name) {
      await handlePromptSelect(promptForm.name)
    } else {
      promptForm.content = ''
    }
  } catch (error) {
    notifyError(message, error)
  }
}

async function handlePromptSelect(name) {
  if (!name) {
    promptForm.content = ''
    return
  }

  try {
    const response = await apiClient.getPromptTemplate(promptForm.category, name)
    promptForm.content = response.data.content || ''
  } catch (error) {
    notifyError(message, error)
  }
}

async function handleSavePrompt() {
  if (!promptForm.name.trim()) {
    message.warning('请先选择或填写模板名')
    return
  }

  promptSaving.value = true
  try {
    const response = await apiClient.savePromptTemplate(promptForm)
    message.success(response.message || '提示词已保存')
    await handlePromptCategoryChange()
  } catch (error) {
    notifyError(message, error)
  } finally {
    promptSaving.value = false
  }
}

async function handleResetPrompt() {
  if (!promptForm.name.trim()) {
    message.warning('请先选择模板')
    return
  }

  promptResetting.value = true
  try {
    const response = await apiClient.resetPromptTemplate({
      category: promptForm.category,
      name: promptForm.name
    })
    promptForm.content = response.data.content || ''
    message.success(response.message || '提示词已重置')
  } catch (error) {
    notifyError(message, error)
  } finally {
    promptResetting.value = false
  }
}

watch(
  () => activeTab.value,
  async tab => {
    const nextTab = normalizeToolTab(tab)
    if (route.query.tab === nextTab) {
      return
    }
    await router.replace({
      query: {
        ...route.query,
        tab: nextTab
      }
    })
  }
)

watch(
  () => [route.query.projectId, route.query.tab, route.query.autoload],
  async () => {
    await applyRouteContext()
  }
)

onMounted(async () => {
  await Promise.all([loadProjects(), handlePromptCategoryChange()])
  await applyRouteContext()
})
</script>

<style scoped>
.file-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 10px 14px;
  border-radius: 16px;
  border: 1px dashed rgba(15, 118, 110, 0.35);
  background: rgba(15, 118, 110, 0.08);
  color: #0f766e;
  font-weight: 600;
  cursor: pointer;
}

.file-trigger input {
  display: none;
}
</style>
