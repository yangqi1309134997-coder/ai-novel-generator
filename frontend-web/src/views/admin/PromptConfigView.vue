<template>
  <div class="admin-prompt-config">
    <PageHeader title="提示词管理" description="编辑和管理系统提示词模板">
      <template #actions>
        <n-button @click="loadTemplates">
          <template #icon><n-icon><refresh-outline /></n-icon></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <LoadingCard v-if="loading" :rows="6" :show-header="false" />

    <template v-else>
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane
          v-for="category in categories"
          :key="category.key"
          :name="category.key"
          :tab="category.label"
        >
          <div class="prompt-list">
            <div
              v-for="tpl in getTemplatesByCategory(category.key)"
              :key="tpl.name"
              class="prompt-item"
            >
              <div class="prompt-item__header">
                <div>
                  <span class="prompt-item__name">{{ tpl.display_name || tpl.name }}</span>
                  <n-tag v-if="tpl.modified" size="tiny" type="warning" round style="margin-left: 8px;">已修改</n-tag>
                </div>
                <n-space size="small">
                  <n-button text size="small" @click="resetTemplate(tpl)">重置为默认</n-button>
                  <n-button text size="small" type="primary" :loading="tpl.saving" @click="saveTemplate(tpl)">保存</n-button>
                </n-space>
              </div>
              <p v-if="tpl.description" class="prompt-item__desc">{{ tpl.description }}</p>
              <n-input
                v-model:value="tpl.content"
                type="textarea"
                :rows="12"
                placeholder="提示词内容..."
                :disabled="tpl.saving"
                class="prompt-editor"
              />
            </div>
            <EmptyState
              v-if="getTemplatesByCategory(category.key).length === 0"
              title="暂无提示词"
              description="该分类下没有提示词模板"
            />
          </div>
        </n-tab-pane>
      </n-tabs>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useMessage, NTabs, NTabPane, NInput, NButton, NSpace, NTag, NIcon } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()
const loading = ref(false)
const templates = ref([])
const activeTab = ref('outline')

const categories = [
  { key: 'outline', label: '大纲生成' },
  { key: 'generation', label: '章节生成' },
  { key: 'character', label: '角色设定' },
  { key: 'world', label: '世界观' },
  { key: '重写风格', label: '重写风格' },
]

function getTemplatesByCategory(categoryKey) {
  return templates.value.filter(t => t.category === categoryKey)
}

async function loadTemplates() {
  try {
    loading.value = true
    const res = await apiClient.listPromptTemplates()
    const data = res.data || res || {}

    // 后端返回 {category: [template_names]} 格式，需要转换为模板对象数组
    const items = []
    if (Array.isArray(data)) {
      // 如果后端直接返回数组
      for (const t of data) {
        items.push({
          ...t,
          content: t.content || t.template || '',
          saving: false,
          modified: false,
        })
      }
    } else if (typeof data === 'object') {
      // 后端返回 Dict[str, List[str]]，逐个加载模板内容
      for (const [category, names] of Object.entries(data)) {
        if (!Array.isArray(names)) continue
        for (const name of names) {
          if (!name || typeof name !== 'string') continue
          items.push({
            name,
            category,
            display_name: name,
            content: '',
            loaded: false,
            saving: false,
            modified: false,
          })
        }
      }
    }

    templates.value = items

    // 为当前激活的分类预加载模板内容
    if (items.length > 0) {
      const firstCat = items[0].category
      if (firstCat) activeTab.value = firstCat
      // 异步加载当前分类的模板内容
      loadCategoryContent(firstCat)
    }
  } catch (e) {
    message.error('加载提示词失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function loadCategoryContent(categoryKey) {
  const categoryTemplates = templates.value.filter(t => t.category === categoryKey && !t.loaded)
  for (const tpl of categoryTemplates) {
    try {
      const res = await apiClient.getPromptTemplate(categoryKey, tpl.name)
      const data = res.data || res || {}
      tpl.content = data.content || ''
      tpl.display_name = data.display_name || tpl.name
      tpl.description = data.description || ''
      tpl.loaded = true
    } catch {
      tpl.loaded = true // 标记为已加载，避免重复请求
    }
  }
}

async function saveTemplate(tpl) {
  if (!tpl.content.trim()) {
    message.warning('提示词内容不能为空')
    return
  }
  try {
    tpl.saving = true
    await apiClient.savePromptTemplate({
      category: tpl.category,
      name: tpl.name,
      content: tpl.content,
    })
    tpl.modified = false
    message.success(`提示词 "${tpl.display_name || tpl.name}" 已保存`)
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    tpl.saving = false
  }
}

async function resetTemplate(tpl) {
  try {
    const res = await apiClient.resetPromptTemplate({
      category: tpl.category,
      name: tpl.name,
    })
    tpl.content = res?.data?.content || res?.data?.template || tpl.content
    tpl.modified = false
    message.success(`提示词 "${tpl.display_name || tpl.name}" 已重置为默认`)
  } catch (e) {
    message.error('重置失败: ' + (e.detail || e.message || '未知错误'))
  }
}

onMounted(() => {
  loadTemplates()
})

// Tab 切换时加载对应分类的模板内容
watch(activeTab, (newTab) => {
  loadCategoryContent(newTab)
})
</script>

<style scoped>
.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 20px 0;
}

.prompt-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
}

.prompt-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.prompt-item__name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.prompt-item__desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px;
  line-height: 1.5;
}

.prompt-editor :deep(textarea) {
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
