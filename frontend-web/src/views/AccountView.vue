<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Account</p>
        <h1 class="hero-title">客户账号中心</h1>
        <p class="hero-copy">
          客户在这里查看会员等级、剩余配额、当前生成权限和平台策略，
          也可以直接回到自己的项目、任务和工具界面继续处理。
        </p>
        <div class="hero-actions">
          <n-button type="primary" @click="router.push({ name: 'Projects' })">我的项目</n-button>
          <n-button secondary @click="router.push({ name: 'Jobs' })">我的任务</n-button>
          <n-button secondary @click="router.push({ name: 'Workspace' })">回到工作台</n-button>
          <n-button secondary @click="handleLogout">退出系统</n-button>
        </div>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">当前账号</div>
          <div class="metric-value">{{ authStore.displayName }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">会员等级</div>
          <div class="metric-value">{{ authStore.subscriptionName }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">剩余配额</div>
          <div class="metric-value">{{ quotaText }}</div>
        </div>
      </div>
    </section>

    <BackendHelpCard
      v-if="backendStore.unavailable"
      title="账号中心当前无法连到后端"
      detail="会员状态、项目列表和任务列表都依赖后端服务。你仍可浏览界面，但需要后端在线后才能继续处理。"
    />

    <n-alert v-if="generationBlocked" type="warning" :show-icon="false">
      {{ authStore.generationMessage || '当前账号暂无生成权限，请联系管理员开通会员。' }}
    </n-alert>

    <n-alert v-if="loadingAccountData" type="info" :show-icon="false">
      正在同步账号资料、最近项目和任务结果。加载完成前，结果卡片会先显示占位状态。
    </n-alert>

    <section class="surface-card">
      <h2 class="section-heading">卡密兑换</h2>
      <p class="section-copy">输入管理员分发的卡密代码，即可兑换对应的会员时长或配额。</p>
      <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
        <n-input
          v-model:value="cardCode"
          placeholder="请输入卡密代码"
          :disabled="redeeming"
          style="flex:1; min-width:200px; max-width:360px;"
          @keyup.enter="handleRedeemCard"
        />
        <n-button
          type="primary"
          :loading="redeeming"
          :disabled="!cardCode.trim() || backendStore.unavailable"
          @click="handleRedeemCard"
        >
          兑换
        </n-button>
      </div>
    </section>

    <section class="split-grid">
      <article class="surface-card">
        <h2 class="section-heading">账号状态</h2>
        <div class="stack">
          <div class="inline-note">
            <strong>邮箱：</strong>
            <span>{{ authStore.user?.email || '未知' }}</span>
          </div>
          <div class="inline-note">
            <strong>角色：</strong>
            <span>{{ authStore.roleName }}</span>
          </div>
          <div class="inline-note">
            <strong>当前生成权限：</strong>
            <span>{{ authStore.canGenerate ? '可生成' : '不可生成' }}</span>
          </div>
          <div class="inline-note">
            <strong>生成说明：</strong>
            <span>{{ authStore.generationMessage || '暂无说明' }}</span>
          </div>
        </div>
      </article>

      <article class="surface-card surface-card--muted">
        <h2 class="section-heading">平台策略</h2>
        <div class="stack">
          <div class="inline-note">
            <strong>商业模式：</strong>
            <span>{{ platformStore.policy.commercial_mode ? '商业版' : '本地版' }}</span>
          </div>
          <div class="inline-note">
            <strong>生成策略：</strong>
            <span>{{ platformStore.policy.generation_mode === 'member_only' ? '仅会员可生成' : '允许免费生成' }}</span>
          </div>
          <div class="inline-note">
            <strong>注册状态：</strong>
            <span>{{ platformStore.policy.allow_registration ? '允许新用户注册' : '仅管理员可开通账号' }}</span>
          </div>
          <div class="inline-note">
            <strong>接口配置：</strong>
            <span>仅管理员可管理</span>
          </div>
          <div class="inline-note">
            <strong>提示词管理：</strong>
            <span>仅管理员可管理</span>
          </div>
        </div>
      </article>
    </section>

    <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">升级会员</h2>
          <p class="section-copy">当前仓库已提供本地可回归的升级闭环：客户可创建订单、完成沙盒支付或提交人工转账备注，后台确认后会员立即生效。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="selectedPaymentChannel" :options="paymentChannelOptions" style="width: 180px;" />
          <n-button secondary :loading="loadingAccountData" @click="loadAccountData">刷新订单</n-button>
        </div>
      </div>

      <div v-if="billingPlans.length" class="delivery-grid" style="margin-top:16px;">
        <article v-for="plan in billingPlans" :key="plan.tier" class="delivery-card">
          <div class="delivery-card__header">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ plan.name }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ plan.description }}
              </p>
            </div>
            <n-tag :type="plan.tier === authStore.subscriptionTier ? 'success' : 'info'" round>
              {{ plan.tier === authStore.subscriptionTier ? '当前档位' : `¥${plan.price}/月` }}
            </n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="success">
              {{ plan.is_unlimited ? '不限配额' : `每日 ${plan.daily_quota} 章` }}
            </n-tag>
            <n-tag size="small" :bordered="false">
              支付方式 {{ paymentChannelLabel(selectedPaymentChannel) }}
            </n-tag>
          </div>

          <div class="chapter-preview__item">
            <strong>升级说明</strong>
            <p class="section-copy" style="margin-top:8px;">
              {{ selectedPaymentChannel === 'sandbox_card' ? '会立即走本地沙盒支付并自动升级会员，适合回归和演示。' : '会先创建人工转账订单，提交付款备注后等待后台确认。' }}
            </p>
          </div>

          <div class="project-card__actions">
            <n-button
              type="primary"
              :disabled="planLocked(plan) || backendStore.unavailable"
              :loading="processingBillingTier === plan.tier"
              @click="handlePurchasePlan(plan)"
            >
              {{ planLocked(plan) ? '当前已拥有或高于该档位' : '创建升级订单' }}
            </n-button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前没有可用的会员升级方案。
      </div>
    </section>

    <section class="insight-grid">
      <article class="surface-card insight-card">
        <div class="insight-card__label">最近可交付结果</div>
        <div class="insight-card__value">{{ readyDeliveryCountText }}</div>
        <p class="insight-card__copy">已完成或已可下载的任务会优先出现在账号中心，方便客户直接回收结果。</p>
      </article>

      <article class="surface-card insight-card">
        <div class="insight-card__label">进行中任务</div>
        <div class="insight-card__value">{{ activeJobsCountText }}</div>
        <p class="insight-card__copy">排队中和生成中的任务会留在这里，客户回到账号中心就能看到当前进展。</p>
      </article>

      <article class="surface-card insight-card insight-card--accent">
        <div class="insight-card__label">在更项目</div>
        <div class="insight-card__value">{{ inProgressProjectCountText }}</div>
        <p class="insight-card__copy">还没写完的项目会继续保留在客户工作面，方便从结果直接进入下一步处理。</p>
      </article>
    </section>

    <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">最近可交付结果</h2>
          <p class="section-copy">优先展示已完成或已可下载的任务，客户回到账号中心后可以直接查看项目、继续润色续写或导出结果。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="jobDownloadFormat" :options="downloadOptions" style="width: 160px;" />
          <n-button secondary :loading="loadingAccountData" @click="loadAccountData">刷新</n-button>
        </div>
      </div>

      <div v-if="loadingAccountData && !accountDataLoaded" class="empty-state">
        正在加载可交付结果...
      </div>

      <div v-else-if="deliveryJobs.length" class="delivery-grid" style="margin-top:16px;">
        <article v-for="job in deliveryJobs" :key="job.id" class="delivery-card">
          <div class="delivery-card__header">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ displayTitle(job.title, '交付结果') }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ formatStatus(job.status) }} · {{ formatStep(job.current_step) }} · 更新于 {{ formatDate(job.updated_at) }}
              </p>
            </div>
            <n-tag :type="job.download_ready ? 'success' : 'info'" round>
              {{ job.download_ready ? '可下载' : '已完成' }}
            </n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="info">
              {{ deliveryProjectProgress(job.project_id) }}
            </n-tag>
            <n-tag size="small" :bordered="false" type="success">
              默认导出 {{ downloadLabel(job.export_format || 'txt') }}
            </n-tag>
            <n-tag size="small" :bordered="false" type="warning">
              进度 {{ job.progress || 0 }}%
            </n-tag>
          </div>

          <div class="chapter-preview__item">
            <strong>当前提示</strong>
            <p class="section-copy" style="margin-top:8px;">
              {{ job.message || '结果已就绪，可直接回到项目继续处理或导出。' }}
            </p>
          </div>

          <div class="delivery-card__footer">
            <span>{{ deliveryProjectTitle(job.project_id) }}</span>
            <span>{{ authStore.canGenerate ? '可继续生成' : '当前账号生成受限' }}</span>
          </div>

          <div class="project-card__actions">
            <n-button secondary @click="router.push({ name: 'Jobs' })">去任务中心</n-button>
            <n-button v-if="job.project_id" tertiary type="primary" @click="openProjectDetail(job.project_id)">
              查看项目
            </n-button>
            <n-button v-if="job.project_id" tertiary @click="openTools(job.project_id, 'polish')">
              去润色
            </n-button>
            <n-button v-if="job.project_id" tertiary @click="openTools(job.project_id, 'continuation')">
              去续写
            </n-button>
            <n-button
              v-if="job.download_ready && job.project_id"
              tertiary
              :disabled="backendStore.unavailable"
              @click="downloadProject(job.project_id, jobDownloadFormat)"
            >
              下载 {{ downloadLabel(jobDownloadFormat) }}
            </n-button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前还没有可交付结果。等后台任务完成后，账号中心会优先把可处理结果推到这里。
      </div>
    </section>

    <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">升级订单与账单</h2>
          <p class="section-copy">这里会显示你的最近升级订单和已生成账单，便于确认会员是否已经正式生效。</p>
        </div>
        <div class="result-actions">
          <n-button secondary :loading="loadingAccountData" @click="loadAccountData">刷新</n-button>
        </div>
      </div>

      <div v-if="recentBillingOrders.length" class="project-list" style="margin-top:16px;">
        <article v-for="order in recentBillingOrders" :key="order.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ order.target_name }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ order.order_no }} · {{ billingStatusLabel(order.status) }} · {{ formatDate(order.updated_at) }}
              </p>
            </div>
            <n-tag :type="billingStatusType(order.status)" round>
              {{ billingStatusLabel(order.status) }}
            </n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="info">
              {{ order.payment_channel_name }}
            </n-tag>
            <n-tag size="small" :bordered="false" type="success">
              ¥{{ order.amount }}
            </n-tag>
            <n-tag v-if="order.invoice_id" size="small" :bordered="false" type="warning">
              已出账单
            </n-tag>
          </div>

          <div class="inline-note">
            <strong>订单说明：</strong>
            <span>{{ order.note || '无附加备注' }}</span>
          </div>
          <div v-if="order.checkout_session?.instructions?.length" class="chapter-preview__item">
            <strong>{{ order.checkout_session.checkout_label || '支付指引' }}</strong>
            <p
              v-for="(instruction, index) in order.checkout_session.instructions"
              :key="`${order.id}-instruction-${index}`"
              class="section-copy"
              style="margin-top:8px;"
            >
              {{ instruction }}
            </p>
          </div>

          <div class="project-card__actions">
            <n-button
              v-if="order.status === 'pending_payment' && order.payment_channel === 'sandbox_card'"
              tertiary
              type="primary"
              :loading="processingOrderId === order.id"
              @click="handleSandboxPay(order)"
            >
              立即完成沙盒支付
            </n-button>
            <n-button
              v-if="order.status === 'pending_payment' && order.payment_channel === 'manual_transfer'"
              tertiary
              :loading="processingOrderId === order.id"
              @click="handleSubmitManualPayment(order)"
            >
              提交付款备注
            </n-button>
            <n-button
              v-if="['pending_payment', 'payment_submitted'].includes(order.status)"
              tertiary
              :loading="processingOrderId === order.id"
              @click="handleCancelBillingOrder(order)"
            >
              取消订单
            </n-button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前还没有升级订单。
      </div>

      <div v-if="recentInvoices.length" class="delivery-grid" style="margin-top:16px;">
        <article v-for="invoice in recentInvoices" :key="invoice.id" class="delivery-card">
          <div class="delivery-card__header">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ invoice.tier_name }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ invoice.invoice_no }} · {{ formatDate(invoice.issued_at) }}
              </p>
            </div>
            <n-tag type="success" round>已出账单</n-tag>
          </div>
          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="info">{{ invoice.payment_channel_name }}</n-tag>
            <n-tag size="small" :bordered="false" type="success">¥{{ invoice.amount }}</n-tag>
            <n-tag size="small" :bordered="false">{{ invoice.order_no }}</n-tag>
          </div>
          <div class="inline-note">
            <strong>账单说明：</strong>
            <span>{{ invoice.payment_channel_name }} · {{ invoice.tier_name }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">最近项目</h2>
          <p class="section-copy">生成完成后，客户可以直接回到这里打开自己的项目继续润色、续写或下载。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="projectDownloadFormat" :options="downloadOptions" style="width: 160px;" />
          <n-button secondary :loading="loadingAccountData" @click="loadAccountData">刷新</n-button>
        </div>
      </div>

      <div v-if="loadingAccountData && !accountDataLoaded" class="empty-state">
        正在加载最近项目...
      </div>

      <div v-else-if="recentProjects.length" class="project-list" style="margin-top:16px;">
        <article v-for="project in recentProjects" :key="project.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ displayTitle(project.title, '项目') }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ project.genre || '未分类' }} · 更新于 {{ formatDate(project.updated_at) }}
              </p>
            </div>
            <n-tag type="info" round>{{ project.completed_chapters || 0 }}/{{ project.total_chapters || 0 }}</n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="success">
              {{ formatWordCount(project.total_words) }}
            </n-tag>
            <n-tag size="small" :bordered="false">
              大纲 {{ project.outline_count || 0 }} 章
            </n-tag>
            <n-tag size="small" :bordered="false" type="warning">
              {{ formatLatestChapter(project) }}
            </n-tag>
          </div>

          <ProjectQuickActions
            :project-id="project.id"
            :download-format="projectDownloadFormat"
            :disable-download="backendStore.unavailable"
          />
        </article>
      </div>

      <div v-else class="empty-state">
        你当前还没有项目。可以去工作台开始创建，或等后台任务完成后回到这里查看。
      </div>
    </section>

    <section class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">最近任务</h2>
          <p class="section-copy">后台任务完成后，客户可以直接从账号中心回到项目详情、工具中心或下载结果。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="jobDownloadFormat" :options="downloadOptions" style="width: 160px;" />
          <n-button secondary :loading="loadingAccountData" @click="loadAccountData">刷新</n-button>
        </div>
      </div>

      <div v-if="loadingAccountData && !accountDataLoaded" class="empty-state">
        正在加载最近任务...
      </div>

      <div v-else-if="recentJobs.length" class="project-list" style="margin-top:16px;">
        <article v-for="job in recentJobs" :key="job.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ displayTitle(job.title, '任务') }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ formatStatus(job.status) }} · {{ formatStep(job.current_step) }} · {{ job.progress || 0 }}%
              </p>
            </div>
            <n-tag :type="jobTagType(job.status)" round>{{ formatStatus(job.status) }}</n-tag>
          </div>

          <div class="stack" style="margin-top:12px; gap:10px;">
            <div class="inline-note">
              <strong>当前提示：</strong>
              <span>{{ job.message || '等待调度' }}</span>
            </div>
            <div class="inline-note">
              <strong>更新时间：</strong>
              <span>{{ formatDate(job.updated_at) }}</span>
            </div>
          </div>

          <div class="project-card__actions">
            <n-button secondary @click="router.push({ name: 'Jobs' })">去任务中心</n-button>
            <n-button v-if="job.project_id" tertiary type="primary" @click="openProjectDetail(job.project_id)">
              查看项目
            </n-button>
            <n-button v-if="job.status === 'completed' && job.project_id" tertiary @click="openTools(job.project_id, 'polish')">
              去润色
            </n-button>
            <n-button v-if="job.status === 'completed' && job.project_id" tertiary @click="openTools(job.project_id, 'continuation')">
              去续写
            </n-button>
            <n-button
              v-if="job.download_ready && job.project_id"
              tertiary
              :disabled="backendStore.unavailable"
              @click="downloadProject(job.project_id, jobDownloadFormat)"
            >
              下载 {{ downloadLabel(jobDownloadFormat) }}
            </n-button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        你当前还没有任务记录。可以去工作台提交整本任务，稍后回到账号中心查看结果。
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NSelect, NTag, useMessage } from 'naive-ui'
import { apiClient } from '../api'
import BackendHelpCard from '../components/BackendHelpCard.vue'
import ProjectQuickActions from '../components/ProjectQuickActions.vue'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'
import { usePlatformStore } from '../stores/platform'
import { notifyError } from '../utils/errors'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const backendStore = useBackendStore()
const platformStore = usePlatformStore()

