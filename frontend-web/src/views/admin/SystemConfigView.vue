<template>
  <div class="admin-system-config">
    <PageHeader title="系统配置" description="管理系统各项配置参数" />

    <LoadingCard v-if="loading" :rows="6" :show-header="false" />

    <n-tabs v-else type="line" animated>
      <!-- Tab 1: Basic -->
      <n-tab-pane name="basic" tab="基础配置">
        <div class="config-section">
          <n-form :model="basicForm" label-placement="left" label-width="100">
            <n-form-item label="网站名称">
              <n-input v-model:value="basicForm.site_name" placeholder="AI 小说生成器" />
            </n-form-item>
            <n-form-item label="网站公告">
              <n-input v-model:value="basicForm.announcement" type="textarea" :rows="4" placeholder="在此输入公告内容，留空则不显示" />
            </n-form-item>
            <n-form-item>
              <n-button type="primary" :loading="saving.basic" @click="saveBasicConfig">保存配置</n-button>
            </n-form-item>
          </n-form>
        </div>
      </n-tab-pane>

      <!-- Tab 2: API -->
      <n-tab-pane name="api" tab="API配置">
        <div class="config-section">
          <n-form :model="apiForm" label-placement="left" label-width="100">
            <n-form-item label="提供商">
              <n-select v-model:value="apiForm.provider" :options="providerOptions" placeholder="选择API提供商" />
            </n-form-item>
            <n-form-item label="API Key">
              <n-input v-model:value="apiForm.api_key" type="password" show-password-on="click" placeholder="输入API密钥" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="apiForm.base_url" placeholder="https://api.example.com/v1" />
            </n-form-item>
            <n-form-item label="模型">
              <n-input v-model:value="apiForm.model" placeholder="gpt-4o-mini" />
            </n-form-item>
            <n-form-item>
              <n-space>
                <n-button type="primary" :loading="saving.api" @click="saveApiConfig">保存配置</n-button>
                <n-button :loading="testing" @click="testApiConnection">测试连接</n-button>
              </n-space>
            </n-form-item>
          </n-form>
        </div>
      </n-tab-pane>

      <!-- Tab 3: SMTP -->
      <n-tab-pane name="smtp" tab="邮件配置">
        <div class="config-section">
          <n-form :model="smtpForm" label-placement="left" label-width="120">
            <n-form-item label="SMTP Host">
              <n-input v-model:value="smtpForm.smtp_host" placeholder="smtp.example.com" />
            </n-form-item>
            <n-form-item label="SMTP Port">
              <n-input-number v-model:value="smtpForm.smtp_port" :min="1" :max="65535" style="width: 100%" />
            </n-form-item>
            <n-form-item label="用户名">
              <n-input v-model:value="smtpForm.smtp_username" placeholder="user@example.com" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input v-model:value="smtpForm.smtp_password" type="password" show-password-on="click" placeholder="SMTP密码" />
            </n-form-item>
            <n-form-item label="发件人地址">
              <n-input v-model:value="smtpForm.smtp_sender" placeholder="noreply@example.com" />
            </n-form-item>
            <n-form-item label="使用TLS">
              <n-switch v-model:value="smtpForm.smtp_use_tls" />
            </n-form-item>
            <n-form-item>
              <n-space>
                <n-button type="primary" :loading="saving.smtp" @click="saveSmtpConfig">保存配置</n-button>
                <n-button :loading="testingSmtp" @click="testSmtp">测试发送</n-button>
              </n-space>
            </n-form-item>
          </n-form>
          <n-modal v-model:show="showSmtpTestModal" preset="card" title="测试发送邮件" style="width: 400px">
            <n-form label-placement="left" label-width="80">
              <n-form-item label="收件人">
                <n-input v-model:value="smtpTestEmail" placeholder="test@example.com" />
              </n-form-item>
            </n-form>
            <template #action>
              <n-button @click="showSmtpTestModal = false">取消</n-button>
              <n-button type="primary" :loading="testingSmtp" @click="doTestSmtp">发送</n-button>
            </template>
          </n-modal>
        </div>
      </n-tab-pane>

      <!-- Tab 4: Payment -->
      <n-tab-pane name="payment" tab="支付配置">
        <div class="config-section">
          <n-form :model="paymentForm" label-placement="left" label-width="140">
            <n-form-item label="启用在线支付">
              <n-switch v-model:value="paymentForm.payment_enabled" />
            </n-form-item>
            <n-form-item label="启用手动转账">
              <n-switch v-model:value="paymentForm.manual_transfer_enabled" />
            </n-form-item>
            <n-form-item label="启用卡密兑换">
              <n-switch v-model:value="paymentForm.card_code_enabled" />
            </n-form-item>
            <n-divider />
            <h3 style="margin: 0 0 16px; font-size: 15px; font-weight: 600; color: #1e293b;">支付宝配置</h3>
            <n-form-item label="App ID">
              <n-input v-model:value="paymentForm.alipay_app_id" placeholder="支付宝应用App ID" />
            </n-form-item>
            <n-form-item label="应用私钥">
              <n-input v-model:value="paymentForm.alipay_private_key" type="textarea" :rows="3" placeholder="RSA2私钥" />
            </n-form-item>
            <n-form-item label="支付宝公钥">
              <n-input v-model:value="paymentForm.alipay_public_key" type="textarea" :rows="3" placeholder="支付宝公钥" />
            </n-form-item>
            <n-form-item label="异步通知地址">
              <n-input v-model:value="paymentForm.alipay_notify_url" placeholder="https://yourdomain.com/api/billing/alipay/notify" />
            </n-form-item>
            <n-form-item label="同步跳转地址">
              <n-input v-model:value="paymentForm.alipay_return_url" placeholder="https://yourdomain.com/account" />
            </n-form-item>
            <n-form-item>
              <n-button type="primary" :loading="saving.payment" @click="savePaymentConfig">保存配置</n-button>
            </n-form-item>
          </n-form>
        </div>
      </n-tab-pane>

      <!-- Tab 5: Membership -->
      <n-tab-pane name="membership" tab="会员配置">
        <div class="config-section">
          <div class="plan-cards">
            <div v-for="(plan, index) in membershipPlans" :key="index" class="plan-card">
              <div class="plan-card__header">
                <n-tag :type="plan.tier === 'pro' ? 'warning' : 'info'" round>{{ plan.tier === 'pro' ? '专业' : '基础' }}</n-tag>
              </div>
              <n-form :model="plan" label-placement="left" label-width="80" size="small">
                <n-form-item label="等级">
                  <n-select v-model:value="plan.tier" :options="[{ label: '基础', value: 'basic' }, { label: '专业', value: 'pro' }]" />
                </n-form-item>
                <n-form-item label="名称">
                  <n-input v-model:value="plan.name" />
                </n-form-item>
                <n-form-item label="价格(元)">
                  <n-input-number v-model:value="plan.price" :min="0" :precision="2" style="width: 100%" />
                </n-form-item>
                <n-form-item label="每日配额">
                  <n-input-number v-model:value="plan.daily_quota" :min="-1" style="width: 100%" />
                  <template #feedback>
                    <span style="font-size: 12px; color: #94a3b8;">-1 表示不限</span>
                  </template>
                </n-form-item>
                <n-form-item label="功能特性">
                  <n-dynamic-tags v-model:value="plan.features" />
                </n-form-item>
              </n-form>
              <n-button text type="error" size="small" @click="removePlan(index)" style="margin-top: 8px;">删除此套餐</n-button>
            </div>
          </div>
          <n-space style="margin-top: 16px;">
            <n-button dashed @click="addPlan">添加套餐</n-button>
            <n-button type="primary" :loading="saving.membership" @click="saveMembershipConfig">保存配置</n-button>
          </n-space>
        </div>
      </n-tab-pane>

      <!-- Tab 6: Generation -->
      <n-tab-pane name="generation" tab="生成参数">
        <div class="config-section">
          <n-form :model="genForm" label-placement="left" label-width="120">
            <n-form-item label="温度 (Temperature)">
              <n-slider v-model:value="genForm.temperature" :min="0" :max="2" :step="0.1" />
              <span class="param-value">{{ genForm.temperature }}</span>
            </n-form-item>
            <n-form-item label="Top P">
              <n-slider v-model:value="genForm.top_p" :min="0" :max="1" :step="0.05" />
              <span class="param-value">{{ genForm.top_p }}</span>
            </n-form-item>
            <n-form-item label="频率惩罚">
              <n-slider v-model:value="genForm.frequency_penalty" :min="0" :max="2" :step="0.1" />
              <span class="param-value">{{ genForm.frequency_penalty }}</span>
            </n-form-item>
            <n-form-item label="存在惩罚">
              <n-slider v-model:value="genForm.presence_penalty" :min="0" :max="2" :step="0.1" />
              <span class="param-value">{{ genForm.presence_penalty }}</span>
            </n-form-item>
            <n-form-item label="最大输出Token">
              <n-input-number v-model:value="genForm.max_tokens" :min="256" :max="32768" :step="256" style="width: 200px" />
            </n-form-item>
            <n-form-item label="章节字数下限">
              <n-input-number v-model:value="genForm.min_chapter_words" :min="500" :max="10000" :step="100" style="width: 200px" />
            </n-form-item>
            <n-form-item label="章节字数上限">
              <n-input-number v-model:value="genForm.max_chapter_words" :min="1000" :max="20000" :step="100" style="width: 200px" />
            </n-form-item>
            <n-form-item>
              <n-button type="primary" :loading="saving.generation" @click="saveGenerationConfig">保存配置</n-button>
            </n-form-item>
          </n-form>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useMessage, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSelect, NSwitch, NSlider, NButton, NSpace, NDivider, NDynamicTags, NTag, NModal } from 'naive-ui'
