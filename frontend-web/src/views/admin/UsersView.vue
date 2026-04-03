<template>
  <div class="admin-users">
    <PageHeader title="用户管理" description="查看与管理平台用户">
      <template #actions>
        <n-button type="primary" @click="loadUsers">
          <template #icon><n-icon><refresh-outline /></n-icon></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="filter-bar">
      <n-input
        v-model:value="filters.search"
        placeholder="搜索邮箱或显示名..."
        clearable
        style="width: 280px"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <n-icon><search-outline /></n-icon>
        </template>
      </n-input>
      <n-select
        v-model:value="filters.role"
        :options="roleOptions"
        placeholder="角色筛选"
        clearable
        style="width: 140px"
        @update:value="handleSearch"
      />
      <n-select
        v-model:value="filters.tier"
        :options="tierOptions"
        placeholder="会员等级"
        clearable
        style="width: 140px"
        @update:value="handleSearch"
      />
    </div>

    <!-- Table -->
    <LoadingCard v-if="loading" :rows="6" :show-header="false" />
    <template v-else>
      <n-data-table
        :columns="columns"
        :data="users"
        :bordered="false"
        :row-key="row => row.id"
        :pagination="pagination"
        :loading="loading"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
      <EmptyState
        v-if="users.length === 0 && !loading"
        title="暂无用户"
        description="没有找到匹配的用户记录"
      />
    </template>

    <!-- User detail modal -->
    <n-modal v-model:show="showDetailModal" preset="card" title="用户详情" style="width: 520px">
      <n-descriptions v-if="selectedUser" bordered :column="1" label-placement="left" size="small">
        <n-descriptions-item label="ID">{{ selectedUser.id }}</n-descriptions-item>
        <n-descriptions-item label="邮箱">{{ selectedUser.email }}</n-descriptions-item>
        <n-descriptions-item label="显示名">{{ selectedUser.display_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="角色">{{ selectedUser.role || '-' }}</n-descriptions-item>
        <n-descriptions-item label="会员等级">{{ selectedUser.subscription_tier || 'free' }}</n-descriptions-item>
        <n-descriptions-item label="余额">&yen;{{ formatMoney(selectedUser.balance || 0) }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="selectedUser.is_active !== false ? 'success' : 'error'" size="small" round>
            {{ selectedUser.is_active !== false ? '正常' : '已禁用' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="注册时间">{{ formatDate(selectedUser.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ formatDate(selectedUser.updated_at) }}</n-descriptions-item>
      </n-descriptions>
    </n-modal>

    <!-- Balance adjust modal -->
    <n-modal v-model:show="showBalanceModal" preset="card" title="调整余额" style="width: 420px">
      <n-form ref="balanceFormRef" :model="balanceForm" :rules="balanceRules" label-placement="left" label-width="80">
        <n-form-item label="当前余额">
          <span>&yen;{{ formatMoney(selectedUser?.balance || 0) }}</span>
        </n-form-item>
        <n-form-item label="调整金额" path="amount">
          <n-input-number
            v-model:value="balanceForm.amount"
            :precision="2"
            style="width: 100%"
            placeholder="正数增加，负数扣除"
          />
        </n-form-item>
        <n-form-item label="原因" path="reason">
          <n-input v-model:value="balanceForm.reason" type="textarea" :rows="3" placeholder="请填写调整原因" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="showBalanceModal = false">取消</n-button>
        <n-button type="primary" :loading="submitting" @click="submitBalanceAdjust">确认调整</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { useMessage, NButton, NTag, NSpace, NIcon, NModal, NDescriptions, NDescriptionsItem, NForm, NFormItem, NInput, NInputNumber, NSelect, NDataTable } from 'naive-ui'
import { SearchOutline, RefreshOutline } from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const selectedUser = ref(null)
const showDetailModal = ref(false)
const showBalanceModal = ref(false)

const filters = reactive({
  search: '',
  role: null,
  tier: null,
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

const balanceForm = reactive({
  amount: null,
  reason: '',
})

const balanceRules = {
  amount: { required: true, type: 'number', message: '请输入调整金额', trigger: 'blur' },
  reason: { required: true, message: '请填写调整原因', trigger: 'blur' },
}

const balanceFormRef = ref(null)

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '运营', value: 'operator' },
  { label: '客服', value: 'support' },
  { label: '客户', value: 'customer' },
]

const tierOptions = [
  { label: '免费', value: 'free' },
  { label: '基础会员', value: 'basic' },
  { label: '专业会员', value: 'pro' },
]

function formatMoney(val) {
  return Number(val || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

function getTierLabel(tier) {
  const map = { free: '免费', basic: '基础会员', pro: '专业会员' }
  return map[tier] || tier || '免费'
}

const columns = [
  {
    title: '邮箱',
    key: 'email',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '显示名',
    key: 'display_name',
    width: 120,
    render(row) {
      return row.display_name || '-'
    },
  },
  {
    title: '角色',
    key: 'role',
    width: 90,
    render(row) {
      const typeMap = { admin: 'error', operator: 'warning', support: 'info', customer: 'default' }
      return h(NTag, { size: 'small', type: typeMap[row.role] || 'default', round: true }, { default: () => row.role || '-' })
    },
  },
  {
    title: '会员等级',
    key: 'subscription_tier',
    width: 100,
    render(row) {
      return h(NTag, { size: 'small', round: true }, { default: () => getTierLabel(row.subscription_tier) })
    },
  },
  {
    title: '余额',
    key: 'balance',
    width: 100,
    render(row) {
      return `\u00A5${formatMoney(row.balance)}`
    },
  },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    render(row) {
      return h(NTag, {
        size: 'small',
        type: row.is_active !== false ? 'success' : 'error',
        round: true,
      }, { default: () => row.is_active !== false ? '正常' : '已禁用' })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => openDetail(row) }, { default: () => '查看详情' }),
          h(NButton, {
            text: true,
            type: row.is_active !== false ? 'warning' : 'success',
            size: 'small',
            onClick: () => toggleBan(row),
          }, { default: () => row.is_active !== false ? '禁用' : '启用' }),
          h(NButton, { text: true, size: 'small', onClick: () => openBalanceModal(row) }, { default: () => '调整余额' }),
        ],
      })
    },
  },
]

async function loadUsers() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.search.trim()) {
      params.search = filters.search.trim()
    }
    const res = await apiClient.getAdminUsers(params)
    users.value = res.data?.items || []
    pagination.itemCount = res.data?.total || 0
  } catch (e) {
    message.error('加载用户列表失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadUsers()
}

function handlePageChange(page) {
  pagination.page = page
  loadUsers()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadUsers()
}

function openDetail(row) {
  selectedUser.value = row
  showDetailModal.value = true
}

async function toggleBan(row) {
  const isActive = row.is_active !== false
  const action = isActive ? '禁用' : '启用'
  try {
    await apiClient.banAdminUser(row.id, { is_active: !isActive, reason: `管理员${action}` })
    message.success(`已${action}用户 ${row.email}`)
    loadUsers()
  } catch (e) {
    message.error(`${action}失败: ` + (e.detail || e.message || '未知错误'))
  }
}

function openBalanceModal(row) {
  selectedUser.value = row
  balanceForm.amount = null
  balanceForm.reason = ''
  showBalanceModal.value = true
}

async function submitBalanceAdjust() {
  if (!balanceForm.amount && balanceForm.amount !== 0) {
    message.warning('请输入调整金额')
    return
  }
  if (!balanceForm.reason.trim()) {
    message.warning('请填写调整原因')
    return
  }
  try {
    submitting.value = true
    await apiClient.adjustUserBalance(selectedUser.value.id, {
      amount: balanceForm.amount,
      reason: balanceForm.reason,
    })
    message.success('余额调整成功')
    showBalanceModal.value = false
    loadUsers()
  } catch (e) {
    message.error('余额调整失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadUsers()
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