const allProjects = ref([])
const allJobs = ref([])
const billingPlans = ref([])
const billingOrders = ref([])
const invoices = ref([])
const paymentChannels = ref([])
const loadingAccountData = ref(false)
const accountDataLoaded = ref(false)
const projectDownloadFormat = ref('txt')
const jobDownloadFormat = ref('txt')
const selectedPaymentChannel = ref('sandbox_card')
const processingBillingTier = ref('')
const processingOrderId = ref('')
const cardCode = ref('')
const redeeming = ref(false)

const downloadOptions = [
  { label: 'TXT', value: 'txt' },
  { label: 'Markdown', value: 'md' },
  { label: 'HTML', value: 'html' },
  { label: 'Word', value: 'docx' },
  { label: 'JSON', value: 'json' }
]

const quotaText = computed(() => {
  if (authStore.remainingQuota >= 999999) return '不限'
  return String(authStore.remainingQuota)
})

const generationBlocked = computed(() => !authStore.canGenerate && !authStore.isBackoffice)
const recentProjects = computed(() => allProjects.value.slice(0, 5))
const recentJobs = computed(() => allJobs.value.slice(0, 5))
const recentBillingOrders = computed(() => billingOrders.value.slice(0, 5))
const recentInvoices = computed(() => invoices.value.slice(0, 4))
const deliveryJobs = computed(() =>
  allJobs.value
    .filter(job => job.download_ready || job.status === 'completed')
    .slice(0, 3)
)
const readyDeliveryCount = computed(() =>
  allJobs.value.filter(job => job.download_ready || job.status === 'completed').length
)
const activeJobsCount = computed(() =>
  allJobs.value.filter(job => job.status === 'queued' || job.status === 'running').length
)
const inProgressProjectCount = computed(() =>
  allProjects.value.filter(project => {
    const total = Number(project.total_chapters || project.chapter_count || 0)
    const completed = Number(project.completed_chapters || 0)
    return total > 0 && completed < total
  }).length
)
const readyDeliveryCountText = computed(() => {
  if (loadingAccountData.value && !accountDataLoaded.value) return '...'
  return String(readyDeliveryCount.value)
})
const activeJobsCountText = computed(() => {
  if (loadingAccountData.value && !accountDataLoaded.value) return '...'
  return String(activeJobsCount.value)
})
const inProgressProjectCountText = computed(() => {
  if (loadingAccountData.value && !accountDataLoaded.value) return '...'
  return String(inProgressProjectCount.value)
})
const projectLookup = computed(() =>
  new Map(allProjects.value.map(project => [project.id, project]))
)
const paymentChannelOptions = computed(() =>
  paymentChannels.value.map(channel => ({
    label: channel.label,
    value: channel.value
  }))
)
const tierRank = {
  free: 0,
  basic: 1,
  pro: 2
}

