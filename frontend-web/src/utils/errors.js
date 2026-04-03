export function normalizeErrorMessage(error, fallback = '请求失败') {
  return error?.detail || error?.message || fallback
}

export function isBackendAvailabilityError(error) {
  const text = `${error?.detail || ''} ${error?.message || ''}`
  return text.includes('后端服务不可达') || text.includes('请求超时')
}

export function notifyError(messageApi, error, fallback = '请求失败') {
  const text = normalizeErrorMessage(error, fallback)
  if (!isBackendAvailabilityError(error)) {
    messageApi.error(text)
  }
  return text
}
