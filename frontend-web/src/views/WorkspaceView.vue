<template>
  <div class="page-stack">
    <!-- Welcome Banner -->
    <section class="ws-welcome">
      <div class="ws-welcome__content">
        <h1 class="ws-welcome__title">欢迎回来，{{ authStore.displayName }}!</h1>
        <p class="ws-welcome__greeting">{{ greetingText }}</p>
      </div>
      <n-tag
        :type="authStore.subscriptionTier === 'free' ? 'default' : 'success'"
        :bordered="false"
        size="large"
        round
      >
        {{ authStore.subscriptionName }}
      </n-tag>
    </section>

    <BackendHelpCard
      v-if="backendStore.unavailable"
      title="工作台当前无法连到后端"
      detail="快速建项、后台任务都依赖后端服务。请先启动后端再执行生成。"
    />

    <n-alert v-if="generationBlocked" type="warning" :show-icon="false" style="margin-bottom: 5px;">
      {{ authStore.generationMessage || '当前账号暂无生成权限，请联系管理员开通会员或调整平台策略。' }}
    </n-alert>

    <!-- Quick Start Form -->
    <section class="surface-card">
      <h2 class="section-heading">快速开始</h2>
      <p class="section-copy">创建新小说项目，填写基本信息后即可开始创作</p>
      <div class="ws-form-grid">
        <div class="stack">
          <n-input v-model:value="quickForm.title" placeholder="小说标题" size="large" maxlength="100" />
          <div class="ws-form-row">
            <n-select v-model:value="quickForm.genre" :options="genreOptions" placeholder="小说类型" />
            <n-select v-model:value="quickForm.style" :options="styleOptions" placeholder="写作风格" />
          </div>
          <n-input v-model:value="quickForm.character_setting" type="textarea" :rows="3" placeholder="角色设定（如：主角是一个穿越到异世界的程序员...）" />
          <n-input v-model:value="quickForm.world_setting" type="textarea" :rows="3" placeholder="世界观（如:科技与魔法并存的未来都市...）" />
        </div>
        <div class="stack">
          <div>
            <label class="ws-label">目标章节数</label>
            <n-input-number v-model:value="quickForm.chapter_count" :min="10" :max="500" style="width: 100%;" />
          </div>
          <n-input v-model:value="quickForm.plot_idea" type="textarea" :rows="7" placeholder="剧情构思（可选,描述你想要的故事走向...)" />
          <div class="result-actions">
            <n-button type="primary" size="large" :loading="quickLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handleQuickMode">
              开始创作
            </n-button>
            <n-button size="large" :loading="jobLoading" :disabled="backendStore.unavailable || generationBlocked" @click="handleSubmitJob">
              后台生成
            </n-button>
          </div>
        </div>
      </div>
    </section>

    <!-- Recent Projects -->
    <div class="ws-section-header">
      <h2 class="section-heading" style="margin: 0;">最近项目</h2>
      <n-button text type="primary" @click="router.push({ name: 'Projects' })">
        查看全部 &rarr;
      </n-button>
    </div>

    <div v-if="loadingProjects" class="ws-card-grid">
      <LoadingCard v-for="i in 3" :key="i" :rows="3" :show-footer="true" />
    </div>
    <div v-else-if="recentProjects.length" class="ws-card-grid">
      <div
        v-for="project in recentProjects"
        :key="project.id"
        class="ws-project-card"
        @click="openProject(project.id)"
      >
        <div class="ws-project-card__header">
          <h3 class="ws-project-card__title">{{ displayTitle(project.title, '项目') }}</h3>
          <n-tag size="small" round :bordered="false" type="info">{{ project.genre || '未分类' }}</n-tag>
        </div>
        <n-progress type="line" :percentage="projectProgress(project)" :show-indicator="false" :height="6" :border-radius="3" color="#6366f1" rail-color="#f1f5f9" />
        <div class="ws-project-card__meta">
          <span>{{ project.completed_chapters || 0 }}/{{ project.total_chapters || project.chapter_count || 0 }} 章</span>
          <span>{{ formatDateShort(project.updated_at) }}</span>
        </div>
      </div>
    </div>
    <EmptyState v-else title="还没有项目" description="填写上方表单创建你的第一个小说项目" />

    <!-- Active Jobs -->
    <div class="ws-section-header">
      <h2 class="section-heading" style="margin: 0;">进行中的任务</h2>
      <n-button text type="primary" @click="router.push({ name: 'Jobs' })">
        查看全部 &rarr;
      </n-button>
    </div>

    <div v-if="loadingJobs">
      <LoadingCard :rows="2" />
    </div>
    <div v-else-if="activeJobs.length" class="stack">
      <div v-for="job in activeJobs" :key="job.id" class="ws-job-card">
        <div class="ws-job-card__header">
          <div class="ws-job-card__info">
            <div class="ws-job-card__icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 1 4 19.5v-15A2.5 0 1 19.5z"/></svg>
            </div>
            <div>
              <h4 class="ws-job-card__title">{{ displayTitle(job.title, '任务') }}</h4>
              <p class="ws-job-card__step">{{ formatStep(job.current_step) }}</p>
            </div>
          </div>
          <n-tag size="small" round :type="jobStatusType(job.status)">{{ job.progress || 0 }}%</n-tag>
        </div>
        <n-progress type="line" :percentage="job.progress || 0" :height="8" :border-radius="4" color="#6366f1" rail-color="#f1f5f9" />
        <div style="margin-top: 8px; font-size: 0.8rem; color: #94a3b8;">
          {{ job.message || '等待调度' }}
        </div>
      </div>
    </div>
    <EmptyState v-else title="暂无进行中的任务" description="提交后台生成任务后，进度会显示在这里" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NSelect, NInputNumber, NTag, NProgress, NAlert } from 'naive-ui'
