<template>
  <div class="admin-orders">
    <PageHeader title="订单管理" description="查看与管理平台订单">
      <template #actions>
        <n-button type="primary" @click="loadOrders">
          <template #icon><n-icon><refresh-outline /></n-icon></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="filter-bar">
      <n-select
        v-model:value="filters.status"
        :options="statusOptions"
        placeholder="订单状态"
        clearable
        style="width: 150px"
        @update:value="handleSearch"
      />
      <n-select
        v-model:value="filters.channel"
        :options="channelOptions"
        placeholder="支付渠道"
        clearable
        style="width: 150px"
        @update:value="handleSearch"
      />
    </div>

    <!-- Table -->
    <LoadingCard v-if="loading" :rows="6" :show-header="false" />
    <template v-else>
      <n-data-table
        :columns="columns"
        :data="orders"
        :bordered="false"
        :row-key="row => row.id"
        :pagination="pagination"
        :loading="loading"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
      <EmptyState
        v-if="orders.length === 0 && !loading"
        title="暂无订单"
        description="没有找到匹配的订单记录"
      />
    </template>

    <!-- Order detail modal -->
    <n-modal v-model:show="showDetailModal" preset="card" title="订单详情" style="width: 560px">
      <n-descriptions v-if="selectedOrder" bordered :column="1" label-placement="left" size="small">
        <n-descriptions-item label="订单ID">{{ selectedOrder.id }}</n-descriptions-item>
        <n-descriptions-item label="订单号">{{ selectedOrder.order_no || '-' }}</n-descriptions-item>
        <n-descriptions-item label="用户ID">{{ selectedOrder.user_id }}</n-descriptions-item>
        <n-descriptions-item label="用户邮箱">{{ selectedOrder.user_email || '-' }}</n-descriptions-item>
        <n-descriptions-item label="金额">&yen;{{ formatMoney(selectedOrder.amount) }}</n-descriptions-item>
        <n-descriptions-item label="支付渠道">{{ selectedOrder.payment_channel || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="statusTagType(selectedOrder.status)" size="small" round>
            {{ statusLabel(selectedOrder.status) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="商品类型">{{ selectedOrder.item_type || '-' }}</n-descriptions-item>
        <n-descriptions-item label="商品名称">{{ selectedOrder.item_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ formatDate(selectedOrder.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ formatDate(selectedOrder.updated_at) }}</n-descriptions-item>
        <n-descriptions-item v-if="selectedOrder.remark" label="备注">{{ selectedOrder.remark }}</n-descriptions-item>
      </n-descriptions>
      <template #action>
        <n-button v-if="selectedOrder?.status === 'pending_payment'" type="success" @click="approveOrder(selectedOrder)">
          审核通过
        </n-button>
        <n-button v-if="selectedOrder?.status === 'paid' || selectedOrder?.status === 'pending_payment'" type="warning" @click="refundOrder(selectedOrder)">
          退款
        </n-button>
        <n-button @click="showDetailModal = false">关闭</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { useMessage, NButton, NTag, NSpace, NIcon, NModal, NDescriptions, NDescriptionsItem, NSelect, NDataTable } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()

const loading = ref(false)
const orders = ref([])
const selectedOrder = ref(null)
const showDetailModal = ref(false)

const filters = reactive({
  status: null,
  channel: null,
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  prefix({ itemCount }) {
    return `共 ${itemCount} 条`
  },
})

const statusOptions = [
  { label: '待支付', value: 'pending_payment' },
  { label: '已支付', value: 'paid' },
  { label: '已审核', value: 'approved' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
  { label: '已退款', value: 'refunded' },
]

const channelOptions = [
  { label: '支付宝', value: 'alipay' },
  { label: '手动转账', value: 'manual_transfer' },
  { label: '卡密兑换', value: 'card_code' },
  { label: '沙箱支付', value: 'sandbox' },
]

const statusMap = {
  pending_payment: { label: '待支付', type: 'warning' },
  paid: { label: '已支付', type: 'success' },
  approved: { label: '已审核', type: 'info' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'default' },
  refunded: { label: '已退款', type: 'error' },
}

function statusLabel(status) {
  return statusMap[status]?.label || status || '-'
}

function statusTagType(status) {
  return statusMap[status]?.type || 'default'
}

function formatMoney(val) {
  return Number(val || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

const columns = [
  {
    title: '订单号',
    key: 'order_no',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: '用户',
    key: 'user_email',
    width: 180,
    ellipsis: { tooltip: true },
    render(row) {
      return row.user_email || row.user_id || '-'
    },
  },
  {
    title: '金额',
    key: 'amount',
    width: 100,
    render(row) {
      return `\u00A5${formatMoney(row.amount)}`
    },
  },
  {
    title: '支付渠道',
    key: 'payment_channel',
    width: 110,
    render(row) {
      return row.payment_channel || '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(NTag, { size: 'small', type: statusTagType(row.status), round: true }, { default: () => statusLabel(row.status) })
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
  {
    title: '操作',
    key: 'actions',
    width: 140,
    fixed: 'right',
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => openDetail(row) }, { default: () => '详情' }),
          h(
            NButton,
            {
              text: true,
              type: row.status === 'pending_payment' ? 'success' : 'default',
              size: 'small',
              disabled: row.status !== 'pending_payment',
              onClick: () => approveOrder(row),
            },
            { default: () => '审核' },
          ),
        ],
      })
    },
  },
]

async function loadOrders() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.status) params.status = filters.status
    if (filters.channel) params.payment_channel = filters.channel
    const res = await apiClient.getAdminOrders(params)
    orders.value = res.data?.items || []
    pagination.itemCount = res.data?.total || 0
  } catch (e) {
    message.error('加载订单列表失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadOrders()
}

function handlePageChange(page) {
  pagination.page = page
  loadOrders()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadOrders()
}

function openDetail(row) {
  selectedOrder.value = row
  showDetailModal.value = true
}

async function approveOrder(row) {
  try {
    await apiClient.approveBillingOrder(row.id)
    message.success('订单已审核通过')
    showDetailModal.value = false
    loadOrders()
  } catch (e) {
    message.error('审核失败: ' + (e.detail || e.message || '未知错误'))
  }
}

async function refundOrder(row) {
  try {
    await apiClient.cancelBillingOrder(row.id, { reason: '管理员退款' })
    message.success('订单已退款')
    showDetailModal.value = false
    loadOrders()
  } catch (e) {
    message.error('退款失败: ' + (e.detail || e.message || '未知错误'))
  }
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
</style>
