<template>
  <div class="login-view">
    <!-- Logo -->
    <div class="login-view__logo">
      <div class="login-view__logo-mark">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
      </div>
      <n-gradient-text type="info" :size="20" style="font-weight:700;">
        AI Novel Studio
      </n-gradient-text>
    </div>

    <!-- Title -->
    <h2 class="login-view__title">{{ codeSent ? '输入验证码' : '欢迎回来' }}</h2>
    <p class="login-view__subtitle">
      {{ codeSent ? `验证码已发送至 ${maskedEmail}` : '输入邮箱地址，我们将发送验证码到你的邮箱' }}
    </p>

    <!-- Alert -->
    <n-alert
      v-if="errorMessage"
      type="error"
      closable
      :show-icon="true"
      style="margin-bottom: 20px;"
      @close="errorMessage = ''"
    >
      {{ errorMessage }}
    </n-alert>

    <!-- Step 1: Email + Send Code -->
    <div class="login-view__field">
      <label class="login-view__label">邮箱地址</label>
      <n-input
        ref="emailInputRef"
        v-model:value="email"
        placeholder="请输入邮箱地址"
        size="large"
        :disabled="sendingCode || verifying"
        @keyup.enter="handleSendCode"
      >
        <template #prefix>
          <n-icon :size="18" color="#94a3b8">
            <mail-outline />
          </n-icon>
        </template>
      </n-input>
    </div>

    <n-button
      v-if="!codeSent"
      type="primary"
      block
      size="large"
      :loading="sendingCode"
      :disabled="!isEmailValid"
      class="login-view__btn"
      @click="handleSendCode"
    >
      {{ sendingCode ? '发送中...' : '发送验证码' }}
    </n-button>

    <!-- Countdown -->
    <div v-if="countdown > 0 && codeSent" class="login-view__countdown">
      <span>{{ countdown }}s 后可重新发送</span>
    </div>
    <n-button
      v-if="codeSent && countdown === 0"
      text
      type="primary"
      class="login-view__resend"
      :loading="sendingCode"
      @click="handleSendCode"
    >
      重新发送验证码
    </n-button>

    <!-- Step 2: Verification Code -->
    <div v-if="codeSent" class="login-view__field">
      <label class="login-view__label">验证码</label>
      <div class="login-view__otp">
        <input
          v-for="(_, index) in otpChars"
          :key="index"
          :ref="el => otpRefs[index] = el"
          v-model="otpChars[index]"
          class="login-view__otp-input"
          :class="{ 'login-view__otp-input--filled': otpChars[index]?.length }"
          maxlength="1"
          inputmode="numeric"
          pattern="[0-9]"
          autocomplete="one-time-code"
          :disabled="verifying"
          @input="handleOtpInput($event, index)"
          @keydown.backspace="handleOtpBackspace($event, index)"
          @paste="handleOtpPaste"
        />
      </div>
    </div>

    <n-button
      v-if="codeSent"
      type="primary"
      block
      size="large"
      :loading="verifying"
      :disabled="!isOtpComplete"
      class="login-view__btn"
      @click="handleVerify"
    >
      {{ verifying ? '验证中...' : '登录 / 注册' }}
    </n-button>

    <!-- Hint -->
    <p class="login-view__hint">
      首次使用该邮箱将自动注册账号
    </p>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NGradientText, NIcon, NInput, useMessage } from 'naive-ui'
import { MailOutline } from '@vicons/ionicons5'
import { apiClient } from '../api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const email = ref('')
const codeSent = ref(false)
const sendingCode = ref(false)
const verifying = ref(false)
const countdown = ref(0)
const errorMessage = ref('')
const otpChars = reactive(['', '', '', '', '', ''])
const otpRefs = ref([])
const emailInputRef = ref(null)

let countdownTimer = null

/* ---- computed ---- */
const isEmailValid = computed(() => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())
})

const isOtpComplete = computed(() => {
  return otpChars.every(c => /^\d$/.test(c))
})

