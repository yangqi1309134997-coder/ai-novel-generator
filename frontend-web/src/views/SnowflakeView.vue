<template>
  <div class="snowflake-view">
    <div class="max-w-6xl mx-auto">
      <div class="bg-white rounded-lg shadow-lg p-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">
          ❄️ 雪花写作法生成器
        </h1>
        <p class="text-gray-600 mb-8">
          基于雪花写作法的智能小说生成系统，从核心种子到完整章节
        </p>

        <!-- 步骤导航 -->
        <n-steps :current="currentStep" :status="currentStatus">
          <n-step title="基础设置" description="设置小说基本信息" />
          <n-step title="架构预览" description="生成核心架构" />
          <n-step title="章节蓝图" description="规划章节节奏" />
          <n-step title="生成小说" description="逐章生成内容" />
          <n-step title="导出" description="导出完成作品" />
        </n-steps>

        <n-divider />

        <!-- 步骤内容 -->
        <div class="mt-8">
          <!-- 步骤1: 基础设置 -->
          <div v-if="currentStep === 1" class="step-content">
            <h2 class="text-xl font-semibold mb-4">步骤1: 基础设置</h2>

            <n-form :model="form" label-placement="top">
              <n-grid :cols="2" :x-gap="24">
                <n-form-item-gi label="小说主题">
                  <n-input
                    v-model:value="form.topic"
                    placeholder="例如：一个被遗忘的剑客，在江湖中寻找失落的记忆"
                    type="textarea"
                    :rows="2"
                  />
                </n-form-item-gi>

                <n-form-item-gi label="小说类型">
                  <n-select
                    v-model:value="form.genre"
                    :options="genreOptions"
                    placeholder="选择小说类型"
                  />
                </n-form-item-gi>

                <n-form-item-gi label="章节数量">
                  <n-slider
                    v-model:value="form.chapterCount"
                    :min="10"
                    :max="500"
                    :step="10"
                  />
                  <template #feedback>
                    <span class="text-sm text-gray-500">{{ form.chapterCount }} 章</span>
                  </template>
                </n-form-item-gi>

                <n-form-item-gi label="每章字数">
                  <n-slider
                    v-model:value="form.wordCount"
                    :min="1000"
                    :max="10000"
                    :step="500"
                  />
                  <template #feedback>
                    <span class="text-sm text-gray-500">{{ form.wordCount }} 字</span>
                  </template>
                </n-form-item-gi>
              </n-grid>

              <n-form-item label="用户指导（可选）">
                <n-input
                  v-model:value="form.userGuidance"
                  placeholder="例如：偏向古龙风格，要有江湖气"
                  type="textarea"
                  :rows="2"
                />
              </n-form-item>
            </n-form>

            <div class="mt-6 flex justify-end">
              <n-button
                type="primary"
                size="large"
                :loading="generating"
                @click="generateArchitecture"
              >
                🚀 生成小说架构
              </n-button>
            </div>
          </div>

          <!-- 步骤2: 架构预览 -->
          <div v-if="currentStep === 2" class="step-content">
            <h2 class="text-xl font-semibold mb-4">步骤2: 架构预览</h2>

            <n-card v-if="architecture" title="生成结果" class="mb-4">
              <n-descriptions bordered :column="1">
                <n-descriptions-item label="核心种子">
                  {{ architecture.core_seed?.substring(0, 100) }}...
                </n-descriptions-item>
                <n-descriptions-item label="角色动力学">
                  {{ architecture.character_dynamics?.substring(0, 100) }}...
                </n-descriptions-item>
                <n-descriptions-item label="世界观">
                  {{ architecture.world_building?.substring(0, 100) }}...
                </n-descriptions-item>
                <n-descriptions-item label="情节架构">
                  {{ architecture.plot_architecture?.substring(0, 100) }}...
                </n-descriptions-item>
              </n-descriptions>
            </n-card>

            <div class="mt-6 flex justify-between">
              <n-button @click="currentStep--">← 上一步</n-button>
              <n-button
                type="primary"
                :loading="generating"
                @click="generateBlueprint"
              >
                📋 生成章节蓝图 →
              </n-button>
            </div>
          </div>

          <!-- 步骤3: 章节蓝图 -->
          <div v-if="currentStep === 3" class="step-content">
            <h2 class="text-xl font-semibold mb-4">步骤3: 章节蓝图</h2>

            <n-input
              v-model:value="blueprint"
              type="textarea"
              :rows="20"
              placeholder="章节蓝图将在这里显示..."
              readonly
            />

            <div class="mt-6 flex justify-between">
              <n-button @click="currentStep--">← 上一步</n-button>
              <n-button
                type="primary"
                @click="currentStep++"
              >
                继续 →
              </n-button>
            </div>
          </div>

          <!-- 步骤4和5占位 -->
          <div v-if="currentStep >= 4" class="step-content">
            <n-result status="info" title="功能预留" description="请使用当前工作台中的规划模式完成雪花规划与章节蓝图。">
              <template #footer>
                <n-button @click="currentStep = 1">返回开始</n-button>
              </template>
            </n-result>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import {
  NSteps,
  NStep,
  NDivider,
  NForm,
  NFormItemGi,
  NGrid,
  NInput,
  NSelect,
  NSlider,
  NButton,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NResult,
  useMessage
} from 'naive-ui'
import { apiClient } from '../api'

const message = useMessage()
const currentStep = ref(1)
const currentStatus = ref('process')
const generating = ref(false)

// 表单数据
const form = reactive({
  topic: '',
  genre: '玄幻',
  chapterCount: 50,
  wordCount: 3000,
  userGuidance: ''
})

// 生成结果
const architecture = ref(null)
const blueprint = ref('')

// 小说类型选项
const genreOptions = [
  { label: '玄幻', value: '玄幻' },
  { label: '仙侠', value: '仙侠' },
  { label: '武侠', value: '武侠' },
  { label: '都市', value: '都市' },
  { label: '言情', value: '言情' },
  { label: '悬疑', value: '悬疑' },
  { label: '科幻', value: '科幻' },
  { label: '历史', value: '历史' },
  { label: '军事', value: '军事' },
  { label: '灵异', value: '灵异' }
]

// 生成架构
async function generateArchitecture() {
  if (!form.topic) {
    message.error('请输入小说主题')
    return
  }

  generating.value = true

  try {
    const response = await apiClient.generateSnowflakeArchitecture({
      topic: form.topic,
      genre: form.genre,
      number_of_chapters: form.chapterCount,
      word_number: form.wordCount,
      user_guidance: form.userGuidance
    })

    if (response.success) {
      architecture.value = response.data
      message.success('架构生成成功！')
      currentStep.value = 2
    }
  } catch (error) {
    message.error('生成失败：' + error.message)
  } finally {
    generating.value = false
  }
}

// 生成蓝图
async function generateBlueprint() {
  generating.value = true

  try {
    const response = await apiClient.generateChapterBlueprint({
      architecture: architecture.value,
      number_of_chapters: form.chapterCount
    })

    if (response.success) {
      blueprint.value = response.data.blueprint
      message.success('章节蓝图生成成功！')
      currentStep.value = 3
    }
  } catch (error) {
    message.error('生成失败：' + error.message)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.snowflake-view {
  padding: 20px 0;
}

.step-content {
  min-height: 400px;
}
</style>
