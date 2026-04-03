/**
 * WebSocket 实时通信
 * 用于接收生成进度和日志
 */

import { ref, onUnmounted } from 'vue'

export function useWebSocket(url = 'ws://localhost:8000/ws') {
  const socket = ref(null)
  const connected = ref(false)
  const progress = ref(0)
  const logs = ref([])
  const error = ref(null)

  /**
   * 连接WebSocket
   */
  function connect() {
    try {
      socket.value = new WebSocket(url)

      socket.value.onopen = () => {
        console.log('[WebSocket] 已连接')
        connected.value = true
        error.value = null
      }

      socket.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleMessage(data)
        } catch (e) {
          console.error('[WebSocket] 解析消息失败:', e)
        }
      }

      socket.value.onerror = (event) => {
        console.error('[WebSocket] 错误:', event)
        error.value = 'WebSocket连接错误'
      }

      socket.value.onclose = () => {
        console.log('[WebSocket] 已断开')
        connected.value = false

        // 自动重连
        setTimeout(() => {
          if (!connected.value) {
            console.log('[WebSocket] 尝试重连...')
            connect()
          }
        }, 3000)
      }
    } catch (e) {
      console.error('[WebSocket] 连接失败:', e)
      error.value = e.message
    }
  }

  /**
   * 处理消息
   */
  function handleMessage(data) {
    switch (data.type) {
      case 'progress':
        progress.value = data.value
        break

      case 'log':
        logs.value.push({
          timestamp: new Date().toISOString(),
          message: data.message,
          level: data.level || 'info'
        })

        // 限制日志数量
        if (logs.value.length > 100) {
          logs.value = logs.value.slice(-100)
        }
        break

      case 'chapter':
        // 新章节生成完成
        console.log('[WebSocket] 新章节:', data.chapter)
        break

      case 'complete':
        // 生成完成
        console.log('[WebSocket] 生成完成')
        break

      case 'error':
        error.value = data.message
        console.error('[WebSocket] 错误:', data.message)
        break

      default:
        console.log('[WebSocket] 未知消息类型:', data.type)
    }
  }

  /**
   * 发送消息
   */
  function send(data) {
    if (socket.value && connected.value) {
      socket.value.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] 未连接，无法发送消息')
    }
  }

  /**
   * 断开连接
   */
  function disconnect() {
    if (socket.value) {
      socket.value.close()
      socket.value = null
      connected.value = false
    }
  }

  /**
   * 清空日志
   */
  function clearLogs() {
    logs.value = []
  }

  // 组件卸载时断开连接
  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    progress,
    logs,
    error,
    connect,
    disconnect,
    send,
    clearLogs
  }
}
