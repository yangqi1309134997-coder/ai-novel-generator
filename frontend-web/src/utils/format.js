/**
 * 共享格式化工具函数
 */

/**
 * 格式化日期时间
 * @param {string|number|Date} value - 日期值
 * @param {string} fallback - 无效日期时的回退文本，默认 '未知'
 * @returns {string}
 */
export function formatDate(value, fallback = '未知') {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleString('zh-CN', { hour12: false })
}

/**
 * 显示标题，处理空标题或问号标题
 * @param {string} title - 原始标题
 * @param {string} fallbackPrefix - 无标题时的回退前缀
 * @returns {string}
 */
export function displayTitle(title, fallbackPrefix) {
  const text = String(title || '').trim()
  if (!text || /^\?+$/.test(text)) {
    return `${fallbackPrefix}记录`
  }
  return text
}