async function loadAccountData() {
  loadingAccountData.value = true

  const [
    projectsResponse,
    jobsResponse,
    profileResponse,
    policyResponse,
    billingPlansResponse,
    billingOrdersResponse,
    billingInvoicesResponse
  ] = await Promise.allSettled([
    apiClient.listProjects(),
    apiClient.listJobs(),
    authStore.refreshProfile(),
    platformStore.refreshPolicy(),
    apiClient.getBillingPlans(),
    apiClient.listBillingOrders(),
    apiClient.listBillingInvoices()
  ])

  try {
    const errors = []

    if (projectsResponse.status === 'fulfilled') {
      allProjects.value = projectsResponse.value.data || []
    } else {
      errors.push(projectsResponse.reason)
    }

    if (jobsResponse.status === 'fulfilled') {
      allJobs.value = jobsResponse.value.data || []
    } else {
      errors.push(jobsResponse.reason)
    }

    if (profileResponse.status === 'rejected') {
      errors.push(profileResponse.reason)
    }

    if (policyResponse.status === 'rejected') {
      errors.push(policyResponse.reason)
    }

    if (billingPlansResponse.status === 'fulfilled') {
      billingPlans.value = billingPlansResponse.value.data?.plans || []
      paymentChannels.value = billingPlansResponse.value.data?.payment_channels || []
      if (!paymentChannels.value.some(channel => channel.value === selectedPaymentChannel.value)) {
        selectedPaymentChannel.value = paymentChannels.value[0]?.value || 'sandbox_card'
      }
    } else {
      billingPlans.value = []
      paymentChannels.value = []
      errors.push(billingPlansResponse.reason)
    }

    if (billingOrdersResponse.status === 'fulfilled') {
      billingOrders.value = billingOrdersResponse.value.data || []
    } else {
      billingOrders.value = []
      errors.push(billingOrdersResponse.reason)
    }

    if (billingInvoicesResponse.status === 'fulfilled') {
      invoices.value = billingInvoicesResponse.value.data || []
    } else {
      invoices.value = []
      errors.push(billingInvoicesResponse.reason)
    }

    accountDataLoaded.value = true

    if (errors.length) {
      notifyError(message, errors[0], '账号中心有部分数据加载失败')
    }
  } finally {
    loadingAccountData.value = false
  }
}

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
  if (number && title) return `最近章节 第${number}章`
  if (title) return `最近章节 ${title}`
  return '最近章节 暂无'
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