import { apiClient } from '../../api'
import PageHeader from '../../components/common/PageHeader.vue'
import LoadingCard from '../../components/common/LoadingCard.vue'

const message = useMessage()
const loading = ref(true)
const testing = ref(false)
const testingSmtp = ref(false)
const showSmtpTestModal = ref(false)
const smtpTestEmail = ref('')

const saving = reactive({
  basic: false,
  api: false,
  smtp: false,
  payment: false,
  membership: false,
  generation: false,
})

// Basic config
const basicForm = reactive({
  site_name: '',
  announcement: '',
})

// API config
const apiForm = reactive({
  provider: '',
  api_key: '',
  base_url: '',
  model: '',
})

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '通义千问', value: 'tongyi' },
  { label: 'ZhipuAI', value: 'zhipu' },
  { label: 'Moonshot', value: 'moonshot' },
  { label: '自定义', value: 'custom' },
]

// SMTP config
const smtpForm = reactive({
  smtp_host: '',
  smtp_port: 465,
  smtp_username: '',
  smtp_password: '',
  smtp_sender: '',
  smtp_use_tls: true,
})

// Payment config
const paymentForm = reactive({
  payment_enabled: false,
  manual_transfer_enabled: false,
  card_code_enabled: false,
  alipay_app_id: '',
  alipay_private_key: '',
  alipay_public_key: '',
  alipay_notify_url: '',
  alipay_return_url: '',
})

