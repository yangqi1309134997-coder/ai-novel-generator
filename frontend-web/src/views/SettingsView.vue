<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-eyebrow">Admin Console</p>
        <h1 class="hero-title">商业版后台控制台</h1>
        <p class="hero-copy">
          这里是后台团队工作面。管理员、运营和客服可以按角色权限查看不同模块；
          客户账号不参与接口配置，只负责使用工作台、项目和任务。
        </p>
      </div>

      <div class="hero-aside">
        <div class="metric-card">
          <div class="metric-label">生成策略</div>
          <div class="metric-value">{{ policyForm.generation_mode === 'member_only' ? '仅会员' : '免费开放' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">当前提供商</div>
          <div class="metric-value">{{ selectedProvider?.name || '未选择' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">客户数</div>
          <div class="metric-value">{{ customerCountText }}</div>
          <div class="metric-label">{{ customerSummaryText }}</div>
        </div>
      </div>
    </section>

    <n-alert v-if="loadingAdminData" type="info" :show-icon="false">
      正在同步后台配置、接口信息、权限账号和审计日志。加载完成前，概览卡片会先显示占位状态。
    </n-alert>

    <div v-if="canViewPolicy || canViewApiConfig" class="split-grid">
      <section v-if="canViewPolicy" class="surface-card">
        <h2 class="section-heading">平台策略</h2>
        <div class="stack">
          <n-select v-model:value="policyForm.generation_mode" :options="generationModeOptions" :disabled="!canEditPolicy" />
          <n-select v-model:value="policyForm.default_subscription_tier" :options="tierOptions" :disabled="!canEditPolicy" />
          <n-switch v-model:value="policyForm.allow_registration" :disabled="!canEditPolicy">
            <template #checked>允许客户自行注册</template>
            <template #unchecked>仅管理员可开通账号</template>
          </n-switch>
          <n-select
            v-model:value="policyForm.member_tiers_allowed"
            :options="memberTierOptions"
            :disabled="!canEditPolicy"
            multiple
            placeholder="可生成的会员等级"
          />

          <div class="chapter-preview__item">
            <strong>运营预设</strong>
            <p class="section-copy" style="margin-top:8px;">
              点击后只会改当前表单，不会立刻生效。确认策略影响后再保存，适合快速切换常见商业化场景。
            </p>
            <div class="result-actions" style="margin-top:12px;">
              <n-button tertiary :disabled="!canEditPolicy" @click="applyPolicyPreset('growth')">开放拉新</n-button>
              <n-button tertiary :disabled="!canEditPolicy" @click="applyPolicyPreset('conversion')">会员转化</n-button>
              <n-button tertiary :disabled="!canEditPolicy" @click="applyPolicyPreset('invite_only')">邀请制运营</n-button>
            </div>
          </div>

          <div class="inline-note">
            <strong>后台边界：</strong>
            <span>接口配置和提示词模板固定由管理员统一维护，客户不开放这些能力。</span>
          </div>
          <div v-if="!canEditPolicy" class="inline-note">
            <strong>当前模式：</strong>
            <span>你当前只有查看权限，不能修改平台策略。</span>
          </div>

          <div class="result-actions">
            <n-button type="primary" :loading="savingPolicy" :disabled="!canEditPolicy" @click="handleSavePolicy">
              保存平台策略
            </n-button>
            <n-button secondary :loading="loadingAdminData" @click="loadAdminData">
              重新读取后台配置
            </n-button>
          </div>
        </div>
      </section>

      <section v-if="canViewApiConfig" class="surface-card surface-card--muted">
        <h2 class="section-heading">模型接口配置</h2>
        <div class="stack">
          <n-select
            v-model:value="apiForm.provider"
            :options="providerOptions"
            :disabled="!canManageApiConfig"
            placeholder="选择提供商"
            @update:value="handleProviderChange"
          />
          <n-select v-model:value="apiForm.model" :options="modelOptions" :disabled="!canManageApiConfig" placeholder="选择模型" />
          <n-input v-model:value="apiForm.base_url" :disabled="!canManageApiConfig" placeholder="Base URL" />
          <n-input
            v-model:value="apiForm.api_key"
            :disabled="!canManageApiConfig"
            type="password"
            show-password-on="click"
            placeholder="API Key，留空则继续使用已保存的 Key"
          />

          <div v-if="currentConfig?.has_api_key" class="inline-note">
            <strong>已保存 Key：</strong>
            <span>{{ currentConfig.api_key_masked }}</span>
          </div>

          <div class="result-actions">
            <n-button type="primary" :loading="savingConfig" :disabled="!canManageApiConfig" @click="handleSaveConfig">
              保存接口配置
            </n-button>
            <n-button secondary :loading="testing" :disabled="!canTestApiConfig" @click="handleTestConfig">
              测试连接
            </n-button>
          </div>

          <div v-if="!canManageApiConfig" class="inline-note">
            <strong>当前模式：</strong>
            <span>你当前只有查看权限，不能修改接口配置。</span>
          </div>

          <div v-if="testResult" class="chapter-preview__item">
            <strong>最近测试结果</strong>
            <p class="section-copy" style="margin-top:8px; white-space: pre-wrap;">{{ testResult }}</p>
          </div>
        </div>
      </section>
    </div>

    <section v-if="canViewPolicy && canViewUsers" class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">策略影响概览</h2>
          <p class="section-copy">这里直接汇总当前表单策略对客户侧的影响，管理员保存前就能预估账号中心和工作台会发生什么变化。</p>
        </div>
        <n-tag :type="policyForm.allow_registration ? 'success' : 'warning'" round>
          {{ policyForm.allow_registration ? '开放注册' : '邀请制运营' }}
        </n-tag>
      </div>

      <div class="insight-grid" style="margin-top:16px;">
        <article class="surface-card insight-card">
          <div class="insight-card__label">可生成客户</div>
          <div class="insight-card__value">{{ generatableCustomerCount }}</div>
          <p class="insight-card__copy">当前用户列表里，能直接进入工作台继续生成的客户数量。</p>
        </article>

        <article class="surface-card insight-card">
          <div class="insight-card__label">受限客户</div>
          <div class="insight-card__value">{{ restrictedCustomerCount }}</div>
          <p class="insight-card__copy">这些客户登录后会在账号中心和工作台看到生成受限提示，适合做会员转化跟进。</p>
        </article>

        <article class="surface-card insight-card">
          <div class="insight-card__label">付费客户</div>
          <div class="insight-card__value">{{ payingCustomerCount }}</div>
          <p class="insight-card__copy">当前已是基础或专业会员的客户数量，适合对照策略观察运营存量。</p>
        </article>

        <article class="surface-card insight-card insight-card--accent">
          <div class="insight-card__label">新注册默认等级</div>
          <div class="insight-card__value">{{ defaultSubscriptionLabel }}</div>
          <p class="insight-card__copy">可生成会员等级：{{ memberTierSummary }}</p>
        </article>
      </div>

      <div class="inline-note" style="margin-top:16px;">
        <strong>当前判断：</strong>
        <span>{{ policyImpactSummary }}</span>
      </div>
    </section>

    <section v-if="canViewUsers" class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">账号与权限管理</h2>
          <p class="section-copy">后台团队可以查看全部账号；具备更高权限的角色可以直接调整客户会员状态与后台角色。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="userRoleFilter" :options="userRoleOptions" style="width: 160px;" />
          <n-select v-model:value="userTierFilter" :options="userTierFilterOptions" style="width: 160px;" />
          <n-button secondary :loading="loadingUsers" @click="loadAdminUsers">
            刷新用户列表
          </n-button>
        </div>
      </div>

      <div class="result-actions" style="margin-top:16px;">
        <n-input v-model:value="userSearchKeyword" clearable placeholder="搜索用户名或邮箱" />
      </div>

      <div v-if="loadingUsers && !users.length" class="empty-state">
        正在加载客户账号数据...
      </div>

      <div v-else-if="filteredUsers.length" class="project-list" style="margin-top:16px;">
        <article v-for="user in filteredUsers" :key="user.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ user.username || user.email }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ user.email }} · {{ user.role_name || user.role }}
              </p>
            </div>
            <n-tag :type="user.can_generate ? 'success' : 'warning'" round>
              {{ user.can_generate ? '可生成' : '不可生成' }}
            </n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="default">
              {{ user.role_name || user.role }}
            </n-tag>
            <n-tag size="small" :bordered="false" type="info">
              {{ user.subscription_name || user.subscription_tier }}
            </n-tag>
            <n-tag size="small" :bordered="false">
              剩余 {{ formatQuota(user.remaining_quota) }}
            </n-tag>
            <n-tag size="small" :bordered="false" :type="user.is_active ? 'success' : 'error'">
              {{ user.is_active ? '已启用' : '已禁用' }}
            </n-tag>
          </div>

          <div class="inline-note">
            <strong>生成说明：</strong>
            <span>{{ user.generation_message }}</span>
          </div>
          <div v-if="user.role !== 'customer'" class="inline-note">
            <strong>后台角色说明：</strong>
            <span>后台团队账号不参与客户会员和配额运营，主要用于运营、客服或平台管理。</span>
          </div>

          <div class="result-actions">
            <n-select
              v-if="canEditUserRoles"
              :value="user.role"
              :options="roleOptions"
              style="width: 160px;"
              @update:value="value => handleUpdateUserRole(user, value)"
            />
            <n-select
              :value="user.subscription_tier"
              :options="tierOptions"
              style="width: 160px;"
              :disabled="!canEditMembership(user)"
              @update:value="value => handleUpdateUser(user, { subscription_tier: value, is_active: user.is_active })"
            />
            <n-switch
              :value="user.is_active"
              :disabled="!canEditMembership(user)"
              @update:value="value => handleUpdateUser(user, { subscription_tier: user.subscription_tier, is_active: value })"
            >
              <template #checked>启用</template>
              <template #unchecked>禁用</template>
            </n-switch>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前筛选条件下没有用户账号数据。
      </div>
    </section>

    <section v-if="canViewBilling" class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">升级订单管理</h2>
          <p class="section-copy">这里汇总客户创建的升级订单。客服可查看状态，运营和管理员可确认人工转账到账并让会员立即生效。</p>
        </div>
        <div class="result-actions">
          <n-button secondary :loading="loadingBillingOrders" @click="loadBillingOrders">刷新订单</n-button>
        </div>
      </div>

      <div v-if="loadingBillingOrders && !billingOrders.length" class="empty-state">
        正在加载升级订单...
      </div>

      <div v-else-if="recentBillingOrders.length" class="project-list" style="margin-top:16px;">
        <article v-for="order in recentBillingOrders" :key="order.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ order.target_name }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ order.order_no }} · {{ order.user_email }} · {{ formatDate(order.updated_at) }}
              </p>
            </div>
            <n-tag :type="billingStatusType(order.status)" round>
              {{ billingStatusLabel(order.status) }}
            </n-tag>
          </div>

          <div class="project-card__meta">
            <n-tag size="small" :bordered="false" type="info">{{ order.payment_channel_name }}</n-tag>
            <n-tag size="small" :bordered="false" type="success">¥{{ order.amount }}</n-tag>
            <n-tag size="small" :bordered="false">{{ order.current_tier }} -> {{ order.target_tier }}</n-tag>
          </div>

          <div class="inline-note">
            <strong>付款备注：</strong>
            <span>{{ order.payment_reference || '客户尚未提交付款备注' }}</span>
          </div>
          <div class="inline-note">
            <strong>订单说明：</strong>
            <span>{{ order.note || '无附加备注' }}</span>
          </div>
          <div v-if="order.checkout_session?.instructions?.length" class="chapter-preview__item">
            <strong>{{ order.checkout_session.checkout_label || '支付指引' }}</strong>
            <p
              v-for="(instruction, index) in order.checkout_session.instructions"
              :key="`${order.id}-admin-instruction-${index}`"
              class="section-copy"
              style="margin-top:8px;"
            >
              {{ instruction }}
            </p>
          </div>

          <div class="project-card__actions">
            <n-button
              v-if="canManageBilling && order.payment_channel === 'manual_transfer' && ['pending_payment', 'payment_submitted'].includes(order.status)"
              tertiary
              type="primary"
              @click="handleApproveBillingOrder(order)"
            >
              确认到账并升级
            </n-button>
            <n-button
              v-if="canManageBilling && ['pending_payment', 'payment_submitted'].includes(order.status)"
              tertiary
              @click="handleCancelManagedBillingOrder(order)"
            >
              取消订单
            </n-button>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前还没有升级订单。
      </div>
    </section>

    <section v-if="canViewAuditLogs" class="surface-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <h2 class="section-heading">后台审计日志</h2>
          <p class="section-copy">记录登录、策略变更、角色调整、会员变更和接口配置操作，便于团队追溯后台行为。</p>
        </div>
        <div class="result-actions">
          <n-select v-model:value="auditRoleFilter" :options="auditRoleOptions" style="width: 160px;" />
          <n-input v-model:value="auditActionFilter" clearable placeholder="按动作前缀过滤，如 admin.user" />
          <n-button secondary :loading="loadingAuditLogs" @click="loadAuditLogs">刷新日志</n-button>
        </div>
      </div>

      <div v-if="loadingAuditLogs && !auditLogs.length" class="empty-state">
        正在加载审计日志...
      </div>

      <div v-else-if="auditLogs.length" class="project-list" style="margin-top:16px;">
        <article v-for="log in auditLogs" :key="log.id" class="project-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h3 style="margin:0; font-size:1.05rem;">{{ formatAuditAction(log.action) }}</h3>
              <p style="margin:8px 0 0; color:#64748b;">
                {{ formatAuditActor(log) }} · {{ formatAuditTime(log.timestamp) }}
              </p>
            </div>
            <n-tag :type="auditStatusType(log.status)" round>
              {{ formatAuditStatus(log.status) }}
            </n-tag>
          </div>

          <div class="stack" style="margin-top:12px; gap:10px;">
            <div class="inline-note">
              <strong>目标：</strong>
              <span>{{ log.target_label || log.target_type || '未标记' }}</span>
            </div>
            <div class="inline-note">
              <strong>动作代码：</strong>
              <span>{{ log.action }}</span>
            </div>
            <div class="inline-note" v-if="log.message">
              <strong>说明：</strong>
              <span>{{ log.message }}</span>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        当前筛选条件下没有审计日志。
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { NAlert, NButton, NInput, NSelect, NSwitch, NTag, useMessage } from 'naive-ui'
import { apiClient } from '../api'
import { useAuthStore } from '../stores/auth'
import { notifyError } from '../utils/errors'

const message = useMessage()
const authStore = useAuthStore()

const providers = ref([])
const currentConfig = ref(null)
const users = ref([])
const roleOptions = ref([
  { label: '客户用户', value: 'customer', permissions: [] },
  { label: '客服支持', value: 'support', permissions: ['backoffice.view', 'billing.view_all', 'users.view', 'audit.view'] },
  { label: '运营人员', value: 'operator', permissions: ['backoffice.view', 'policy.view', 'policy.edit', 'users.view', 'billing.view_all', 'billing.manage'] },
  { label: '管理员', value: 'admin', permissions: ['backoffice.view', 'policy.view', 'policy.edit', 'users.view', 'users.role.edit', 'billing.view_all', 'billing.manage'] }
])
const auditLogs = ref([])
const billingOrders = ref([])
const savingConfig = ref(false)
const savingPolicy = ref(false)
const testing = ref(false)
const loadingAdminData = ref(false)
const loadingUsers = ref(false)
const loadingAuditLogs = ref(false)
const loadingBillingOrders = ref(false)
const adminDataLoaded = ref(false)
const testResult = ref('')
const userSearchKeyword = ref('')
const userRoleFilter = ref('all')
const userTierFilter = ref('all')
const auditRoleFilter = ref('all')
const auditActionFilter = ref('')

const apiForm = reactive({
  provider: '',
  model: '',
  base_url: '',
  api_key: ''
})

const policyForm = reactive({
  allow_registration: true,
  generation_mode: 'free',
  member_tiers_allowed: ['basic', 'pro'],
  default_subscription_tier: 'free'
})

const generationModeOptions = [
  { label: '允许免费生成', value: 'free' },
  { label: '仅会员可生成', value: 'member_only' }
]

const tierOptions = [
  { label: '免费用户', value: 'free' },
  { label: '基础会员', value: 'basic' },
  { label: '专业会员', value: 'pro' }
]

const memberTierOptions = tierOptions.filter(item => item.value !== 'free')

const userTierFilterOptions = [
  { label: '全部会员', value: 'all' },
  ...tierOptions
]

const canViewPolicy = computed(() => authStore.hasPermission('policy.view'))
const canEditPolicy = computed(() => authStore.hasPermission('policy.edit'))
const canViewApiConfig = computed(() => authStore.hasPermission('api_config.view'))
const canManageApiConfig = computed(() => authStore.hasPermission('api_config.edit'))
const canTestApiConfig = computed(() => authStore.hasPermission('api_config.test'))
const canViewUsers = computed(() => authStore.hasPermission('users.view'))
const canManageUsers = computed(() => authStore.hasPermission('users.membership.edit'))
const canEditUserRoles = computed(() => authStore.hasPermission('users.role.edit'))
const canViewBilling = computed(() => authStore.hasPermission('billing.view_all'))
const canManageBilling = computed(() => authStore.hasPermission('billing.manage'))
const canViewAuditLogs = computed(() => authStore.hasPermission('audit.view'))

const userRoleOptions = computed(() => [
  { label: '全部角色', value: 'all' },
  ...roleOptions.value.map(item => ({ label: item.label, value: item.value }))
])

const auditRoleOptions = computed(() => [
  { label: '全部操作者', value: 'all' },
  ...roleOptions.value.map(item => ({ label: item.label, value: item.value })),
  { label: '匿名', value: 'anonymous' }
])

const providerOptions = computed(() =>
  providers.value.map(item => ({
    label: `${item.icon || 'API'} ${item.name}`,
    value: item.id
  }))
)

const selectedProvider = computed(() =>
  providers.value.find(item => item.id === apiForm.provider) || null
)

const modelOptions = computed(() =>
  (selectedProvider.value?.models || []).map(item => ({
    label: item,
    value: item
  }))
)

const customerUsers = computed(() => users.value.filter(user => user.role === 'customer'))
const payingCustomerCount = computed(() =>
  customerUsers.value.filter(user => user.subscription_tier !== 'free').length
)
const generatableCustomerCount = computed(() =>
  customerUsers.value.filter(user => user.can_generate).length
)
const restrictedCustomerCount = computed(() =>
  customerUsers.value.filter(user => user.is_active && !user.can_generate).length
)
const customerCountText = computed(() => {
  if (loadingAdminData.value && !adminDataLoaded.value) return '...'
  return String(customerUsers.value.length)
})
const customerSummaryText = computed(() => {
  if (loadingAdminData.value && !adminDataLoaded.value) return '客户策略同步中'
  return `可生成 ${generatableCustomerCount.value} / 受限 ${restrictedCustomerCount.value}`
})
const defaultSubscriptionLabel = computed(() =>
  tierOptions.find(item => item.value === policyForm.default_subscription_tier)?.label || '免费用户'
)
const memberTierSummary = computed(() => {
  if (!policyForm.member_tiers_allowed?.length) return '当前未开放任何会员等级'
  return policyForm.member_tiers_allowed
    .map(tier => tierOptions.find(item => item.value === tier)?.label || tier)
    .join('、')
})
const policyImpactSummary = computed(() => {
  if (loadingAdminData.value && !adminDataLoaded.value) {
    return '后台策略和客户列表正在同步，完成后这里会显示真实影响范围。'
  }

  const registrationText = policyForm.allow_registration
    ? '当前允许客户自行注册'
    : '当前关闭公开注册，仅管理员可开通账号'
  const generationText = policyForm.generation_mode === 'member_only'
    ? `平台将只允许 ${memberTierSummary.value} 生成，当前有 ${restrictedCustomerCount.value} 位活跃客户会被限制`
    : '平台允许免费生成，客户登录后不会因为会员策略被拦住'

  return `${registrationText}；${generationText}；新注册用户默认会拿到“${defaultSubscriptionLabel.value}”档位。`
})

const filteredUsers = computed(() => {
  const keyword = userSearchKeyword.value.trim().toLowerCase()
  let list = [...users.value]

  if (userRoleFilter.value !== 'all') {
    list = list.filter(user => user.role === userRoleFilter.value)
  }

  if (userTierFilter.value !== 'all') {
    list = list.filter(user => user.subscription_tier === userTierFilter.value)
  }

  if (keyword) {
    list = list.filter(user => {
      const haystack = `${user.username || ''} ${user.email || ''}`.toLowerCase()
      return haystack.includes(keyword)
    })
  }

  return list
})
const recentBillingOrders = computed(() => billingOrders.value.slice(0, 8))

function handleProviderChange(providerId) {
  const provider = providers.value.find(item => item.id === providerId)
  if (!provider) return
  apiForm.base_url = provider.base_url || ''
  apiForm.model = provider.default_model || provider.models?.[0] || ''
}

function applyPolicyPreset(preset) {
  if (preset === 'growth') {
    policyForm.allow_registration = true
    policyForm.generation_mode = 'free'
    policyForm.default_subscription_tier = 'free'
    policyForm.member_tiers_allowed = ['basic', 'pro']
    return
  }

  if (preset === 'conversion') {
    policyForm.allow_registration = true
    policyForm.generation_mode = 'member_only'
    policyForm.default_subscription_tier = 'free'
    policyForm.member_tiers_allowed = ['basic', 'pro']
    return
  }

  policyForm.allow_registration = false
  policyForm.generation_mode = 'member_only'
  policyForm.default_subscription_tier = 'basic'
  policyForm.member_tiers_allowed = ['basic', 'pro']
}

function formatQuota(value) {
  return Number(value) >= 999999 ? '不限' : String(Number(value) || 0)
}

function formatDate(value) {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function resolveRoleLabel(role) {
  return roleOptions.value.find(item => item.value === role)?.label || role || '未知角色'
}

function canEditMembership(user) {
  return canManageUsers.value && user.role === 'customer'
}

function buildAuditParams() {
  const params = { limit: 40 }
  if (auditRoleFilter.value !== 'all') {
    params.actor_role = auditRoleFilter.value
  }
  if (auditActionFilter.value.trim()) {
    params.action_prefix = auditActionFilter.value.trim()
  }
  return params
}

async function loadAdminData() {
  loadingAdminData.value = true
  loadingUsers.value = true

  const [policyResponse, providersResponse, configResponse, usersResponse, rolesResponse, billingResponse] = await Promise.allSettled([
    canViewPolicy.value ? apiClient.getAdminPolicy() : Promise.resolve({ data: {} }),
    canViewApiConfig.value ? apiClient.listProviders() : Promise.resolve({ data: [] }),
    canViewApiConfig.value ? apiClient.getApiConfig() : Promise.resolve({ data: null }),
    canViewUsers.value ? apiClient.listAdminUsers() : Promise.resolve({ data: [] }),
    canEditUserRoles.value ? apiClient.listAdminRoles() : Promise.resolve({ data: roleOptions.value }),
    canViewBilling.value ? apiClient.listBillingOrders() : Promise.resolve({ data: [] })
  ])

  try {
    const errors = []

    if (policyResponse.status === 'fulfilled' && canViewPolicy.value) {
      Object.assign(policyForm, policyResponse.value.data || {})
    } else if (policyResponse.status === 'rejected') {
      errors.push(policyResponse.reason)
    }

    if (providersResponse.status === 'fulfilled' && canViewApiConfig.value) {
      providers.value = providersResponse.value.data || []
    } else {
      providers.value = []
      if (providersResponse.status === 'rejected') {
        errors.push(providersResponse.reason)
      }
    }

    if (configResponse.status === 'fulfilled' && canViewApiConfig.value) {
      currentConfig.value = configResponse.value.data
      if (currentConfig.value) {
        apiForm.provider = currentConfig.value.provider
        apiForm.model = currentConfig.value.model
        apiForm.base_url = currentConfig.value.base_url
        apiForm.api_key = ''
      }
    } else {
      currentConfig.value = null
      if (configResponse.status === 'rejected') {
        errors.push(configResponse.reason)
      }
    }

    if (canViewApiConfig.value && !currentConfig.value && providers.value.length) {
      apiForm.provider = providers.value[0].id
      handleProviderChange(providers.value[0].id)
    }

    if (usersResponse.status === 'fulfilled' && canViewUsers.value) {
      users.value = usersResponse.value.data || []
    } else {
      users.value = []
      if (usersResponse.status === 'rejected') {
        errors.push(usersResponse.reason)
      }
    }

    if (rolesResponse.status === 'fulfilled' && canEditUserRoles.value) {
      roleOptions.value = (rolesResponse.value.data || []).map(item => ({
        label: item.label,
        value: item.value,
        permissions: item.permissions || []
      }))
    } else if (rolesResponse.status === 'rejected') {
      errors.push(rolesResponse.reason)
    }

    if (billingResponse.status === 'fulfilled' && canViewBilling.value) {
      billingOrders.value = billingResponse.value.data || []
    } else {
      billingOrders.value = []
      if (billingResponse.status === 'rejected') {
        errors.push(billingResponse.reason)
      }
    }

    adminDataLoaded.value = true

    if (canViewAuditLogs.value) {
      await loadAuditLogs()
    } else {
      auditLogs.value = []
    }

    if (errors.length) {
      notifyError(message, errors[0], '后台配置有部分数据加载失败')
    }
  } finally {
    loadingAdminData.value = false
    loadingUsers.value = false
  }
}

async function loadAdminUsers() {
  if (!canViewUsers.value) {
    users.value = []
    return
  }

  loadingUsers.value = true
  try {
    const response = await apiClient.listAdminUsers()
    users.value = response.data || []
  } finally {
    loadingUsers.value = false
  }
}

async function loadAuditLogs() {
  if (!canViewAuditLogs.value) {
    auditLogs.value = []
    return
  }

  loadingAuditLogs.value = true
  try {
    const response = await apiClient.listAdminAuditLogs(buildAuditParams())
    auditLogs.value = response.data || []
  } catch (error) {
    notifyError(message, error, '审计日志加载失败')
  } finally {
    loadingAuditLogs.value = false
  }
}

async function loadBillingOrders() {
  if (!canViewBilling.value) {
    billingOrders.value = []
    return
  }

  loadingBillingOrders.value = true
  try {
    const response = await apiClient.listBillingOrders()
    billingOrders.value = response.data || []
  } catch (error) {
    notifyError(message, error, '升级订单加载失败')
  } finally {
    loadingBillingOrders.value = false
  }
}

async function handleSavePolicy() {
  if (!canEditPolicy.value) {
    message.warning('你当前没有修改平台策略的权限')
    return
  }

  savingPolicy.value = true
  try {
    const response = await apiClient.saveAdminPolicy(policyForm)
    Object.assign(policyForm, response.data || {})
    message.success(response.message || '平台策略已更新')
    await loadAdminUsers()
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  } finally {
    savingPolicy.value = false
  }
}

async function handleSaveConfig() {
  if (!canManageApiConfig.value) {
    message.warning('你当前没有修改接口配置的权限')
    return
  }

  if (!apiForm.provider || !apiForm.model) {
    message.warning('请先选择提供商和模型')
    return
  }

  savingConfig.value = true
  try {
    const response = await apiClient.saveApiConfig(apiForm)
    currentConfig.value = response.data
    apiForm.api_key = ''
    message.success(response.message || '接口配置已保存')
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  } finally {
    savingConfig.value = false
  }
}

async function handleTestConfig() {
  if (!canTestApiConfig.value) {
    message.warning('你当前没有测试接口配置的权限')
    return
  }

  if (!apiForm.provider || !apiForm.model) {
    message.warning('请先选择提供商和模型')
    return
  }

  testing.value = true
  try {
    const response = await apiClient.testApiConnection(apiForm)
    testResult.value = response.result || '连接成功'
    message.success(response.message || '连接成功')
  } catch (error) {
    testResult.value = ''
    notifyError(message, error)
  } finally {
    testing.value = false
    await loadAuditLogs()
  }
}

async function handleUpdateUser(user, payload) {
  if (!canEditMembership(user)) {
    message.warning('你当前没有修改该账号会员状态的权限')
    return
  }

  try {
    const response = await apiClient.updateAdminUserMembership(user.id, payload)
    message.success(response.message || '用户会员状态已更新')
    await loadAdminUsers()
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  }
}

async function handleUpdateUserRole(user, role) {
  if (!canEditUserRoles.value) {
    message.warning('你当前没有调整账号角色的权限')
    return
  }

  try {
    const response = await apiClient.updateAdminUserRole(user.id, { role })
    message.success(response.message || '账号角色已更新')
    await loadAdminUsers()
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  }
}

async function handleApproveBillingOrder(order) {
  if (!canManageBilling.value) {
    message.warning('你当前没有确认升级订单的权限')
    return
  }

  try {
    const response = await apiClient.approveBillingOrder(order.id, {
      payment_reference: order.payment_reference || ''
    })
    message.success(response.message || '订单已确认到账')
    await loadBillingOrders()
    await loadAdminUsers()
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  }
}

async function handleCancelManagedBillingOrder(order) {
  if (!canManageBilling.value) {
    message.warning('你当前没有取消升级订单的权限')
    return
  }

  try {
    const response = await apiClient.cancelBillingOrder(order.id, { note: '后台取消订单' })
    message.success(response.message || '订单已取消')
    await loadBillingOrders()
    await loadAuditLogs()
  } catch (error) {
    notifyError(message, error)
  }
}

const formatAuditTime = formatDate

function formatAuditStatus(status) {
  return {
    success: '成功',
    failed: '失败',
    denied: '拒绝'
  }[status] || status || '未知'
}

function auditStatusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'denied') return 'warning'
  return 'default'
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

function formatAuditAction(action) {
  return {
    'auth.login': '账号登录',
    'auth.register': '账号注册',
    'admin.policy.update': '平台策略更新',
    'admin.user.membership.update': '客户会员更新',
    'admin.user.role.update': '账号角色调整',
    'admin.api_config.save': '接口配置保存',
    'admin.api_config.test': '接口连接测试',
    'admin.prompt.save': '提示词保存',
    'admin.prompt.reset': '提示词重置',
    'billing.order.create': '创建升级订单',
    'billing.order.submit_payment': '提交付款备注',
    'billing.order.sandbox_pay': '沙盒支付完成',
    'billing.order.approve': '后台确认到账',
    'billing.order.cancel': '取消升级订单'
  }[action] || action
}

function formatAuditActor(log) {
  const email = log.actor_email || '匿名'
  const roleLabel = resolveRoleLabel(log.actor_role)
  return `${email} · ${roleLabel}`
}

watch([auditRoleFilter, auditActionFilter], async () => {
  if (!canViewAuditLogs.value || !adminDataLoaded.value) return
  await loadAuditLogs()
})

onMounted(async () => {
  try {
    await loadAdminData()
  } catch (error) {
    notifyError(message, error)
  }
})
</script>