function paymentChannelLabel(value) {
  return paymentChannels.value.find(channel => channel.value === value)?.label || value || '未知通道'
}

function planLocked(plan) {
  return (tierRank[plan.tier] || 0) <= (tierRank[authStore.subscriptionTier] || 0)
}

function billingStatusLabel(status) {
  return {
    pending_payment: '待付款',
    payment_submitted: '待确认',
    paid: '已支付',
    cancelled: '已取消'
  }[status] || status
}

function billingStatusType(status) {
  if (status === 'paid') return 'success'
  if (status === 'cancelled') return 'default'
  if (status === 'payment_submitted') return 'warning'
  return 'info'
}

function jobTagType(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'warning'
  return 'info'
}

function downloadLabel(format) {
  return downloadOptions.find(option => option.value === format)?.label || 'TXT'
}

function deliveryProjectTitle(projectId) {
  if (!projectId) return '未关联项目'
  const project = projectLookup.value.get(projectId)
  if (!project) return '项目信息暂未加载'
  return `关联项目 · ${displayTitle(project.title, '项目')}`
}

function deliveryProjectProgress(projectId) {
  if (!projectId) return '未关联项目'
  const project = projectLookup.value.get(projectId)
  if (!project) return '项目信息暂未加载'
  const completed = Number(project.completed_chapters || 0)
  const total = Number(project.total_chapters || project.chapter_count || 0)
  return total > 0 ? `项目进度 ${completed}/${total}` : '项目进度 暂无'
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

function downloadProject(projectId, format = 'txt') {
  window.open(apiClient.getProjectExportUrl(projectId, format), '_blank', 'noopener')
}

async function handlePurchasePlan(plan) {
  if (planLocked(plan)) {
    message.info('当前账号已经是该档位或更高档位')
    return
  }

  processingBillingTier.value = plan.tier
  try {
    const response = await apiClient.createBillingOrder({
      target_tier: plan.tier,
      payment_channel: selectedPaymentChannel.value,
      note: selectedPaymentChannel.value === 'sandbox_card' ? '账号中心沙盒升级' : '账号中心人工转账升级'
    })
    const order = response.data

    if (selectedPaymentChannel.value === 'sandbox_card') {
      await apiClient.sandboxPayBillingOrder(order.id)
      message.success(`已完成 ${plan.name} 的沙盒支付升级`)
    } else {
      message.success(response.message || '升级订单已创建，请提交付款备注')
    }

    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  } finally {
    processingBillingTier.value = ''
  }
}

async function handleSandboxPay(order) {
  processingOrderId.value = order.id
  try {
    const response = await apiClient.sandboxPayBillingOrder(order.id)
    message.success(response.message || '沙盒支付已完成')
    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  } finally {
    processingOrderId.value = ''
  }
}

async function handleSubmitManualPayment(order) {
  const paymentReference = window.prompt('请输入转账流水号或付款备注', order.payment_reference || '')
  if (!paymentReference) return

  processingOrderId.value = order.id
  try {
    const response = await apiClient.submitBillingPayment(order.id, { payment_reference: paymentReference })
    message.success(response.message || '付款备注已提交')
    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  } finally {
    processingOrderId.value = ''
  }
}

async function handleCancelBillingOrder(order) {
  processingOrderId.value = order.id
  try {
    const response = await apiClient.cancelBillingOrder(order.id, { note: '客户主动取消订单' })
    message.success(response.message || '订单已取消')
    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  } finally {
    processingOrderId.value = ''
  }
}

function handleLogout() {
  authStore.logout()
  message.success('已退出登录')
  router.push({ name: 'Home' })
}

async function handleRedeemCard() {
  const code = cardCode.value.trim()
  if (!code) return
  redeeming.value = true
  try {
    const response = await apiClient.redeemCardCode(code)
    message.success(response.message || '卡密兑换成功')
    cardCode.value = ''
    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  } finally {
    redeeming.value = false
  }
}

onMounted(async () => {
  try {
    await loadAccountData()
  } catch (error) {
    notifyError(message, error)
  }
})
</script>
