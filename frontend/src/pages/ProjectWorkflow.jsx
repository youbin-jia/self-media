import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Steps, Card, Button, message, Spin, Typography, Divider, Space, Tag, Alert, Progress, Collapse, Input, List, Popconfirm, Modal, Switch, Badge, Drawer } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  SaveOutlined,
  HistoryOutlined,
  RollbackOutlined,
  DiffOutlined,
  DeleteOutlined
} from '@ant-design/icons'
import {
  getProject,
  executeStep,
  regenerateStep,
  updateProjectScript,
  getProjectScript,
  getProjectScriptHistory,
  rollbackProjectScript,
  aiReviseProjectScript,
  deleteProjectScriptHistory,
  clearProjectScriptHistory
} from '../services/api'
import AnimatedNumber from '../components/AnimatedNumber'
import ReactMarkdown from 'react-markdown'

const { Title, Paragraph } = Typography

const workflowSteps = [
  { key: 'script', title: '脚本生成' },
  { key: 'review', title: '脚本审核' },
  { key: 'visual', title: '视觉规划' },
  { key: 'audio', title: '音频生成' },
  { key: 'video', title: '视频合成' }
]

const stageLabelMap = {
  queued: '排队中',
  outline_generating: '生成大纲',
  outline_done: '大纲已完成',
  script_generating: '生成完整脚本',
  review_loading: '读取脚本',
  review_analyzing: '审核分析',
  review_persisting: '整理报告',
  persisting: '保存结果',
  fallback_generating: '离线占位生成',
  running: '执行中',
  completed: '已完成',
  failed: '执行失败'
}