import { apiClient } from '../api'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'
import EmptyState from '../components/common/EmptyState.vue'
import LoadingCard from '../components/common/LoadingCard.vue'
import BackendHelpCard from '../components/BackendHelpCard.vue'

const router = useRouter()
const authStore = useAuthStore()
const backendStore = useBackendStore()

// 快速开始表单
const quickForm = ref({
  title: '',
  genre: '玄幻',
  character_setting: '',
  world_setting: '',
  chapter_count: 50,
  plot_idea: '',
  style: '玄幻仙侠',
})
const quickLoading = ref(false)
const jobLoading = ref(false)

// 类型选项
const genreOptions = [
  { label: '玄幻', value: '玄幻' },
  { label: '仙侠', value: '仙侠' },
  { label: '都市', value: '都市' },
  { label: '言情', value: '言情' },
  { label: '悬疑', value: '悬疑' },
  { label: '推理', value: '推理' },
  { label: '历史', value: '历史' },
  { label: '穿越', value: '穿越' },
  { label: '科幻', value: '科幻' },
  { label: '武侠', value: '武侠' },
  { label: '现实', value: '现实' },
  { label: '轻小说', value: '轻小说' },
]
const styleOptions = genreOptions  // 同样的选项

// 项目和任务
const loadingProjects = ref(true)
const loadingJobs = ref(true)
const recentProjects = ref([])
const activeJobs = ref([])
const generationBlocked = computed(() => !authStore.canGenerate)

// 问候语
const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了，注意休息'
  if (hour < 12) return '今天想写什么样的故事？'
  if (hour < 18) return '下午好，继续你的创作之旅'
  return '晚上好，灵感来了吗？'
})

// 获取数据
async function loadProjects() {
  loadingProjects.value = true
  try {
    const res = await apiClient.listProjects()
    recentProjects.value = (res.data || []).slice(0, 6)
  } catch { /* ignore */ }
  loadingProjects.value = false
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    const res = await apiClient.listJobs()
    activeJobs.value = (res.data || []).filter(j => j.status === 'running' || j.status === 'queued').slice(0, 3)
  } catch { /* ignore */ }
  loadingJobs.value = false
}

// 快速生成
async function handleQuickMode() {
  if (!quickForm.value.title.trim()) return
  quickLoading.value = true
  try {
    await apiClient.generateQuickOutline(quickForm.value)
    router.push({ name: 'Projects' })
  } catch (e) {
    console.error(e)
  }
  quickLoading.value = false
}

async function handleSubmitJob() {
  if (!quickForm.value.title.trim()) return
  jobLoading.value = true
  try {
    await apiClient.createFullGenerationJob(quickForm.value)
    router.push({ name: 'Jobs' })
  } catch (e) {
    console.error(e)
  }
  jobLoading.value = false
}

function openProject(id) {
  router.push({ name: 'ProjectDetail', params: { projectId: id } })
}

function projectProgress(p) {
  const total = p.chapter_count || 0
  const done = p.chapters?.length || 0
  return total > 0 ? Math.round((done / total) * 100) : 0
}

function displayTitle(title, fallback) {
  const text = String(title || '').trim()
  if (!text || /^\?+$/.test(text)) return `${fallback}记录`
  return text
}

function formatDateShort(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return d }
}

function formatStep(step) {
  const map = {
    queued: '排队中',
    running: '生成中',
    outline: '生成大纲',
    chapters: '生成章节',
    completed: '已完成',
    failed: '失败',
  }
  return map[step] || step || ''
}

function jobStatusType(status) {
  const map = {
    running: 'info',
    queued: 'warning',
    completed: 'success',
    failed: 'error',
  }
  return map[status] || 'default'
}

let refreshTimer = null
onMounted(() => {
  loadProjects()
  loadJobs()
  refreshTimer = setInterval(loadJobs, 10000)
})
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.ws-welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 30px;
  border-radius: 24px;
  background:
    linear-gradient(160deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08)),
    var(--panel-light);
  border: 1px solid rgba(99, 102, 241, 0.16);
  box-shadow: var(--shadow-card);
  flex-wrap: wrap;
}

.ws-welcome__title {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
  color: #0f172a;
}

.ws-welcome__greeting {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.95rem;
}

.ws-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ws-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.ws-form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.ws-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.88rem;
  font-weight: 500;
  color: #475569;
}

.ws-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.ws-project-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.16);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.ws-project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.1);
  border-color: rgba(99, 102, 241, 0.22);
}

.ws-project-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.ws-project-card__title {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 600;
  color: #0f172a;
}

.ws-project-card__meta {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 0.82rem;
  color: #64748b;
}

.ws-job-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.16);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.ws-job-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.1);
  border-color: rgba(99, 102, 241, 0.22);
}

.ws-job-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.ws-job-card__info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ws-job-card__icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.08));
  color: #6366f1;
  flex-shrink: 0;
}

.ws-job-card__title {
  margin: 0;
  font-size: 0.96rem;
  font-weight: 600;
  color: #0f172a;
}

.ws-job-card__step {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: #64748b;
}

@media (max-width: 960px) {
  .ws-form-grid {
    grid-template-columns: 1fr;
  }

  .ws-welcome {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
