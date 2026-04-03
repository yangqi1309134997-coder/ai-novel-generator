<template>
  <div class="admin-card-codes">
    <PageHeader title="卡密管理" description="生成、查看和管理卡密">
      <template #actions>
        <n-button type="primary" @click="showGenerateModal = true">
          <template #icon><n-icon><add-outline /></n-icon></template>
          批量生成
        </n-button>
      </template>
    </PageHeader>

    <!-- Generate modal -->
    <n-modal v-model:show="showGenerateModal" preset="card" title="批量生成卡密" style="width: 460px">
      <n-form :model="genForm" label-placement="left" label-width="80">
        <n-form-item label="生成数量">
          <n-input-number v-model:value="genForm.quantity" :min="1" :max="500" style="width: 100%" />
        </n-form-item>
        <n-form-item label="类型">
          <n-select v-model:value="genForm.tier" :options="tierOptions" />
        </n-form-item>
        <n-form-item label="天数">
          <n-input-number v-model:value="genForm.days" :min="1" :max="3650" style="width: 100%" />
        </n-form-item>
        <n-form-item label="面值(元)">
          <n-input-number v-model:value="genForm.value_yuan" :min="0" :precision="2" style="width: 100%" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="showGenerateModal = false">取消</n-button>
        <n-button type="primary" :loading="generating" @click="handleGenerate">生成</n-button>
      </template>
    </n-modal>

    <!-- Generated codes result modal -->
    <n-modal v-model:show="showResultModal" preset="card" title="生成结果" style="width: 560px">
      <n-alert type="success" :show-icon="false" style="margin-bottom: 16px">
        成功生成 {{ generatedCodes.length }} 张卡密
      </n-alert>
      <n-input
        type="textarea"
        :value="generatedCodesText"
        :rows="10"
        readonly
      />
      <template #action>
        <n-button @click="copyAllCodes">复制全部</n-button>
        <n-button type="primary" @click="showResultModal = false">确定</n-button>
      </template>
    </n-modal>

    <!-- Filters -->
    <div class="filter-bar">
      <n-select
        v-model:value="filters.status"
        :options="cardStatusOptions"
        placeholder="状态筛选"
        clearable
        style="width: 150px"
        @update:value="handleSearch"
      />
      <n-select
        v-model:value="filters.tier"
        :options="tierOptions"
        placeholder="类型筛选"
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
        :data="cards"
        :bordered="false"
        :row-key="row => row.id"
        :pagination="pagination"
        :loading="loading"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
      <EmptyState
        v-if="cards.length === 0 && !loading"
        title="暂无卡密"
        description="点击上方按钮批量生成卡密"
      />
    </template>
  </div>
</template>

<script setup>
import { h, onMounted, reactive, ref, computed } from 'vue'
import { useMessage, NButton, NTag, NSpace, NIcon, NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NDataTable, NAlert } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()

const loading = ref(false)
const generating = ref(false)
const cards = ref([])
const showGenerateModal = ref(false)
const showResultModal = ref(false)
const generatedCodes = ref([])

const genForm = reactive({
  quantity: 10,
  tier: 'basic',
  days: 30,
  value_yuan: 29,
})

const filters = reactive({
  status: null,
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

const tierOptions = [
  { label: '基础会员', value: 'basic' },
  { label: '专业会员', value: 'pro' },
]

const cardStatusOptions = [
  { label: '可用', value: 'available' },
  { label: '已兑换', value: 'redeemed' },
  { label: '已作废', value: 'disabled' },
]

const cardStatusMap = {
  available: { label: '可用', type: 'success' },
  redeemed: { label: '已兑换', type: 'info' },
  disabled: { label: '已作废', type: 'default' },
}

function formatDate(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

const generatedCodesText = computed(() => {
  return generatedCodes.value.map(c => c.code).join('\n')
})

const columns = [
  {
    title: '卡密',
    key: 'code',
    width: 240,
    ellipsis: { tooltip: true },
  },
  {
    title: '类型',
    key: 'tier',
    width: 100,
    render(row) {
      const label = row.tier === 'pro' ? '专业' : '基础'
      return h(NTag, { size: 'small', round: true }, { default: () => label })
    },
  },
  {
    title: '天数',
    key: 'days',
    width: 80,
    render(row) {
      return `${row.days}天`
    },
  },
  {
    title: '面值',
    key: 'value_yuan',
    width: 80,
    render(row) {
      return `\u00A5${row.value_yuan || 0}`
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render(row) {
      const s = cardStatusMap[row.status] || { label: row.status, type: 'default' }
      return h(NTag, { size: 'small', type: s.type, round: true }, { default: () => s.label })
    },
  },
  {
    title: '兑换者',
    key: 'redeemed_by',
    width: 180,
    ellipsis: { tooltip: true },
    render(row) {
      return row.redeemed_by || row.redeemed_by_email || '-'
    },
  },
  {
    title: '创建时间',
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
          h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => copyCode(row.code) }, { default: () => '复制' }),
          h(
            NButton,
            {
              text: true,
              type: 'error',
              size: 'small',
              disabled: row.status !== 'available',
              onClick: () => disableCard(row),
            },
            { default: () => '作废' },
          ),
        ],
      })
    },
  },
]

async function loadCards() {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.status) params.status = filters.status
    if (filters.tier) params.tier = filters.tier
    const res = await apiClient.getAdminCardCodes(params)
    cards.value = res.data?.items || []
    pagination.itemCount = res.data?.total || 0
  } catch (e) {
    message.error('加载卡密列表失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadCards()
}

function handlePageChange(page) {
  pagination.page = page
  loadCards()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadCards()
}

async function handleGenerate() {
  try {
    generating.value = true
    const res = await apiClient.generateCardCodes(genForm)
    generatedCodes.value = res.data?.codes || []
    showGenerateModal.value = false
    showResultModal.value = true
    loadCards()
  } catch (e) {
    message.error('生成卡密失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    generating.value = false
  }
}

function copyCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

function copyAllCodes() {
  navigator.clipboard.writeText(generatedCodesText.value).then(() => {
    message.success('已复制全部卡密到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

async function disableCard(row) {
  try {
    await apiClient.disableCardCode(row.id)
    message.success('卡密已作废')
    loadCards()
  } catch (e) {
    message.error('作废失败: ' + (e.detail || e.message || '未知错误'))
  }
}

onMounted(() => {
  loadCards()
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
