<template>
  <div class="admin-audit-logs">
    <PageHeader title="系统日志" description="查看系统审计日志">
      <template #actions>
        <n-button type="primary" @click="loadLogs">
          <template #icon><n-icon><refresh-outline /></n-icon></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="filter-bar">
      <n-select
        v-model:value="filters.action_prefix"
        :options="actionOptions"
        placeholder="操作类型"
        clearable
        style="width: 200px"
        @update:value="handleSearch"
      />
      <n-select
        v-model:value="filters.actor_role"
        :options="roleOptions"
        placeholder="操作者角色"
        clearable
        style="width: 150px"
        @update:value="handleSearch"
      />
    </div>

    <!-- Table -->
    <LoadingCard v-if="loading" :rows="8" :show-header="false" />
    <template v-else>
      <n-data-table
        :columns="columns"
        :data="logs"
        :bordered="false"
        :row-key="row => row.id || row.timestamp"
        :pagination="pagination"
        :loading="loading"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
      <EmptyState
        v-if="logs.length === 0 && !loading"
        title="暂无日志"
        description="没有找到匹配的审计日志"
      />
    </template>
  </div>
</template>

<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { useMessage, NButton, NTag, NIcon, NSelect, NDataTable } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()

const loading = ref(false)
const logs = ref([])

const filters = reactive({
  action_prefix: null,
  actor_role: null,
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  prefix({ itemCount }) {
    return `共 ${itemCount} 条`
  },
})

const actionOptions = [
  { label: '用户管理', value: 'admin.user' },
  { label: '配置变更', value: 'admin.config' },
  { label: '卡密操作', value: 'admin.card_codes' },
  { label: '订单管理', value: 'admin.order' },
  { label: '认证操作', value: 'auth' },
  { label: '生成任务', value: 'generation' },
]

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '运营', value: 'operator' },
  { label: '客服', value: 'support' },
  { label: '客户', value: 'customer' },
]

function formatDateTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

function getStatusType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed' || status === 'error') return 'error'
  return 'default'
}

const columns = [
  {
    title: '时间',
    key: 'timestamp',
    width: 170,
    render(row) {
      return formatDateTime(row.timestamp || row.created_at)
    },
  },
  {
    title: '操作类型',
    key: 'action',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      return h(NTag, { size: 'small', round: true }, { default: () => row.action || '-' })
    },
  },
  {
    title: '操作者',
    key: 'actor_email',
    width: 180,
    ellipsis: { tooltip: true },
    render(row) {
      return row.actor_email || row.actor || '-'
    },
  },
  {
    title: '目标',
    key: 'target_label',
    width: 160,
    ellipsis: { tooltip: true },
    render(row) {
      return row.target_label || row.target_id || '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render(row) {
      return h(NTag, { size: 'small', type: getStatusType(row.status), round: true }, { default: () => row.status || '-' })
    },
  },
  {
    title: '描述',
    key: 'message',
    ellipsis: { tooltip: true },
    render(row) {
      return row.message || '-'
    },
  },
]

async function loadLogs() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.action_prefix) params.action_prefix = filters.action_prefix
    if (filters.actor_role) params.actor_role = filters.actor_role
    const res = await apiClient.getAdminAuditLogs(params)
    logs.value = res.data?.items || []
    pagination.itemCount = res.data?.total || 0
  } catch (e) {
    message.error('加载日志失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadLogs()
}

function handlePageChange(page) {
  pagination.page = page
  loadLogs()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadLogs()
}

onMounted(() => {
  loadLogs()
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
