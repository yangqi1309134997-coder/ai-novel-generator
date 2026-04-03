/**
 * 小说生成状态管理 - Pinia Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNovelStore = defineStore('novel', () => {
  const currentNovel = ref(null)
  const chapters = ref([])
  const generationProgress = ref(0)
  const isGenerating = ref(false)
  const logs = ref([])
  const config = ref({
    apiProvider: 'zhipu',
    apiKey: '',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4/',
    model: 'glm-4.7-flash'
  })
  const snowflakeData = ref({
    architecture: null,
    chapterBlueprint: null,
    currentStep: 'idle',
    progress: {
      architecture: 0,
      blueprint: 0,
      generation: 0
    }
  })
  const qualityReport = ref(null)

  const generationStatus = computed(() => {
    if (isGenerating.value) {
      return '生成中...'
    }
    if (chapters.value.length > 0) {
      return `已生成 ${chapters.value.length} 章`
    }
    return '未开始'
  })

  const canGenerate = computed(() => {
    return config.value.apiKey &&
      snowflakeData.value.architecture &&
      !isGenerating.value
  })

  const totalProgress = computed(() => {
    const { architecture, blueprint, generation } = snowflakeData.value.progress
    return Math.round((architecture + blueprint + generation) / 3)
  })

  function setConfig(newConfig) {
    config.value = { ...config.value, ...newConfig }
    localStorage.setItem('novel-config', JSON.stringify(config.value))
  }

  function loadConfig() {
    const saved = localStorage.getItem('novel-config')
    if (saved) {
      try {
        config.value = JSON.parse(saved)
      } catch (e) {
        console.error('加载配置失败:', e)
      }
    }
  }

  function updateProgress(step, progress) {
    if (step in snowflakeData.value.progress) {
      snowflakeData.value.progress[step] = progress
    }
    generationProgress.value = totalProgress.value
  }

  function addLog(message, type = 'info') {
    const log = {
      timestamp: new Date().toISOString(),
      message,
      type
    }
    logs.value.push(log)

    if (logs.value.length > 100) {
      logs.value = logs.value.slice(-100)
    }
  }

  function clearLogs() {
    logs.value = []
  }

  function setArchitecture(architecture) {
    snowflakeData.value.architecture = architecture
    snowflakeData.value.currentStep = 'blueprint'
    addLog('架构生成完成', 'success')
  }

  function setChapterBlueprint(blueprint) {
    snowflakeData.value.chapterBlueprint = blueprint
    snowflakeData.value.currentStep = 'completed'
    addLog('章节蓝图生成完成', 'success')
  }

  function addChapter(chapter) {
    chapters.value.push(chapter)
    addLog(`第${chapter.number}章生成完成`, 'success')
  }

  function startGenerating() {
    isGenerating.value = true
    snowflakeData.value.currentStep = 'generating'
    addLog('开始生成小说', 'info')
  }

  function stopGenerating() {
    isGenerating.value = false
    addLog('生成已停止', 'warning')
  }

  function completeGenerating() {
    isGenerating.value = false
    snowflakeData.value.currentStep = 'completed'
    addLog('小说生成完成', 'success')
  }

  function reset() {
    currentNovel.value = null
    chapters.value = []
    generationProgress.value = 0
    isGenerating.value = false
    logs.value = []
    snowflakeData.value = {
      architecture: null,
      chapterBlueprint: null,
      currentStep: 'idle',
      progress: {
        architecture: 0,
        blueprint: 0,
        generation: 0
      }
    }
    qualityReport.value = null
    addLog('状态已重置', 'info')
  }

  function setQualityReport(report) {
    qualityReport.value = report
    addLog('质量评估完成', 'info')
  }

  function exportProject(format = 'txt') {
    const data = {
      novel: currentNovel.value,
      chapters: chapters.value,
      architecture: snowflakeData.value.architecture,
      blueprint: snowflakeData.value.chapterBlueprint
    }

    let content
    let filename
    let mimeType

    switch (format) {
      case 'txt':
        content = exportAsTxt(data)
        filename = 'novel.txt'
        mimeType = 'text/plain'
        break
      case 'md':
        content = exportAsMarkdown(data)
        filename = 'novel.md'
        mimeType = 'text/markdown'
        break
      case 'json':
        content = JSON.stringify(data, null, 2)
        filename = 'novel.json'
        mimeType = 'application/json'
        break
      default:
        throw new Error(`不支持的导出格式: ${format}`)
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)

    addLog(`项目已导出为 ${filename}`, 'success')
  }

  function exportAsTxt(data) {
    let content = ''

    if (data.architecture) {
      content += '#=== 小说架构 ===\n\n'
      content += `主题：${data.architecture.core_seed || ''}\n\n`
      content += `角色：${data.architecture.character_dynamics || ''}\n\n`
      content += `世界观：${data.architecture.world_building || ''}\n\n`
    }

    content += '#=== 正文 ===\n\n'
    data.chapters.forEach(chapter => {
      content += `# ${chapter.title || '第' + chapter.number + '章'}\n\n`
      content += chapter.content || ''
      content += '\n\n'
    })

    return content
  }

  function exportAsMarkdown(data) {
    let content = `# ${data.novel?.title || '小说'}\n\n`

    if (data.architecture) {
      content += `## 架构\n\n`
      content += `**主题**: ${data.architecture.core_seed || ''}\n\n`
      content += `**角色**: ${data.architecture.character_dynamics || ''}\n\n`
      content += `**世界观**: ${data.architecture.world_building || ''}\n\n`
    }

    content += `## 正文\n\n`
    data.chapters.forEach(chapter => {
      content += `### ${chapter.title || '第' + chapter.number + '章'}\n\n`
      content += chapter.content || ''
      content += '\n\n'
    })

    return content
  }

  loadConfig()

  return {
    currentNovel,
    chapters,
    generationProgress,
    isGenerating,
    logs,
    config,
    snowflakeData,
    qualityReport,
    generationStatus,
    canGenerate,
    totalProgress,
    setConfig,
    loadConfig,
    updateProgress,
    addLog,
    clearLogs,
    setArchitecture,
    setChapterBlueprint,
    addChapter,
    startGenerating,
    stopGenerating,
    completeGenerating,
    reset,
    setQualityReport,
    exportProject
  }
})