// Membership config
const membershipPlans = ref([
  { tier: 'basic', name: '基础会员', price: 29, daily_quota: 50, features: ['每天50次生成'] },
  { tier: 'pro', name: '专业会员', price: 99, daily_quota: -1, features: ['无限次生成', '优先处理'] },
])

// Generation config
const genForm = reactive({
  temperature: 0.7,
  top_p: 0.9,
  frequency_penalty: 0,
  presence_penalty: 0,
  max_tokens: 4096,
  min_chapter_words: 2000,
  max_chapter_words: 5000,
})

async function loadConfigs() {
  try {
    loading.value = true
    const results = await Promise.allSettled([
      apiClient.getAdminConfig(),
      apiClient.getApiConfig(),
      apiClient.getAdminSmtpConfig(),
      apiClient.getAdminPaymentConfig(),
      apiClient.getAdminMembershipConfig(),
      apiClient.getAdminGenerationConfig(),
    ])

    // Basic config
    if (results[0].status === 'fulfilled' && results[0].value?.data) {
      const configs = results[0].value.data
      const findCfg = (key) => {
        const item = configs.find(c => c.config_key === key)
        return item?.config_value || ''
      }
      basicForm.site_name = findCfg('site_name') || ''
      basicForm.announcement = findCfg('announcement') || ''
    }

    // API config
    if (results[1].status === 'fulfilled' && results[1].value?.data) {
      const d = results[1].value.data
      apiForm.provider = d.provider || ''
      apiForm.api_key = d.api_key || ''
      apiForm.base_url = d.base_url || ''
      apiForm.model = d.model || ''
    }

    // SMTP config
    if (results[2].status === 'fulfilled' && results[2].value?.data) {
      const d = results[2].value.data
      smtpForm.smtp_host = d.smtp_host || ''
      smtpForm.smtp_port = Number(d.smtp_port) || 465
      smtpForm.smtp_username = d.smtp_username || ''
      smtpForm.smtp_password = d.smtp_password || ''
      smtpForm.smtp_sender = d.smtp_sender || ''
      smtpForm.smtp_use_tls = d.smtp_use_tls !== false && d.smtp_use_tls !== 'false'
    }

    // Payment config
    if (results[3].status === 'fulfilled' && results[3].value?.data) {
      const d = results[3].value.data
      paymentForm.payment_enabled = d.payment_enabled === true || d.payment_enabled === 'true'
      paymentForm.manual_transfer_enabled = d.manual_transfer_enabled === true || d.manual_transfer_enabled === 'true'
      paymentForm.card_code_enabled = d.card_code_enabled === true || d.card_code_enabled === 'true'
      paymentForm.alipay_app_id = d.alipay_app_id || ''
      paymentForm.alipay_private_key = d.alipay_private_key || ''
      paymentForm.alipay_public_key = d.alipay_public_key || ''
      paymentForm.alipay_notify_url = d.alipay_notify_url || ''
      paymentForm.alipay_return_url = d.alipay_return_url || ''
    }

    // Membership config
    if (results[4].status === 'fulfilled' && results[4].value?.data) {
      const d = results[4].value.data
      const plans = d.config_value || d
      if (Array.isArray(plans)) {
        membershipPlans.value = plans.map(p => ({
          tier: p.tier || 'basic',
          name: p.name || '',
          price: Number(p.price) || 0,
          daily_quota: Number(p.daily_quota) ?? -1,
          features: Array.isArray(p.features) ? [...p.features] : [],
        }))
      }
    }

    // Generation config
    if (results[5].status === 'fulfilled' && results[5].value?.data) {
      const d = results[5].value.data
      const cfg = d.config_value || d
      if (typeof cfg === 'object') {
        genForm.temperature = Number(cfg.temperature) || 0.7
        genForm.top_p = Number(cfg.top_p) || 0.9
        genForm.frequency_penalty = Number(cfg.frequency_penalty) || 0
        genForm.presence_penalty = Number(cfg.presence_penalty) || 0
        genForm.max_tokens = Number(cfg.max_tokens) || 4096
        genForm.min_chapter_words = Number(cfg.min_chapter_words) || 2000
        genForm.max_chapter_words = Number(cfg.max_chapter_words) || 5000
      }
    }
  } catch (e) {
    message.error('加载配置失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function saveBasicConfig() {
  try {
    saving.basic = true
    await apiClient.saveAdminConfig({
      items: [
        { config_key: 'site_name', config_value: basicForm.site_name, value_type: 'string' },
        { config_key: 'announcement', config_value: basicForm.announcement, value_type: 'string' },
      ],
    })
    message.success('基础配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.basic = false
  }
}

async function saveApiConfig() {
  try {
    saving.api = true
    await apiClient.saveApiConfig(apiForm)
    message.success('API配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.api = false
  }
}

async function testApiConnection() {
  try {
    testing.value = true
    await apiClient.testApiConnection(apiForm)
    message.success('API连接测试成功')
  } catch (e) {
    message.error('连接测试失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

async function saveSmtpConfig() {
  try {
    saving.smtp = true
    await apiClient.saveAdminSmtpConfig(smtpForm)
    message.success('SMTP配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.smtp = false
  }
}

function testSmtp() {
  showSmtpTestModal.value = true
}

async function doTestSmtp() {
  if (!smtpTestEmail.value.trim()) {
    message.warning('请输入收件人邮箱')
    return
  }
  try {
    testingSmtp.value = true
    await apiClient.testAdminSmtp({ to_email: smtpTestEmail.value.trim() })
    message.success('测试邮件已发送')
    showSmtpTestModal.value = false
  } catch (e) {
    message.error('发送失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    testingSmtp.value = false
  }
}

async function savePaymentConfig() {
  try {
    saving.payment = true
    await apiClient.saveAdminPaymentConfig(paymentForm)
    message.success('支付配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.payment = false
  }
}

function addPlan() {
  membershipPlans.value.push({ tier: 'basic', name: '', price: 0, daily_quota: -1, features: [] })
}

function removePlan(index) {
  membershipPlans.value.splice(index, 1)
}

async function saveMembershipConfig() {
  try {
    saving.membership = true
    await apiClient.saveAdminMembershipConfig({ plans: membershipPlans.value })
    message.success('会员配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.membership = false
  }
}

async function saveGenerationConfig() {
  try {
    saving.generation = true
    await apiClient.saveAdminGenerationConfig({ config: { ...genForm } })
    message.success('生成参数配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.detail || e.message || '未知错误'))
  } finally {
    saving.generation = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.config-section {
  max-width: 720px;
  padding: 20px 0;
}

.param-value {
  display: inline-block;
  width: 48px;
  text-align: right;
  font-size: 14px;
  color: #64748b;
  margin-left: 12px;
  flex-shrink: 0;
}

.plan-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.plan-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
}

.plan-card__header {
  margin-bottom: 16px;
}
</style>