function ProjectWorkflow() {
  const COMPACT_MODE_KEY = 'self-media-workflow-compact-mode'
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [editingScript, setEditingScript] = useState(false)
  const [scriptDraft, setScriptDraft] = useState('')
  const [savingScript, setSavingScript] = useState(false)
  const [scriptHistory, setScriptHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [rollingBackId, setRollingBackId] = useState(null)
  const [deletingHistoryId, setDeletingHistoryId] = useState(null)
  const [clearingHistory, setClearingHistory] = useState(false)
  const [historyModalOpen, setHistoryModalOpen] = useState(false)
  const [aiRevisionLoading, setAiRevisionLoading] = useState(false)
  const [aiRevisionApplying, setAiRevisionApplying] = useState(false)
  const [aiRevisionCandidate, setAiRevisionCandidate] = useState(null)
  const [reviewScoreChange, setReviewScoreChange] = useState(null)
  const [reviewTrend, setReviewTrend] = useState([])
  const [outlinePromptDraft, setOutlinePromptDraft] = useState('')
  const [fullScriptPromptDraft, setFullScriptPromptDraft] = useState('')
  const [promptDirty, setPromptDirty] = useState(false)
  const [promptEditorVisible, setPromptEditorVisible] = useState(false)
  const [runningStepKey, setRunningStepKey] = useState('')
  const [lastFailedStepKey, setLastFailedStepKey] = useState('')
  const [activeAnchor, setActiveAnchor] = useState('insight')
  const [scriptEditTip, setScriptEditTip] = useState('')
  const [compactMode, setCompactMode] = useState(() => {
    const cached = localStorage.getItem(COMPACT_MODE_KEY)
    return cached !== '0'
  })
  const [diffModal, setDiffModal] = useState({
    open: false,
    title: '',
    outlineDiff: [],
    fullScriptDiff: []
  })
  const refreshTimerRef = useRef(null)

  useEffect(() => {
    loadProject()
    loadScriptHistory()
  }, [id])

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(COMPACT_MODE_KEY, compactMode ? '1' : '0')
  }, [compactMode])

  useEffect(() => {
    const sectionIds = ['script-section-insight', 'script-section-output']
    const idToKey = {
      'script-section-insight': 'insight',
      'script-section-output': 'output'
    }

    const sections = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean)

    if (!sections.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible.length) {
          const key = idToKey[visible[0].target.id]
          if (key) setActiveAnchor(key)
        }
      },
      {
        root: null,
        rootMargin: '-80px 0px -55% 0px',
        threshold: [0.15, 0.35, 0.6]
      }
    )

    sections.forEach((node) => observer.observe(node))
    return () => observer.disconnect()
  }, [project, scriptHistory.length])

  const loadProject = async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const response = await getProject(id)
      const projectData = response.data

      try {
        const scriptRes = await getProjectScript(id)
        const scriptData = scriptRes.data
        const metadata = { ...(projectData.metadata || {}) }
        const steps = { ...(metadata.steps || {}) }
        const scriptStep = { ...(steps.script || {}) }
        const output = { ...(scriptStep.output || {}) }

        if (scriptData.outline) output.outline = scriptData.outline
        if (scriptData.full_script) output.full_script = scriptData.full_script
        if (Array.isArray(scriptData.segments)) output.segments_count = scriptData.segments.length

        scriptStep.output = output
        steps.script = scriptStep
        metadata.steps = steps
        projectData.metadata = metadata
      } catch {
        // If script endpoint not ready, keep project payload only.
      }

      setProject(projectData)
      updateCurrentStep(projectData)

      const scriptOutput = projectData?.metadata?.steps?.script?.output || {}
      const llmInput = scriptOutput.llm_input || {}
      if (!promptDirty) {
        setOutlinePromptDraft(llmInput.outline_prompt || '')
        setFullScriptPromptDraft(llmInput.full_script_prompt || '')
      }
      return projectData
    } catch (error) {
      if (!silent) message.error('加载项目失败')
      return null
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const sleep = (ms) => new Promise((resolve) => {
    setTimeout(resolve, ms)
  })

  const waitForStepSettled = async (stepName, timeoutMs = 180000) => {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      const data = await loadProject(true)
      const current = data?.steps?.[stepName] || data?.metadata?.steps?.[stepName]
      if (current?.status && current.status !== 'processing') return current
      await sleep(1200)
    }
    return null
  }

  const loadScriptHistory = async () => {
    try {
      setLoadingHistory(true)
      const response = await getProjectScriptHistory(id, 20)
      setScriptHistory(response.data || [])
    } catch {
      // Keep page usable if history endpoint fails.
      setScriptHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  const updateCurrentStep = (projectData) => {
    const stepsData = projectData?.steps || projectData?.metadata?.steps
    if (!stepsData) return
    const stepIndex = workflowSteps.findIndex(
      step => stepsData[step.key]?.status !== 'completed'
    )
    setCurrentStep(stepIndex === -1 ? workflowSteps.length - 1 : stepIndex)
  }

  const runStepAction = async (stepName, mode = 'execute') => {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
    setRunningStepKey(stepName)

    // Start polling immediately and keep polling while backend task runs.
    await loadProject(true)
    refreshTimerRef.current = setInterval(() => {
      loadProject(true)
    }, 1200)

    const messageKey = mode === 'execute' ? 'execute' : 'regenerate'
    const loadingText = mode === 'execute' ? '执行中...' : '重新生成中...'
    const successText = mode === 'execute' ? '执行成功' : '重新生成成功'
    const failText = mode === 'execute' ? '执行失败' : '重新生成失败'
    let handedOffToBackgroundSync = false

    const startBackgroundSyncUntilSettled = () => {
      handedOffToBackgroundSync = true
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
      const startedAt = Date.now()
      refreshTimerRef.current = setInterval(async () => {
        const data = await loadProject(true)
        const current = data?.steps?.[stepName] || data?.metadata?.steps?.[stepName]
        const status = current?.status
        if (status && status !== 'processing') {
          clearInterval(refreshTimerRef.current)
          refreshTimerRef.current = null
          setRunningStepKey('')
          if (status === 'failed') {
            focusFailedStep(stepName)
            const reason = current?.progress?.message || current?.output?.error || current?.output?.reason || failText
            message.error({ content: reason, key: messageKey })
          } else {
            setLastFailedStepKey((prev) => (prev === stepName ? '' : prev))
            message.success({ content: successText, key: messageKey })
          }
          await loadScriptHistory()
          return
        }
        if (Date.now() - startedAt > 180000) {
          clearInterval(refreshTimerRef.current)
          refreshTimerRef.current = null
          setRunningStepKey('')
          message.warning({ content: '后台处理时间较长，请稍后刷新查看最终状态', key: messageKey })
        }
      }, 1200)
    }

    try {
      message.loading({ content: loadingText, key: messageKey })
      const payload = {}
      if (stepName === 'script') {
        if (outlinePromptDraft?.trim()) payload.outline_prompt = outlinePromptDraft.trim()
        if (fullScriptPromptDraft?.trim()) payload.full_script_prompt = fullScriptPromptDraft.trim()
      }

      if (mode === 'execute') {
        await executeStep(id, stepName, stepName === 'script' ? payload : undefined)
      } else {
        await regenerateStep(id, stepName, stepName === 'script' ? payload : undefined)
      }
      setLastFailedStepKey((prev) => (prev === stepName ? '' : prev))
      const settled = await waitForStepSettled(stepName, 30000)
      const settledStatus = settled?.status
      if (!settled) {
        message.loading({ content: '后台仍在处理中，继续同步状态...', key: messageKey })
        startBackgroundSyncUntilSettled()
      } else if (settledStatus === 'failed') {
        focusFailedStep(stepName)
        const reason = settled?.progress?.message || settled?.output?.error || settled?.output?.reason || failText
        message.error({ content: reason, key: messageKey })
      } else {
        message.success({ content: successText, key: messageKey })
      }
      await loadScriptHistory()
    } catch (error) {
      const timeoutLike = error?.code === 'ECONNABORTED' || `${error?.message || ''}`.toLowerCase().includes('timeout')
      if (timeoutLike) {
        message.loading({ content: '请求超时，后台可能仍在处理中，正在继续同步状态...', key: messageKey })
      }
      const settled = await waitForStepSettled(stepName, 180000)
      if (!settled) {
        message.loading({ content: '请求失败，但后台可能仍在处理中，继续同步状态...', key: messageKey })
        startBackgroundSyncUntilSettled()
      } else if (settled.status === 'failed') {
        focusFailedStep(stepName)
        const reason = settled?.progress?.message || settled?.output?.error || settled?.output?.reason || failText
        message.error({ content: reason, key: messageKey })
      } else {
        setLastFailedStepKey((prev) => (prev === stepName ? '' : prev))
        message.success({ content: successText, key: messageKey })
      }
      await loadScriptHistory()
    } finally {
      if (!handedOffToBackgroundSync && refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
        refreshTimerRef.current = null
      }
      if (!handedOffToBackgroundSync) {
        setRunningStepKey('')
      }
    }
  }

  const handleExecuteStep = async (stepName) => runStepAction(stepName, 'execute')

  const handleRegenerateStep = async (stepName) => runStepAction(stepName, 'regenerate')

  const getStepStatus = (stepKey) => {
    const step = project?.steps?.[stepKey] || project?.metadata?.steps?.[stepKey]
    if (!step) return 'wait'
    if (step.status === 'completed') return 'finish'
    if (step.status === 'processing') return 'process'
    if (step.status === 'failed') return 'error'
    return 'wait'
  }

  const getStatusMeta = (stepKey) => {
    const step = project?.steps?.[stepKey] || project?.metadata?.steps?.[stepKey]
    const status = step?.status || 'wait'
    const serverPercent = Number(step?.progress?.percent)
    const progress = Number.isFinite(serverPercent)
      ? Math.max(0, Math.min(100, serverPercent))
      : (status === 'completed' ? 100 : status === 'processing' ? 15 : 0)
    if (status === 'failed') {
      return { cardColor: '#fff2f0', borderColor: '#ffccc7', tagColor: 'error', text: '失败', progress }
    }
    if (status === 'completed') {
      return { cardColor: '#f6ffed', borderColor: '#b7eb8f', tagColor: 'success', text: '已完成', progress }
    }
    if (status === 'processing') {
      return { cardColor: '#e6f4ff', borderColor: '#91caff', tagColor: 'processing', text: '执行中', progress }
    }
    return { cardColor: '#fafafa', borderColor: '#d9d9d9', tagColor: 'default', text: '待执行', progress }
  }

  const getStageLabel = (stage) => stageLabelMap[stage] || (stage || '-')

  const toIntSeconds = (value) => {
    const n = Number(value)
    if (!Number.isFinite(n)) return null
    return Math.max(0, Math.round(n))
  }

  const getElapsedSeconds = (startIso, endIso) => {
    if (!startIso) return null
    const start = new Date(startIso)
    const end = endIso ? new Date(endIso) : new Date()
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
    return Math.max(0, Math.floor((end.getTime() - start.getTime()) / 1000))
  }

  const getEtaSeconds = (progress) => {
    const percent = Number(progress?.percent)
    const elapsed = Number(progress?.total_duration_sec)
    if (!Number.isFinite(percent) || !Number.isFinite(elapsed)) return null
    if (percent <= 0 || percent >= 100) return percent >= 100 ? 0 : null
    const eta = Math.round((elapsed / percent) * (100 - percent))
    return Math.max(0, eta)
  }

  const focusFailedStep = (stepKey) => {
    setLastFailedStepKey(stepKey)
    const node = document.getElementById(`step-card-${stepKey}`)
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const completedCount = workflowSteps.filter((step) => getStepStatus(step.key) === 'finish').length
  const overallPercent = Math.round((completedCount / workflowSteps.length) * 100)

  const renderMultilineText = (text) => {
    if (!text) return <Paragraph type="secondary">暂无内容</Paragraph>
    const content = String(text)
    if (needCollapse(content)) {
      return (
        <Collapse
          size="small"
          items={[
            {
              key: 'full-script-preview',
              label: '展开查看完整脚本',
              children: (
                <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                  {content}
                </Paragraph>
              )
            }
          ]}
        />
      )
    }
    return (
      <Paragraph
        style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}
        ellipsis={{ rows: compactMode ? 5 : 8 }}
      >
        {content}
      </Paragraph>
    )
  }

  const needCollapse = (text) => {
    if (!text) return false
    const content = String(text)
    return content.length > 500 || content.split('\n').length > 12
  }

  const calcLineDiff = (baseText, currentText) => {
    const before = String(baseText || '').split('\n')
    const after = String(currentText || '').split('\n')
    const maxLen = Math.max(before.length, after.length)
    const rows = []
    for (let i = 0; i < maxLen; i += 1) {
      const oldLine = before[i]
      const newLine = after[i]
      if (oldLine === newLine) continue
      if (oldLine !== undefined) {
        rows.push({ type: 'removed', line: i + 1, text: oldLine })
      }
      if (newLine !== undefined) {
        rows.push({ type: 'added', line: i + 1, text: newLine })
      }
    }
    return rows
  }

  const openHistoryDiff = (item, index) => {
    const base = scriptHistory[index + 1]
    const outlineDiff = calcLineDiff(base?.outline, item?.outline)
    const fullScriptDiff = calcLineDiff(base?.full_script, item?.full_script)
    setDiffModal({
      open: true,
      title: base
        ? `版本 v${item.version} 对比 v${base.version}`
        : `版本 v${item.version}（无更早版本可对比）`,
      outlineDiff,
      fullScriptDiff
    })
  }

  const renderDiffRows = (rows) => {
    if (!rows.length) {
      return <Alert type="info" showIcon message="该部分没有文本差异" />
    }
    return (
      <List
        size="small"
        dataSource={rows}
        renderItem={(row) => (
          <List.Item className={row.type === 'added' ? 'diff-line-added' : 'diff-line-removed'}>
            <Space wrap>
              <Tag color={row.type === 'added' ? 'success' : 'error'}>
                {row.type === 'added' ? '+' : '-'} 行 {row.line}
              </Tag>
              <Typography.Text style={{ whiteSpace: 'pre-wrap' }}>{row.text || '(空行)'}</Typography.Text>
            </Space>
          </List.Item>
        )}
      />
    )
  }

  const handleStartEditScript = (fullScript) => {
    setScriptDraft(fullScript || '')
    setEditingScript(true)
    setScriptEditTip('')
  }

  const handleCancelEditScript = () => {
    setEditingScript(false)
    setScriptDraft('')
    setScriptEditTip('')
  }

  const handleSaveScript = async () => {
    try {
      setSavingScript(true)
      await updateProjectScript(id, { full_script: scriptDraft })
      message.success('完整脚本已保存')
      setEditingScript(false)
      setScriptEditTip('')
      await loadProject()
      await loadScriptHistory()
    } catch (error) {
      message.error('保存脚本失败')
    } finally {
      setSavingScript(false)
    }
  }

  const handleRollback = async (historyId) => {
    try {
      setRollingBackId(historyId)
      await rollbackProjectScript(id, historyId)
      message.success('已回滚到历史版本')
      await loadProject()
      await loadScriptHistory()
    } catch {
      message.error('回滚失败')
    } finally {
      setRollingBackId(null)
    }
  }

  const handleDeleteHistory = async (historyId) => {
    try {
      setDeletingHistoryId(historyId)
      await deleteProjectScriptHistory(id, historyId)
      message.success('已删除该历史版本')
      await loadScriptHistory()
    } catch {
      message.error('删除历史版本失败')
    } finally {
      setDeletingHistoryId(null)
    }
  }

  const handleClearHistory = async () => {
    try {
      setClearingHistory(true)
      await clearProjectScriptHistory(id)
      message.success('已清空历史版本')
      await loadScriptHistory()
    } catch {
      message.error('清空历史版本失败')
    } finally {
      setClearingHistory(false)
    }
  }

  const handleAiReviseFromReview = async (reviewOutput) => {
    try {
      setAiRevisionLoading(true)
      const issues = Array.isArray(reviewOutput?.issues) ? reviewOutput.issues : []
      const recommendations = Array.isArray(reviewOutput?.recommendations) ? reviewOutput.recommendations : []
      const response = await aiReviseProjectScript(id, { issues, recommendations })
      const data = response.data
      const diffRows = calcLineDiff(data?.original_full_script || '', data?.revised_full_script || '')
      setAiRevisionCandidate({
        original: data?.original_full_script || '',
        revised: data?.revised_full_script || '',
        diffRows,
        llmInput: data?.llm_input || null,
        baseVersion: data?.script_version || null,
        generatedAt: data?.generated_at || null,
        stale: false,
        currentVersion: data?.script_version || null
      })
      message.success('已生成 AI 修订候选稿，请确认后采纳')
    } catch (error) {
      const detail = error?.response?.data?.detail
      message.error(detail || 'AI 修订失败')
    } finally {
      setAiRevisionLoading(false)
    }
  }

  const handleApplyAiRevision = async (force = false) => {
    if (!aiRevisionCandidate?.revised) return
    try {
      setAiRevisionApplying(true)
      const reviewStepBefore = project?.steps?.review || project?.metadata?.steps?.review
      const scoreBefore = Number(reviewStepBefore?.output?.score)
      const gradeBefore = reviewStepBefore?.output?.grade || null
      const latestScriptRes = await getProjectScript(id)
      const latestVersion = latestScriptRes?.data?.version
      const baseVersion = aiRevisionCandidate?.baseVersion
      if (!force && baseVersion && latestVersion && Number(latestVersion) !== Number(baseVersion)) {
        setAiRevisionCandidate((prev) => ({
          ...prev,
          stale: true,
          currentVersion: latestVersion
        }))
        message.warning('检测到脚本已有新版本，请确认后使用“强制覆盖采纳”')
        return
      }
      await updateProjectScript(id, { full_script: aiRevisionCandidate.revised })
      message.loading({ content: '已采纳修订，正在自动复审...', key: 'ai-apply-review' })
      await executeStep(id, 'review')
      const settledReview = await waitForStepSettled('review', 120000)
      const scoreAfter = Number(settledReview?.output?.score)
      const gradeAfter = settledReview?.output?.grade || null
      if (settledReview?.status === 'completed' && settledReview?.output?.mode === 'real_review' && Number.isFinite(scoreAfter)) {
        const delta = Number.isFinite(scoreBefore) ? Number((scoreAfter - scoreBefore).toFixed(2)) : null
        const nowIso = new Date().toISOString()
        setReviewScoreChange({
          beforeScore: Number.isFinite(scoreBefore) ? scoreBefore : null,
          afterScore: scoreAfter,
          beforeGrade: gradeBefore,
          afterGrade: gradeAfter,
          delta,
          updatedAt: nowIso
        })
        setReviewTrend((prev) => {
          const next = [
            ...prev,
            {
              score: scoreAfter,
              grade: gradeAfter || '-',
              delta,
              at: nowIso
            }
          ]
          return next.slice(-6)
        })
        if (delta !== null) {
          const trend = delta >= 0 ? `+${delta}` : `${delta}`
          message.success({ content: `自动复审完成，评分变化 ${trend}`, key: 'ai-apply-review' })
        } else {
          message.success({ content: '自动复审完成', key: 'ai-apply-review' })
        }
      } else {
        message.warning({ content: '已保存修订稿，但自动复审未返回有效结果，请手动复审', key: 'ai-apply-review' })
      }
      setAiRevisionCandidate(null)
      await loadProject()
      await loadScriptHistory()
    } catch {
      message.error('采纳 AI 修订失败')
    } finally {
      setAiRevisionApplying(false)
    }
  }

  const jumpToScriptOutput = () => {
    setActiveAnchor('output')
    const node = document.getElementById('script-section-output')
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const buildReviewInsertTemplate = ({ type = '', severity = '', message: reviewMessage = '', recommendation = '' }) => {
    const now = new Date().toLocaleString('zh-CN', { hour12: false })
    return [
      '【审核修改任务】',
      `- 时间：${now}`,
      `- 问题类型：${type || '未分类'}`,
      `- 严重级别：${severity || 'medium'}`,
      `- 问题描述：${reviewMessage || '请根据审核结果优化脚本'}`,
      `- 修改建议：${recommendation || '请结合上下文优化表达、结构与节奏'}`,
      '- 修改结果：',
      '- [在此填写你修改后的关键片段或说明]',
      '【审核修改任务结束】'
    ].join('\n')
  }

  const buildReviewReplaceTemplate = ({ type = '', severity = '', message: reviewMessage = '', recommendation = '', originalText = '' }) => {
    const now = new Date().toLocaleString('zh-CN', { hour12: false })
    return [
      '【审核定向修改】',
      `- 时间：${now}`,
      `- 问题类型：${type || '未分类'}`,
      `- 严重级别：${severity || 'medium'}`,
      `- 问题描述：${reviewMessage || '请根据审核结果优化脚本'}`,
      `- 修改建议：${recommendation || '请结合上下文优化表达、结构与节奏'}`,
      '',
      '【原片段】',
      originalText || '[未识别到原片段]',
      '',
      '【改写片段（请替换为优化后的内容）】',
      '- [在此填写改写后的正文]',
      '【审核定向修改结束】'
    ].join('\n')
  }

  const tokenizeKeywords = (...texts) => {
    const merged = texts
      .map((v) => String(v || ''))
      .join(' ')
      .toLowerCase()
    const chunks = merged.match(/[\u4e00-\u9fa5]{2,}|[a-z0-9]{3,}/g) || []
    return Array.from(new Set(chunks)).slice(0, 30)
  }

  const findBestScriptBlock = (scriptText, keywords) => {
    const blocks = String(scriptText || '')
      .split(/\n{2,}/)
      .map((b) => b.trim())
      .filter(Boolean)
    if (!blocks.length) return { index: -1, block: '' }
    if (!keywords.length) return { index: 0, block: blocks[0] }

    let bestIndex = 0
    let bestScore = -1
    blocks.forEach((block, idx) => {
      const lower = block.toLowerCase()
      let score = 0
      keywords.forEach((kw) => {
        if (lower.includes(kw)) score += 1
      })
      if (score > bestScore) {
        bestScore = score
        bestIndex = idx
      }
    })
    return { index: bestIndex, block: blocks[bestIndex] }
  }

  const insertReviewItemToScriptEditor = ({ issue, recommendation, source, mode = 'append' }) => {
    const scriptStep = project?.steps?.script || project?.metadata?.steps?.script
    const currentScript = editingScript ? scriptDraft : (scriptStep?.output?.full_script || '')
    if (!String(currentScript || '').trim() && mode === 'replace') {
      message.warning('当前没有可替换的脚本文本，已改为追加模式')
      mode = 'append'
    }

    const template = buildReviewInsertTemplate({
      type: issue?.type,
      severity: issue?.severity,
      message: issue?.message,
      recommendation
    })
    let merged = ''
    if (mode === 'append') {
      merged = currentScript
        ? `${String(currentScript).trimEnd()}\n\n${template}\n`
        : `${template}\n`
    } else {
      const keywords = tokenizeKeywords(issue?.message, recommendation, issue?.type, issue?.severity)
      const { index, block } = findBestScriptBlock(currentScript, keywords)
      if (index < 0 || !block) {
        merged = currentScript
          ? `${String(currentScript).trimEnd()}\n\n${template}\n`
          : `${template}\n`
        message.warning('未定位到相关片段，已改为追加插入')
      } else {
        const blocks = String(currentScript)
          .split(/\n{2,}/)
          .map((b) => b.trim())
          .filter(Boolean)
        const replaceTemplate = buildReviewReplaceTemplate({
          type: issue?.type,
          severity: issue?.severity,
          message: issue?.message,
          recommendation,
          originalText: block
        })
        blocks[index] = replaceTemplate
        merged = `${blocks.join('\n\n')}\n`
      }
    }

    setScriptDraft(merged)
    setEditingScript(true)
    if (mode === 'replace') {
      setScriptEditTip('已定位并替换相关片段，请按“改写片段”模板完成优化。')
    } else {
      setScriptEditTip(source === 'issue' ? '已将未通过项插入脚本编辑区，请按模板修改。' : '已将审核建议插入脚本编辑区，请按模板修改。')
    }
    jumpToScriptOutput()
    message.success(mode === 'replace' ? '已定位并替换到脚本编辑区' : '已插入到脚本编辑区')
  }

  const renderHumanOutput = (stepKey, output) => {
    if (!output) return null

    if (stepKey === 'script') {
      const segmentCount = Number(output.segments_count ?? 0)
      const showPreviewOnlyWarning = output.fallback || segmentCount <= 0
      return (
        <div className="human-output-wrap">
          <Card size="small" className="human-output-card" title="脚本结果概览">
            <Space wrap>
              <Tag color="blue">主题：{output.topic || '-'}</Tag>
              <Tag color={output.fallback ? 'warning' : 'success'}>
                {output.fallback ? '离线占位结果' : 'AI生成结果'}
              </Tag>
              <Tag color="purple">片段数：{output.segments_count ?? 0}</Tag>
            </Space>
          </Card>

          {showPreviewOnlyWarning ? (
            <Alert
              type="warning"
              showIcon
              message="当前结果仅供预览"
              description="片段数为 0 或使用了离线占位结果，暂不可用于自动分镜、自动配音与自动合成。请配置可用的 AI 服务后重新生成。"
            />
          ) : null}

          <Card size="small" className="human-output-card" title="脚本大纲">
            {needCollapse(output.outline) ? (
              <Collapse
                size="small"
                items={[
                  {
                    key: 'outline-preview',
                    label: '展开查看完整大纲（Markdown）',
                    children: (
                      <div className="human-output-markdown">
                        <ReactMarkdown>{output.outline || ''}</ReactMarkdown>
                      </div>
                    )
                  }
                ]}
              />
            ) : (
              <div className="human-output-markdown">
                <ReactMarkdown>{output.outline || ''}</ReactMarkdown>
              </div>
            )}
          </Card>

          <Card
            size="small"
            className="human-output-card"
            title="完整脚本"
            extra={
              <Space>
                <Button
                  size="small"
                  icon={<HistoryOutlined />}
                  onClick={() => {
                    loadScriptHistory()
                    setHistoryModalOpen(true)
                  }}
                >
                  历史版本
                </Button>
                {editingScript ? (
                  <>
                    <Button size="small" onClick={handleCancelEditScript}>取消</Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<SaveOutlined />}
                      loading={savingScript}
                      onClick={handleSaveScript}
                    >
                      保存
                    </Button>
                  </>
                ) : (
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleStartEditScript(output.full_script)}
                  >
                    编辑
                  </Button>
                )}
              </Space>
            }
          >
            {editingScript ? (
              <Space direction="vertical" size={10} style={{ width: '100%' }}>
                {scriptEditTip ? (
                  <Alert
                    type="info"
                    showIcon
                    message={scriptEditTip}
                  />
                ) : null}
                <Input.TextArea
                  value={scriptDraft}
                  onChange={(e) => setScriptDraft(e.target.value)}
                  autoSize={{ minRows: 8, maxRows: 18 }}
                  placeholder="请输入完整脚本文本"
                />
              </Space>
            ) : (
              renderMultilineText(output.full_script)
            )}
          </Card>
        </div>
      )
    }

    if (stepKey === 'review') {
      if (output.mode !== 'real_review') {
        return <Alert type="info" showIcon message={output.message || '审核结果暂不可用'} />
      }
      const issues = Array.isArray(output.issues) ? output.issues : []
      const recommendations = Array.isArray(output.recommendations) ? output.recommendations : []
      const visibleScoreChange = reviewScoreChange && Number.isFinite(Number(reviewScoreChange.afterScore))
        ? reviewScoreChange
        : null
      const trendData = reviewTrend.length
        ? reviewTrend
        : (Number.isFinite(Number(output.score))
          ? [{ score: Number(output.score), grade: output.grade || '-', delta: null, at: output.reviewed_at || new Date().toISOString() }]
          : [])
      const maxScore = trendData.length
        ? Math.max(...trendData.map((r) => Number(r.score) || 0), 1)
        : 1
      return (
        <div className="human-output-wrap">
          <Card
            size="small"
            className="human-output-card"
            title="审核结果概览"
            extra={(
              <Button
                size="small"
                type="primary"
                loading={aiRevisionLoading}
                onClick={() => handleAiReviseFromReview(output)}
              >
                让大模型自动修改
              </Button>
            )}
          >
            <Space wrap>
              <Tag color={output.passed ? 'success' : 'error'}>
                {output.passed ? '审核通过' : '审核未通过'}
              </Tag>
              <Tag color="blue">评分：{output.score ?? 0}</Tag>
              <Tag color="purple">等级：{output.grade || '-'}</Tag>
              <Tag color={issues.length ? 'warning' : 'success'}>问题数：{issues.length}</Tag>
            </Space>
            {visibleScoreChange ? (
              <Alert
                style={{ marginTop: 10 }}
                type={visibleScoreChange.delta !== null && visibleScoreChange.delta < 0 ? 'warning' : 'success'}
                showIcon
                message="采纳 AI 修订后自动复审结果"
                description={(
                  <Space wrap>
                    <Tag color="default">采纳前：{visibleScoreChange.beforeScore ?? '-'}（{visibleScoreChange.beforeGrade || '-'}）</Tag>
                    <Tag color="blue">采纳后：{visibleScoreChange.afterScore}（{visibleScoreChange.afterGrade || '-'}）</Tag>
                    {visibleScoreChange.delta !== null ? (
                      <Tag color={visibleScoreChange.delta >= 0 ? 'success' : 'error'}>
                        变化：{visibleScoreChange.delta >= 0 ? `+${visibleScoreChange.delta}` : visibleScoreChange.delta}
                      </Tag>
                    ) : null}
                    <Tag>{formatDateTime(visibleScoreChange.updatedAt)}</Tag>
                  </Space>
                )}
              />
            ) : null}
            {trendData.length ? (
              <div style={{ marginTop: 10 }}>
                <Paragraph strong style={{ marginBottom: 8 }}>评分趋势（最近 {trendData.length} 次）</Paragraph>
                <Space wrap size={8} style={{ marginBottom: 8 }}>
                  <Tag color="purple">最近：{trendData[trendData.length - 1]?.score}</Tag>
                  <Tag color="success">最佳：{Math.max(...trendData.map((r) => Number(r.score) || 0))}</Tag>
                  <Tag>{trendData[trendData.length - 1]?.grade || '-'}</Tag>
                </Space>
                <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', minHeight: 56 }}>
                  {trendData.map((item, idx) => {
                    const score = Number(item.score) || 0
                    const h = Math.max(12, Math.round((score / maxScore) * 44))
                    return (
                      <div
                        key={`trend-${idx}-${item.at}`}
                        title={`${formatDateTime(item.at)} | ${score}`}
                        style={{
                          width: 20,
                          height: h,
                          borderRadius: 6,
                          background: idx === trendData.length - 1 ? 'linear-gradient(180deg, #818cf8, #6366f1)' : 'linear-gradient(180deg, #c7d2fe, #a5b4fc)',
                          display: 'flex',
                          alignItems: 'flex-start',
                          justifyContent: 'center',
                          color: '#fff',
                          fontSize: 10,
                          lineHeight: '12px',
                          paddingTop: 2
                        }}
                      >
                        {score}
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </Card>
          <Card size="small" className="human-output-card" title="问题清单">
            {issues.length ? (
              <List
                size="small"
                dataSource={issues}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="apply-issue"
                        size="small"
                        onClick={() => insertReviewItemToScriptEditor({
                          issue: item,
                          recommendation: item?.message,
                          source: 'issue',
                          mode: 'append'
                        })}
                      >
                        一键插入到脚本编辑区
                      </Button>,
                      <Button
                        key="replace-issue"
                        size="small"
                        onClick={() => insertReviewItemToScriptEditor({
                          issue: item,
                          recommendation: item?.message,
                          source: 'issue',
                          mode: 'replace'
                        })}
                      >
                        定位并替换片段
                      </Button>
                    ]}
                  >
                    <Space wrap>
                      <Tag color={item.severity === 'high' ? 'error' : item.severity === 'medium' ? 'warning' : 'default'}>
                        {item.severity || 'medium'}
                      </Tag>
                      {item.type ? <Tag>{item.type}</Tag> : null}
                      <Typography.Text>{item.message || '-'}</Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>未发现明显问题</Paragraph>
            )}
          </Card>
          <Card size="small" className="human-output-card" title="修改建议">
            {recommendations.length ? (
              <List
                size="small"
                dataSource={recommendations}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="apply-rec"
                        size="small"
                        onClick={() => insertReviewItemToScriptEditor({
                          recommendation: item,
                          source: 'recommendation',
                          mode: 'append'
                        })}
                      >
                        一键插入到脚本编辑区
                      </Button>,
                      <Button
                        key="replace-rec"
                        size="small"
                        onClick={() => insertReviewItemToScriptEditor({
                          recommendation: item,
                          source: 'recommendation',
                          mode: 'replace'
                        })}
                      >
                        定位并替换片段
                      </Button>
                    ]}
                  >
                    <Typography.Text>{item}</Typography.Text>
                  </List.Item>
                )}
              />
            ) : (
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>暂无额外建议</Paragraph>
            )}
          </Card>
          {aiRevisionCandidate ? (
            <Card
              size="small"
              className="human-output-card"
              title="AI 修订候选稿（待你确认）"
              extra={(
                <Space>
                  <Button
                    size="small"
                    onClick={() => setAiRevisionCandidate(null)}
                  >
                    取消候选
                  </Button>
                  <Popconfirm
                    title="确认采纳 AI 修订稿？"
                    description={aiRevisionCandidate.baseVersion ? `将基于候选基线版本 v${aiRevisionCandidate.baseVersion} 保存。` : '将把候选稿写入当前完整脚本。'}
                    okText="确认采纳"
                    cancelText="取消"
                    onConfirm={() => handleApplyAiRevision(false)}
                  >
                    <Button
                      size="small"
                      type="primary"
                      loading={aiRevisionApplying}
                    >
                      确认采纳并保存
                    </Button>
                  </Popconfirm>
                </Space>
              )}
            >
              <Space wrap style={{ marginBottom: 10 }}>
                <Tag color="purple">差异行数：{aiRevisionCandidate.diffRows.length}</Tag>
                {aiRevisionCandidate.llmInput?.provider ? <Tag color="blue">模型：{aiRevisionCandidate.llmInput.provider}</Tag> : null}
                {aiRevisionCandidate.baseVersion ? <Tag color="geekblue">基线版本：v{aiRevisionCandidate.baseVersion}</Tag> : null}
                {aiRevisionCandidate.generatedAt ? <Tag>候选生成：{formatDateTime(aiRevisionCandidate.generatedAt)}</Tag> : null}
              </Space>
              {aiRevisionCandidate.stale ? (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginBottom: 10 }}
                  message="脚本版本已变化"
                  description={`候选基线版本 v${aiRevisionCandidate.baseVersion}，当前最新版本 v${aiRevisionCandidate.currentVersion}。建议重新生成候选稿，或谨慎强制覆盖。`}
                  action={(
                    <Button
                      size="small"
                      danger
                      loading={aiRevisionApplying}
                      onClick={() => handleApplyAiRevision(true)}
                    >
                      强制覆盖采纳
                    </Button>
                  )}
                />
              ) : null}
              {aiRevisionCandidate.diffRows.length ? (
                <Collapse
                  size="small"
                  items={[
                    {
                      key: 'ai-revise-diff',
                      label: '查看修改点（Diff）',
                      children: renderDiffRows(aiRevisionCandidate.diffRows)
                    }
                  ]}
                />
              ) : (
                <Alert type="info" showIcon message="AI 修订内容与原稿差异较小" />
              )}
              <Collapse
                size="small"
                style={{ marginTop: 10 }}
                items={[
                  {
                    key: 'ai-revise-content',
                    label: '查看修订后的完整脚本',
                    children: (
                      <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                        {aiRevisionCandidate.revised || ''}
                      </Paragraph>
                    )
                  },
                  {
                    key: 'ai-revise-prompt',
                    label: '查看发送给大模型的修订输入',
                    children: (
                      <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: 0, whiteSpace: 'pre-wrap' }}>
                        {aiRevisionCandidate.llmInput?.prompt || ''}
                      </pre>
                    )
                  }
                ]}
              />
            </Card>
          ) : null}
        </div>
      )
    }

    if (output.message) {
      return <Alert type="info" showIcon message={output.message} />
    }

    return <Paragraph type="secondary">步骤已完成</Paragraph>
  }

  const formatDateTime = (value) => {
    if (!value) return '-'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return value
    return d.toLocaleString('zh-CN', { hour12: false })
  }

  const sourceLabelMap = {
    manual_edit: '手动编辑',
    llm_generate: '模型生成',
    fallback_generate: '离线占位生成'
  }

  const getSourceLabel = (source) => {
    if (!source) return '未知来源'
    if (source.startsWith('rollback_to_v')) {
      const version = source.replace('rollback_to_v', '')
      return `版本回滚（回滚至 v${version}）`
    }
    return sourceLabelMap[source] || source
  }

  const scrollToScriptSection = (sectionKey) => {
    if (sectionKey === 'history') {
      setActiveAnchor(sectionKey)
      loadScriptHistory()
      setHistoryModalOpen(true)
      return
    }
    setActiveAnchor(sectionKey)
    const node = document.getElementById(`script-section-${sectionKey}`)
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const scriptStepData = project?.steps?.script || project?.metadata?.steps?.script
  const showScriptAnchors = !!scriptStepData
  const scriptStatus = scriptStepData?.status
  const insightIndicatorClass = scriptStatus === 'failed'
    ? 'error'
    : scriptStatus === 'processing'
      ? 'processing'
      : scriptStatus === 'completed'
        ? 'success'
        : 'default'
  const outputReady = !!(scriptStepData?.output?.full_script || scriptStepData?.output?.outline)
  const outputIndicatorClass = outputReady ? 'success' : 'default'

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!project) {
    return <div>项目不存在</div>
  }

  return (
    <div className={`workflow-page ${compactMode ? 'compact-workflow' : ''}`}>
      <Title level={2} style={{ marginBottom: 12 }}>{project.title}</Title>
      <Card
        className="glass-card hover-tilt"
        style={{ marginBottom: 16 }}
      >
        <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
          <div>
            <Paragraph style={{ marginBottom: 4 }}>
              <strong>总体进度：</strong>
              <AnimatedNumber value={completedCount} />/<AnimatedNumber value={workflowSteps.length} /> 步
            </Paragraph>
            <Tag color={overallPercent === 100 ? 'success' : 'processing'}>
              {overallPercent === 100 ? '流程完成' : '进行中'}
            </Tag>
          </div>
          <div style={{ minWidth: 260 }}>
            <Progress
              percent={overallPercent}
              format={() => <AnimatedNumber value={overallPercent} suffix="%" />}
              status={overallPercent === 100 ? 'success' : 'active'}
            />
            <Space style={{ marginTop: 8 }}>
              <Tag color={compactMode ? 'blue' : 'default'} style={{ marginInlineEnd: 0 }}>
                {compactMode ? '紧凑模式' : '详细模式'}
              </Tag>
              <Switch
                checked={compactMode}
                onChange={setCompactMode}
                checkedChildren="紧凑"
                unCheckedChildren="详细"
              />
            </Space>
          </div>
        </Space>
      </Card>
      <Divider />

      <Steps current={currentStep} style={{ marginBottom: '24px' }} className="workflow-steps">
        {workflowSteps.map((step, index) => (
          <Steps.Step
            key={step.key}
            title={step.title}
            status={getStepStatus(step.key)}
            icon={
              getStepStatus(step.key) === 'finish' ? <CheckCircleOutlined /> :
              getStepStatus(step.key) === 'process' ? <PlayCircleOutlined /> :
              getStepStatus(step.key) === 'error' ? <CloseCircleOutlined /> :
              <ClockCircleOutlined />
            }
          />
        ))}
      </Steps>

      {showScriptAnchors ? (
        <Card className="glass-card workflow-anchor-nav" size="small" style={{ marginBottom: 14 }}>
          <Space wrap size={8}>
            <Tag color="blue" style={{ marginInlineEnd: 4 }}>快速跳转</Tag>
            <Button
              size="small"
              type={activeAnchor === 'insight' ? 'primary' : 'default'}
              onClick={() => scrollToScriptSection('insight')}
            >
              <span className="anchor-btn-inner">
                执行洞察
                <span className={`anchor-indicator ${insightIndicatorClass}`} />
              </span>
            </Button>
            <Button
              size="small"
              type={activeAnchor === 'output' ? 'primary' : 'default'}
              onClick={() => scrollToScriptSection('output')}
            >
              <span className="anchor-btn-inner">
                脚本输出
                <span className={`anchor-indicator ${outputIndicatorClass}`} />
              </span>
            </Button>
            <Button
              size="small"
              type={activeAnchor === 'history' ? 'primary' : 'default'}
              onClick={() => scrollToScriptSection('history')}
            >
              <span className="anchor-btn-inner">
                历史版本
                <Badge size="small" count={scriptHistory.length} />
              </span>
            </Button>
          </Space>
        </Card>
      ) : null}

      {workflowSteps.map((step, index) => (
        (() => {
          const stepData = project?.steps?.[step.key] || project?.metadata?.steps?.[step.key]
          const statusMeta = getStatusMeta(step.key)
          const inFlight = runningStepKey === step.key || stepData?.status === 'processing'
          const progressText = stepData?.progress?.message || (inFlight ? '处理中...' : '')
          const progressMeta = stepData?.progress || {}
          const stageLabel = getStageLabel(progressMeta.stage)
          const totalSeconds = toIntSeconds(progressMeta.total_duration_sec)
          const currentStageSeconds = getElapsedSeconds(
            progressMeta.timeline?.length ? progressMeta.timeline[progressMeta.timeline.length - 1]?.entered_at : null,
            progressMeta.timeline?.length ? progressMeta.timeline[progressMeta.timeline.length - 1]?.exited_at : null
          )
          const etaSeconds = getEtaSeconds(progressMeta)
          const stageTimeline = Array.isArray(progressMeta.timeline) ? progressMeta.timeline : []
          const llmCalls = Array.isArray(progressMeta.llm_calls) ? progressMeta.llm_calls : []
          const llmCallByStage = llmCalls.reduce((acc, item) => {
            if (item?.stage) acc[item.stage] = item
            return acc
          }, {})
          const llmInputItems = []
          const outputLlmInput = stepData?.output?.llm_input || {}
          const hasOutlineInput = llmCalls.some((call) => call?.stage === 'outline_generating' && call?.input)
          const hasFullScriptInput = llmCalls.some((call) => call?.stage === 'script_generating' && call?.input)
          llmCalls.forEach((call, idx) => {
            llmInputItems.push({
              key: `${call.stage || 'llm'}-${idx}`,
              stage: call.stage,
              input: call.input || '',
              duration_sec: call.duration_sec,
              success: call.success,
              provider: call.provider,
              error: call.error
            })
          })
          if (!hasOutlineInput && outputLlmInput.outline_prompt) {
            llmInputItems.push({
              key: 'outline-fallback',
              stage: 'outline_generating',
              input: outputLlmInput.outline_prompt,
              source: 'legacy_fallback'
            })
          }
          if (!hasFullScriptInput && outputLlmInput.full_script_prompt) {
            llmInputItems.push({
              key: 'full-script-fallback',
              stage: 'script_generating',
              input: outputLlmInput.full_script_prompt,
              source: 'legacy_fallback'
            })
          }
          const llmSuccessCount = llmInputItems.filter((item) => item.success !== false).length
          const llmFailCount = llmInputItems.filter((item) => item.success === false).length
          const llmTotalSeconds = llmInputItems.reduce((sum, item) => {
            const sec = Number(item.duration_sec)
            return sum + (Number.isFinite(sec) ? sec : 0)
          }, 0)
          const failedHighlight = lastFailedStepKey === step.key
          const failureReason = progressMeta.message || stepData?.output?.error || stepData?.output?.reason
          const hasAnyRunning = !!runningStepKey || workflowSteps.some((s) => {
            const d = project?.steps?.[s.key] || project?.metadata?.steps?.[s.key]
            return d?.status === 'processing'
          })
          return (
            <Card
              key={step.key}
              id={`step-card-${step.key}`}
              className="workflow-step-card hover-tilt stagger-fade-in premium-step-card"
              title={`${index + 1}. ${step.title}`}
              style={{
                marginBottom: '16px',
                background: statusMeta.cardColor,
                borderColor: failedHighlight ? '#ff4d4f' : statusMeta.borderColor,
                boxShadow: failedHighlight ? '0 0 0 2px rgba(255, 77, 79, 0.22)' : undefined,
                animationDelay: `${Math.min(0.07 * (index + 1), 0.45)}s`
              }}
              extra={
                <Space>
                  <Tag color={statusMeta.tagColor}>{statusMeta.text}</Tag>
                  <Button
                    type="primary"
                    onClick={() => handleExecuteStep(step.key)}
                    disabled={getStepStatus(step.key) === 'finish' || hasAnyRunning}
                    loading={inFlight}
                  >
                    执行
                  </Button>
                  <Button
                    onClick={() => handleRegenerateStep(step.key)}
                    disabled={getStepStatus(step.key) === 'wait' || hasAnyRunning}
                    loading={inFlight}
                  >
                    重新生成
                  </Button>
                </Space>
              }
            >
              <Progress
                percent={statusMeta.progress}
                size="small"
                status={statusMeta.progress === 100 ? 'success' : statusMeta.progress > 0 ? 'active' : 'normal'}
                showInfo={false}
                style={{ marginBottom: 12 }}
                className="step-progress-bar"
              />
              {inFlight ? (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message={`${stageLabel} · ${progressText}`}
                  description={`当前阶段耗时 ${currentStageSeconds ?? 0}s ｜ 总耗时 ${totalSeconds ?? 0}s ｜ 预计剩余 ${etaSeconds ?? '-'}s（自动刷新）`}
                />
              ) : null}
              {failedHighlight && !inFlight ? (
                <Alert
                  type="error"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message="该步骤最近一次执行失败"
                  description={failureReason || '已自动定位并高亮，请检查模型配置、网络或输入后重试。'}
                />
              ) : null}
              {stepData ? (
                <div>
                  <Paragraph className="step-status-line">
                    <strong>状态：</strong>
                    <Tag color={statusMeta.tagColor}>{stepData.status}</Tag>
                    {progressMeta.stage ? <Tag color="blue">阶段：{stageLabel}</Tag> : null}
                    {totalSeconds !== null ? <Tag color="geekblue">总耗时：{totalSeconds}s</Tag> : null}
                    {inFlight && etaSeconds !== null ? <Tag color="cyan">预计剩余：{etaSeconds}s</Tag> : null}
                  </Paragraph>
                  <div
                    id={step.key === 'script' ? 'script-section-insight' : undefined}
                    className="step-section-title"
                  >
                    执行洞察
                  </div>
                  {stepData.status === 'failed' ? (
                    <Alert
                      type="error"
                      showIcon
                      style={{ marginBottom: 12 }}
                      message="步骤执行失败"
                      description={failureReason || '未返回具体失败原因，请查看后端日志。'}
                    />
                  ) : null}
                  {stageTimeline.length ? (
                    <Collapse
                      className="step-collapse-panel"
                      size="small"
                      style={{ marginBottom: 12 }}
                      items={[
                        {
                          key: `timeline-${step.key}`,
                          label: `阶段耗时明细（${stageTimeline.length}）`,
                          children: (
                            <List
                              size="small"
                              dataSource={stageTimeline}
                              renderItem={(item, idx) => {
                                const sec = toIntSeconds(item.duration_sec) ?? getElapsedSeconds(item.entered_at, item.exited_at) ?? 0
                                const llmCall = llmCallByStage[item.stage]
                                const llmSec = toIntSeconds(llmCall?.duration_sec)
                                return (
                                  <List.Item>
                                    <Space wrap>
                                      <Tag color={idx === stageTimeline.length - 1 && !item.exited_at ? 'processing' : 'default'}>
                                        {getStageLabel(item.stage)}
                                      </Tag>
                                      {llmCall ? (
                                        <Tag color={llmCall.success === false ? 'error' : 'cyan'}>
                                          模型调用
                                        </Tag>
                                      ) : null}
                                      <Typography.Text type="secondary">{formatDateTime(item.entered_at)}</Typography.Text>
                                      <Typography.Text type="secondary">→</Typography.Text>
                                      <Typography.Text type="secondary">{item.exited_at ? formatDateTime(item.exited_at) : '进行中'}</Typography.Text>
                                      <Tag color="purple">阶段耗时 {sec}s</Tag>
                                      {llmCall ? (
                                        <Tag color={llmCall.success === false ? 'error' : 'geekblue'}>
                                          模型耗时 {llmSec ?? 0}s
                                        </Tag>
                                      ) : null}
                                    </Space>
                                  </List.Item>
                                )
                              }}
                            />
                          )
                        }
                      ]}
                    />
                  ) : null}
                  {llmInputItems.length ? (
                    <Collapse
                      className="step-collapse-panel"
                      size="small"
                      style={{ marginBottom: 12 }}
                      items={[
                        {
                          key: `llm-inputs-${step.key}`,
                          label: (
                            <Space wrap size={8} style={{ width: '100%', justifyContent: 'space-between' }}>
                              <span>大模型输入与调用明细（{llmInputItems.length}）</span>
                              {step.key === 'script' ? (
                                <Button
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    setPromptEditorVisible(true)
                                  }}
                                >
                                  Prompt编辑
                                </Button>
                              ) : null}
                            </Space>
                          ),
                          children: (
                            <Space direction="vertical" size={12} style={{ width: '100%' }}>
                              <div className="llm-summary-strip">
                                <Tag color="blue">阶段数：{llmInputItems.length}</Tag>
                                <Tag color="success">成功：{llmSuccessCount}</Tag>
                                <Tag color={llmFailCount > 0 ? 'error' : 'default'}>失败：{llmFailCount}</Tag>
                                <Tag color="purple">模型总耗时：{Math.round(llmTotalSeconds)}s</Tag>
                              </div>
                              <List
                                size="small"
                                dataSource={llmInputItems}
                                renderItem={(call) => (
                                  <List.Item key={call.key} className="llm-stage-item">
                                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                                      <Space wrap>
                                        <Tag color="blue">{getStageLabel(call.stage)}</Tag>
                                        {call.duration_sec !== undefined ? (
                                          <Tag color="geekblue">模型耗时 {toIntSeconds(call.duration_sec) ?? 0}s</Tag>
                                        ) : null}
                                        {call.success !== undefined ? (
                                          <Tag color={call.success === false ? 'error' : 'success'}>
                                            {call.success === false ? '调用失败' : '调用成功'}
                                          </Tag>
                                        ) : null}
                                        {call.provider ? <Tag>{call.provider}</Tag> : null}
                                        {call.source === 'legacy_fallback' ? <Tag color="default">历史兼容输入</Tag> : null}
                                      </Space>
                                      {call.error ? <Alert type="error" showIcon message={call.error} /> : null}
                                      <div className="llm-input-preview">
                                        <Paragraph
                                          style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
                                          ellipsis={{ rows: compactMode ? 2 : 4, expandable: true, symbol: '展开输入详情' }}
                                        >
                                          {call.input || '该阶段无输入内容'}
                                        </Paragraph>
                                      </div>
                                    </Space>
                                  </List.Item>
                                )}
                              />
                            </Space>
                          )
                        }
                      ]}
                    />
                  ) : null}
                  {stepData.output && (
                    <div
                      id={step.key === 'script' ? 'script-section-output' : undefined}
                      className="step-output-zone"
                    >
                      <strong>输出：</strong>
                      {step.key === 'script' && stepData.output?.fallback ? (
                        <Alert
                          type="warning"
                          showIcon
                          style={{ marginBottom: '12px' }}
                          message="当前为离线占位结果"
                          description="未成功调用 AI 服务（如 API Key 无效或网络异常），系统返回了开发占位脚本，仅用于流程联调。"
                        />
                      ) : null}

                      {renderHumanOutput(step.key, stepData.output)}

                      {!compactMode ? (
                        <Collapse
                          className="step-collapse-panel"
                          size="small"
                          style={{ marginTop: 12 }}
                          items={[
                            {
                              key: 'raw',
                              label: '原始结果（隐藏标签 / 调试）',
                              children: (
                                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: 0 }}>
                                  {JSON.stringify(stepData.output, null, 2)}
                                </pre>
                              )
                            }
                          ]}
                        />
                      ) : null}
                    </div>
                  )}
                </div>
              ) : (
                <Paragraph type="secondary">等待执行</Paragraph>
              )}

            </Card>
          )
        })()
      ))}

      <Modal
        title={`历史版本差异：${diffModal.title}`}
        open={diffModal.open}
        onCancel={() => setDiffModal({ open: false, title: '', outlineDiff: [], fullScriptDiff: [] })}
        footer={null}
        width={920}
      >
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Card size="small" title="大纲修改点">
            {renderDiffRows(diffModal.outlineDiff)}
          </Card>
          <Card size="small" title="完整脚本修改点">
            {renderDiffRows(diffModal.fullScriptDiff)}
          </Card>
        </Space>
      </Modal>

      <Modal
        title={`历史版本（${scriptHistory.length}）`}
        open={historyModalOpen}
        onCancel={() => setHistoryModalOpen(false)}
        footer={null}
        width={920}
      >
        <Space wrap size={8} style={{ width: '100%', justifyContent: 'space-between', marginBottom: 10 }}>
          <Tag color="blue">仅保留最近 10 条</Tag>
          <Popconfirm
            title="确认清空当前项目的全部历史版本？"
            description="清空后不可恢复"
            okText="确认清空"
            cancelText="取消"
            onConfirm={handleClearHistory}
            disabled={!scriptHistory.length}
          >
            <Button
              size="small"
              danger
              loading={clearingHistory}
              disabled={!scriptHistory.length}
            >
              清空历史
            </Button>
          </Popconfirm>
        </Space>
        <List
          loading={loadingHistory}
          dataSource={scriptHistory}
          locale={{ emptyText: '暂无历史版本' }}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  key="diff"
                  size="small"
                  icon={<DiffOutlined />}
                  onClick={() => openHistoryDiff(item, scriptHistory.findIndex((h) => h.id === item.id))}
                >
                  查看修改点
                </Button>,
                <Popconfirm
                  key="rollback"
                  title="确认回滚到这个版本？"
                  okText="回滚"
                  cancelText="取消"
                  onConfirm={() => handleRollback(item.id)}
                >
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    loading={rollingBackId === item.id}
                  >
                    回滚
                  </Button>
                </Popconfirm>,
                <Popconfirm
                  key="delete"
                  title="确认删除该历史版本？"
                  description="删除后不可恢复"
                  okText="删除"
                  cancelText="取消"
                  onConfirm={() => handleDeleteHistory(item.id)}
                >
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    loading={deletingHistoryId === item.id}
                  >
                    删除
                  </Button>
                </Popconfirm>
              ]}
            >
              <List.Item.Meta
                avatar={<HistoryOutlined style={{ color: '#6D5EF5' }} />}
                title={`版本 v${item.version} · ${getSourceLabel(item.source)}`}
                description={formatDateTime(item.created_at)}
              />
            </List.Item>
          )}
        />
      </Modal>

      <Drawer
        title="Prompt编辑"
        open={promptEditorVisible}
        onClose={() => setPromptEditorVisible(false)}
        width={820}
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <Paragraph strong style={{ marginBottom: 6 }}>大纲 Prompt</Paragraph>
            <Input.TextArea
              value={outlinePromptDraft}
              onChange={(e) => {
                setPromptDirty(true)
                setOutlinePromptDraft(e.target.value)
              }}
              style={{ minHeight: 160, resize: 'vertical' }}
              placeholder="不填则使用系统默认大纲 Prompt"
            />
          </div>
          <div>
            <Paragraph strong style={{ marginBottom: 6 }}>完整脚本 Prompt</Paragraph>
            <Input.TextArea
              value={fullScriptPromptDraft}
              onChange={(e) => {
                setPromptDirty(true)
                setFullScriptPromptDraft(e.target.value)
              }}
              style={{ minHeight: 280, resize: 'vertical' }}
              placeholder="不填则使用系统默认完整脚本 Prompt（支持 {{OUTLINE}} 占位符）"
            />
          </div>
          <Space>
            <Button
              size="small"
              onClick={() => {
                setPromptDirty(false)
                setOutlinePromptDraft(scriptStepData?.output?.llm_input?.outline_prompt || '')
                setFullScriptPromptDraft(scriptStepData?.output?.llm_input?.full_script_prompt || '')
              }}
            >
              重置为最近一次生成输入
            </Button>
            <Button
              size="small"
              onClick={() => {
                setPromptDirty(false)
                setOutlinePromptDraft('')
                setFullScriptPromptDraft('')
              }}
            >
              清空并使用系统默认
            </Button>
          </Space>
        </Space>
      </Drawer>
    </div>
  )
}

export default ProjectWorkflow
