<template>
  <div class="backend-help">
    <strong>{{ title }}</strong>
    <p>{{ detail }}</p>
    <code>{{ command }}</code>
    <div class="backend-help__actions">
      <n-button secondary @click="handleCopy">复制启动命令</n-button>
      <n-button tertiary @click="router.push({ name: 'Settings' })">打开设置页</n-button>
    </div>
  </div>
</template>

<script setup>
import { NButton, useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: {
    type: String,
    default: '后端服务未启动'
  },
  detail: {
    type: String,
    default: '当前页面无法加载实时数据，请先启动 FastAPI 后端服务。'
  },
  command: {
    type: String,
    default: 'python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000'
  }
})

const router = useRouter()
const message = useMessage()

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.command)
    message.success('启动命令已复制')
  } catch {
    message.error('复制失败，请手动复制命令')
  }
}
</script>

<style scoped>
.backend-help {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border-radius: 18px;
  border: 1px dashed rgba(239, 68, 68, 0.28);
  background: rgba(239, 68, 68, 0.06);
  color: #7f1d1d;
}

.backend-help p {
  margin: 0;
  line-height: 1.7;
}

.backend-help code {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  color: #111827;
  overflow-x: auto;
}

.backend-help__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
