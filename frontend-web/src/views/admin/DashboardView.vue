<template>
  <div class="admin-dashboard">
    <PageHeader title="管理面板" description="系统概览与数据统计" />

    <!-- Stats cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--users">
          <n-icon :size="24"><people-outline /></n-icon>
        </div>
        <div class="stat-card__body">
          <div class="stat-card__label">总用户数</div>
          <div class="stat-card__value">{{ stats.users?.total ?? '-' }}</div>
          <div class="stat-card__sub">今日新增 {{ stats.users?.new_today ?? 0 }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--active">
          <n-icon :size="24"><flash-outline /></n-icon>
        </div>
        <div class="stat-card__body">
          <div class="stat-card__label">活跃用户(7天)</div>
          <div class="stat-card__value">{{ stats.users?.active_7d ?? '-' }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--jobs">
          <n-icon :size="24"><construct-outline /></n-icon>
        </div>
        <div class="stat-card__body">
          <div class="stat-card__label">进行中任务</div>
          <div class="stat-card__value">{{ stats.jobs?.active ?? '-' }}</div>
          <div class="stat-card__sub">今日完成 {{ stats.jobs?.completed_today ?? 0 }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--revenue">
          <n-icon :size="24"><wallet-outline /></n-icon>
        </div>
        <div class="stat-card__body">
          <div class="stat-card__label">今日收入</div>
          <div class="stat-card__value">&yen;{{ formatMoney(stats.revenue?.today ?? 0) }}</div>
          <div class="stat-card__sub">累计 &yen;{{ formatMoney(stats.revenue?.total ?? 0) }}</div>
        </div>
      </div>
    </div>

    <!-- Recent orders -->
    <div class="section-card">
      <div class="section-card__header">
        <h2 class="section-card__title">最近订单</h2>
        <n-button text size="small" @click="router.push({ name: 'AdminOrders' })">查看全部</n-button>
      </div>
      <LoadingCard v-if="loadingOrders" :rows="4" :show-header="false" />
      <n-data-table
        v-else
        :columns="orderColumns"
        :data="recentOrders"
        :bordered="false"
        size="small"
        :pagination="false"
      />
      <EmptyState v-if="!loadingOrders && recentOrders.length === 0" title="暂无订单" description="系统暂无订单记录" />
    </div>

    <!-- System status -->
    <div class="section-card">
      <div class="section-card__header">
        <h2 class="section-card__title">系统状态</h2>
      </div>
      <div class="status-grid">
        <div class="status-item">
          <n-icon :size="18" :color="apiConfigured ? '#18a058' : '#d03050'">
            <checkmark-circle-outline v-if="apiConfigured" />
            <close-circle-outline v-else />
          </n-icon>
          <span>API: {{ apiConfigured ? '已配置' : '未配置' }}</span>
        </div>
        <div class="status-item">
          <n-icon :size="18" :color="smtpConfigured ? '#18a058' : '#d03050'">
            <checkmark-circle-outline v-if="smtpConfigured" />
            <close-circle-outline v-else />
          </n-icon>
          <span>SMTP: {{ smtpConfigured ? '已配置' : '未配置' }}</span>
        </div>
        <div class="status-item">
          <n-icon :size="18" :color="paymentConfigured ? '#18a058' : '#d03050'">
            <checkmark-circle-outline v-if="paymentConfigured" />
            <close-circle-outline v-else />
          </n-icon>
          <span>支付: {{ paymentConfigured ? '已配置' : '未配置' }}</span>
        </div>
        <div class="status-item">
          <n-icon :size="18" color="#18a058"><checkmark-circle-outline /></n-icon>
          <span>卡密可用: {{ stats.card_codes?.available ?? 0 }} 张</span>
        </div>
        <div class="status-item">
          <n-icon :size="18" :color="stats.orders?.pending > 0 ? '#f0a020' : '#18a058'">
            <checkmark-circle-outline v-if="stats.orders?.pending === 0" />
            <alert-circle-outline v-else />
          </n-icon>
          <span>待处理订单: {{ stats.orders?.pending ?? 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NButton, NIcon, NTag } from 'naive-ui'
import {
  PeopleOutline,
  FlashOutline,
  ConstructOutline,
  WalletOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  AlertCircleOutline,
} from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const router = useRouter()
const message = useMessage()

const loading = ref(true)
const loadingOrders = ref(true)
const stats = ref({})
const recentOrders = ref([])
const apiConfigured = ref(false)
const smtpConfigured = ref(false)
const paymentConfigured = ref(false)

function formatMoney(val) {
  return Number(val || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

const orderStatusMap = {
  pending_payment: { label: '待支付', type: 'warning' },
  paid: { label: '已支付', type: 'success' },
  approved: { label: '已审核', type: 'info' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'default' },
  refunded: { label: '已退款', type: 'error' },
}

const orderColumns = [
  { title: '订单号', key: 'order_no', width: 180, ellipsis: { tooltip: true } },
  { title: '用户', key: 'user_email', width: 180, ellipsis: { tooltip: true } },
  {
    title: '金额',
    key: 'amount',
    width: 100,
    render(row) {
      return `\u00A5${formatMoney(row.amount)}`
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const s = orderStatusMap[row.status] || { label: row.status, type: 'default' }
      return h(NTag, { size: 'small', type: s.type, round: true }, { default: () => s.label })
    },
  },
  {
    title: '时间',
    key: 'created_at',
    width: 170,
    render(row) {
      return formatDate(row.created_at)
    },
  },
]

async function loadStats() {
  try {
    loading.value = true
    const res = await apiClient.getAdminStats()
    stats.value = res.data || {}
  } catch (e) {
    message.error('加载统计数据失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function loadRecentOrders() {
  try {
    loadingOrders.value = true
    const res = await apiClient.getAdminOrders({ page: 1, page_size: 5 })
    recentOrders.value = res.data?.items || []
  } catch {
    // silently ignore
  } finally {
    loadingOrders.value = false
  }
}

async function loadSystemStatus() {
  try {
    const [apiRes, smtpRes, payRes] = await Promise.allSettled([
      apiClient.getApiConfig(),
      apiClient.getAdminSmtpConfig(),
      apiClient.getAdminPaymentConfig(),
    ])
    if (apiRes.status === 'fulfilled' && apiRes.value?.data) {
      apiConfigured.value = Boolean(apiRes.value.data.api_key || apiRes.value.data.base_url)
    }
    if (smtpRes.status === 'fulfilled' && smtpRes.value?.data) {
      smtpConfigured.value = Boolean(smtpRes.value.data.smtp_host)
    }
    if (payRes.status === 'fulfilled' && payRes.value?.data) {
      const d = payRes.value.data
      paymentConfigured.value = Boolean(d.alipay_app_id || d.payment_enabled)
    }
  } catch {
    // ignore
  }
}

onMounted(() => {
  loadStats()
  loadRecentOrders()
  loadSystemStatus()
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.stat-card__icon--users { background: #ede9fe; color: #7c3aed; }
.stat-card__icon--active { background: #dbeafe; color: #2563eb; }
.stat-card__icon--jobs { background: #fef3c7; color: #d97706; }
.stat-card__icon--revenue { background: #d1fae5; color: #059669; }

.stat-card__body { flex: 1; min-width: 0; }
.stat-card__label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}
.stat-card__value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}
.stat-card__sub {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.section-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}
.section-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.section-card__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}
.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #475569;
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .status-grid {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