const maskedEmail = computed(() => {
  const e = email.value.trim()
  if (!e) return ''
  const [local, domain] = e.split('@')
  if (!domain) return e
  const visible = local.slice(0, 2)
  return `${visible}***@${domain}`
})

/* ---- methods ---- */
function getRedirectTarget() {
  const redirect = route.query.redirect
  return redirect ? String(redirect) : '/workspace'
}

function startCountdown() {
  countdown.value = 60
  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function handleSendCode() {
  if (!isEmailValid.value || sendingCode.value) return
  errorMessage.value = ''
  sendingCode.value = true

  try {
    await apiClient.sendVerificationCode(email.value.trim())
    codeSent.value = true
    startCountdown()
    message.success('验证码已发送')
    await nextTick()
    otpRefs.value[0]?.focus()
  } catch (err) {
    errorMessage.value = err?.detail || err?.message || '发送验证码失败，请稍后重试'
  } finally {
    sendingCode.value = false
  }
}

function handleOtpInput(event, index) {
  const value = event.target.value.replace(/\D/g, '')
  otpChars[index] = value

  if (value && index < 5) {
    nextTick(() => {
      otpRefs.value[index + 1]?.focus()
    })
  }

  // Auto-submit when all filled
  if (otpChars.every(c => /^\d$/.test(c))) {
    nextTick(() => handleVerify())
  }
}

function handleOtpBackspace(event, index) {
  if (!otpChars[index] && index > 0) {
    otpChars[index - 1] = ''
    nextTick(() => {
      otpRefs.value[index - 1]?.focus()
    })
  }
}

function handleOtpPaste(event) {
  event.preventDefault()
  const text = (event.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 6)
  if (!text) return

  for (let i = 0; i < 6; i++) {
    otpChars[i] = text[i] || ''
  }
  const focusIndex = Math.min(text.length, 5)
  nextTick(() => {
    otpRefs.value[focusIndex]?.focus()
  })

  if (text.length === 6) {
    nextTick(() => handleVerify())
  }
}

async function handleVerify() {
  if (!isOtpComplete.value || verifying.value) return
  errorMessage.value = ''
  verifying.value = true

  const code = otpChars.join('')

  try {
    const response = await apiClient.verifyCode(email.value.trim(), code)
    authStore.setSession(response)
    message.success('登录成功')

    if (countdownTimer) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }

    router.push(getRedirectTarget())
  } catch (err) {
    errorMessage.value = err?.detail || err?.message || '验证失败，请检查验证码'
  } finally {
    verifying.value = false
  }
}

onMounted(() => {
  emailInputRef.value?.focus()
})
</script>

<style scoped>
.login-view {
  width: 100%;
}

/* Logo */
.login-view__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 28px;
}

.login-view__logo-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

/* Title */
.login-view__title {
  margin: 0;
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.login-view__subtitle {
  margin: 8px 0 0;
  text-align: center;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}

/* Fields */
.login-view__field {
  margin-top: 24px;
}

.login-view__label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

/* Button */
.login-view__btn {
  margin-top: 20px;
  height: 48px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
}

/* Countdown */
.login-view__countdown {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;
  color: #94a3b8;
}

.login-view__resend {
  display: block;
  margin: 12px auto 0;
  font-size: 13px;
}

/* OTP inputs */
.login-view__otp {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.login-view__otp-input {
  width: 48px;
  height: 56px;
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  outline: none;
  background: #f8fafc;
  color: #0f172a;
  transition: all 0.2s ease;
  caret-color: #6366f1;
}

.login-view__otp-input:focus {
  border-color: #6366f1;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.login-view__otp-input--filled {
  border-color: #6366f1;
  background: #fff;
}

.login-view__otp-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Hint */
.login-view__hint {
  margin: 24px 0 0;
  text-align: center;
  font-size: 13px;
  color: #94a3b8;
}

/* Responsive */
@media (max-width: 520px) {
  .login-view__otp-input {
    width: 42px;
    height: 50px;
    font-size: 20px;
  }

  .login-view__otp {
    gap: 6px;
  }
}
</style>
