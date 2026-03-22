import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Steps, Card, Button, message, Spin, Typography, Divider, Space, Tag, Alert, Progress, Collapse, Input, List, Popconfirm, Modal, Switch, Badge, Drawer, Tooltip } from 'antd'
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
  DeleteOutlined,
  InfoCircleOutlined
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
import { LtxShotBoardPanel } from '../components/LtxShotBoardPanel'
import ReactMarkdown from 'react-markdown'
import { FinalVideoPreviewPlugin, VideoPipelineEnvPlugin, VideoGenerationMonitorPlugin } from '../plugins/workflow'

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
  visual_loading: '读取脚本',
  visual_planning: '生成视觉规划',
  visual_structuring: '整理分镜结果',
  audio_loading: '读取脚本',
  audio_synthesizing: '生成配音音频',
  audio_persisting: '保存音频结果',
  video_loading: '读取素材',
  video_shot_timeline: '分镜时间轴（LTX / 裁切素材）',
  video_synthesizing: '合成视频',
  video_audio_mix: '挂载音频轨道',
  video_persisting: '保存视频结果',
  persisting: '保存结果',
  fallback_generating: '离线占位生成',
  running: '执行中',
  completed: '已完成',
  failed: '执行失败'
}

const viralDimensionMeta = {
  hook: { label: '开场钩子', max: 20 },
  value_density: { label: '价值密度', max: 20 },
  narrative_progression: { label: '叙事推进', max: 15 },
  emotional_rhythm: { label: '情绪节奏', max: 15 },
  credibility: { label: '可信合规', max: 15 },
  cta_interaction: { label: '互动转化', max: 15 }
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
  /** 快速跳转栏：最近点击的流程步骤（用于按钮高亮） */
  const [quickJumpFocus, setQuickJumpFocus] = useState(null)
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
  /** 执行中每秒触发重渲染，用于本步已运行时长（与轮询无关的本地时钟） */
  const [progressClock, setProgressClock] = useState(0)
  useEffect(() => {
    if (!runningStepKey) return undefined
    const t = window.setInterval(() => setProgressClock((c) => c + 1), 1000)
    return () => window.clearInterval(t)
  }, [runningStepKey])

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
    const pollMs = stepName === 'video' ? 750 : 1200
    while (Date.now() - start < timeoutMs) {
      const data = await loadProject(true)
      const current = data?.steps?.[stepName] || data?.metadata?.steps?.[stepName]
      if (current?.status && current.status !== 'processing') return current
      await sleep(pollMs)
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
    const pollMs = stepName === 'video' ? 750 : 1200
    refreshTimerRef.current = setInterval(() => {
      loadProject(true)
    }, pollMs)

    const messageKey = mode === 'execute' ? 'execute' : 'regenerate'
    const loadingText = mode === 'execute' ? '执行中...' : '重新生成中...'
    const successText = mode === 'execute' ? '执行成功' : '重新生成成功'
    const failText = mode === 'execute' ? '执行失败' : '重新生成失败'
    let handedOffToBackgroundSync = false

    const startBackgroundSyncUntilSettled = () => {
      handedOffToBackgroundSync = true
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
      const startedAt = Date.now()
      const bgPollMs = stepName === 'video' ? 750 : 1200
      let longVideoWarned = false
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
        if (stepName === 'video') {
          if (Date.now() - startedAt > 300000 && !longVideoWarned) {
            longVideoWarned = true
            message.warning({
              content: '视频步骤仍在执行（LTX 侧车 / Comfy 或 MoviePy 编码可能需较长时间），页面会持续自动刷新进度',
              key: `${messageKey}-longvideo`,
              duration: 8
            })
          }
          return
        }
        if (Date.now() - startedAt > 180000) {
          clearInterval(refreshTimerRef.current)
          refreshTimerRef.current = null
          setRunningStepKey('')
          message.warning({ content: '后台处理时间较长，请稍后刷新查看最终状态', key: messageKey })
        }
      }, bgPollMs)
    }

    try {
      message.loading({ content: loadingText, key: messageKey })
      const payload = {}
      if (stepName === 'script') {
        if (outlinePromptDraft?.trim()) payload.outline_prompt = outlinePromptDraft.trim()
        if (fullScriptPromptDraft?.trim()) payload.full_script_prompt = fullScriptPromptDraft.trim()
      }

      const longVideo = stepName === 'video' ? { timeout: 7200000 } : {}
      if (mode === 'execute') {
        await executeStep(id, stepName, stepName === 'script' ? payload : undefined, longVideo)
      } else {
        await regenerateStep(id, stepName, stepName === 'script' ? payload : undefined, longVideo)
      }
      setLastFailedStepKey((prev) => (prev === stepName ? '' : prev))
      const settled = await waitForStepSettled(stepName, stepName === 'video' ? 120000 : 30000)
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
      const settled = await waitForStepSettled(stepName, stepName === 'video' ? 300000 : 180000)
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

  const scrollToWorkflowStep = (stepKey) => {
    setQuickJumpFocus(stepKey)
    setActiveAnchor('')
    const node = document.getElementById(`step-card-${stepKey}`)
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const quickJumpStepDotClass = (stepKey) => {
    const st = getStepStatus(stepKey)
    if (st === 'error') return 'error'
    if (st === 'process') return 'processing'
    if (st === 'finish') return 'success'
    return 'default'
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
      const viralReview = output.metrics?.viral_template_review || {}
      const viralDimensionsRaw = Array.isArray(viralReview.dimensions) ? viralReview.dimensions : []
      const viralDimensions = viralDimensionsRaw.map((item) => {
        const key = item?.key || ''
        const meta = viralDimensionMeta[key] || { label: key || '未命名维度', max: 20 }
        const score = Number(item?.score) || 0
        return {
          key,
          label: meta.label,
          max: meta.max,
          score: Math.max(0, Math.min(meta.max, score)),
          reason: item?.reason || ''
        }
      })
      const getRadarPoint = (index, ratio, cx = 140, cy = 140, r = 100) => {
        const angle = (-Math.PI / 2) + ((Math.PI * 2 * index) / Math.max(viralDimensions.length, 1))
        const x = cx + Math.cos(angle) * r * ratio
        const y = cy + Math.sin(angle) * r * ratio
        return `${x.toFixed(2)},${y.toFixed(2)}`
      }
      const radarPolygonPoints = viralDimensions
        .map((d, idx) => getRadarPoint(idx, d.max > 0 ? d.score / d.max : 0))
        .join(' ')
      const radarAxisPoints = viralDimensions
        .map((_, idx) => getRadarPoint(idx, 1))
      const scriptStep = project?.steps?.script || project?.metadata?.steps?.script
      const reviewLlmInput = viralReview?.llm_input || {}
      const allReviewPrompts = [
        { key: 'outline', title: '脚本生成大纲 Prompt', text: scriptStep?.output?.llm_input?.outline_prompt || '' },
        { key: 'full-script', title: '脚本生成完整脚本 Prompt', text: scriptStep?.output?.llm_input?.full_script_prompt || '' },
        { key: 'review-instruction', title: '评审指令 Prompt（完整版）', text: reviewLlmInput?.review_instruction_prompt || reviewLlmInput?.prompt || '' }
      ].filter((item) => String(item.text || '').trim())
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
              <Tag color="blue">评分：{formatScore(output.score)}</Tag>
              <Tag color="purple">等级：{output.grade || '-'}</Tag>
              <Tag color={issues.length ? 'warning' : 'success'}>问题数：{issues.length}</Tag>
              {output.metrics?.scoring_mode ? <Tag color="cyan">模式：{output.metrics.scoring_mode}</Tag> : null}
              {Number.isFinite(Number(output.metrics?.llm_score_100)) ? (
                <Tag color="geekblue">LLM评分：{formatScore(output.metrics?.llm_score_100)}</Tag>
              ) : null}
              {Number.isFinite(Number(output.metrics?.rule_score_100)) ? (
                <Tag color="purple">规则评分：{formatScore(output.metrics?.rule_score_100)}</Tag>
              ) : null}
            </Space>
            {viralDimensions.length ? (
              <Card size="small" style={{ marginTop: 10 }} title="爆款模板六维评审（雷达/条形图）">
                {viralReview.summary ? (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 10 }}
                    message="模型评审结论"
                    description={viralReview.summary}
                  />
                ) : null}
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  <svg width="300" height="300" viewBox="0 0 280 280" style={{ background: '#fafafa', borderRadius: 8 }}>
                    <circle cx="140" cy="140" r="100" fill="none" stroke="#e5e7eb" />
                    <circle cx="140" cy="140" r="75" fill="none" stroke="#e5e7eb" />
                    <circle cx="140" cy="140" r="50" fill="none" stroke="#e5e7eb" />
                    <circle cx="140" cy="140" r="25" fill="none" stroke="#e5e7eb" />
                    {radarAxisPoints.map((point, idx) => (
                      <line key={`axis-${idx}`} x1="140" y1="140" x2={point.split(',')[0]} y2={point.split(',')[1]} stroke="#d1d5db" />
                    ))}
                    {viralDimensions.map((d, idx) => {
                      const p = radarAxisPoints[idx].split(',')
                      return (
                        <text
                          key={`label-${d.key}-${idx}`}
                          x={Number(p[0])}
                          y={Number(p[1])}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize="10"
                          fill="#475569"
                        >
                          {d.label}
                        </text>
                      )
                    })}
                    <polygon points={radarPolygonPoints} fill="rgba(99,102,241,0.28)" stroke="#6366f1" strokeWidth="2" />
                  </svg>
                  <div style={{ flex: 1, minWidth: 280 }}>
                    <List
                      size="small"
                      dataSource={viralDimensions}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
                              <Typography.Text strong>{item.label}</Typography.Text>
                              <Tag color="blue">{formatScore(item.score)} / {item.max}</Tag>
                            </Space>
                            <Progress
                              percent={Math.round((item.score / Math.max(item.max, 1)) * 100)}
                              size="small"
                              showInfo={false}
                            />
                            {item.reason ? <Typography.Text type="secondary">{item.reason}</Typography.Text> : null}
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>
                </div>
              </Card>
            ) : null}
            <Collapse
              size="small"
              style={{ marginTop: 10 }}
              items={[
                {
                  key: 'review-llm-prompts',
                  label: `大模型评审输入内容（含全部 Prompt，${allReviewPrompts.length}项）`,
                  children: allReviewPrompts.length ? (
                    <Space direction="vertical" size={10} style={{ width: '100%' }}>
                      {reviewLlmInput?.provider ? (
                        <Space wrap>
                          <Tag color="blue">评审模型提供商：{reviewLlmInput.provider}</Tag>
                          {reviewLlmInput?.model ? <Tag color="purple">评审模型：{reviewLlmInput.model}</Tag> : null}
                        </Space>
                      ) : null}
                      {allReviewPrompts.map((item) => (
                        <Card key={item.key} size="small" title={item.title}>
                          <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: 4, margin: 0, whiteSpace: 'pre-wrap' }}>
                            {item.text}
                          </pre>
                        </Card>
                      ))}
                    </Space>
                  ) : (
                    <Alert type="info" showIcon message="暂无可展示的 Prompt 输入（可能是规则回退模式）" />
                  )
                }
              ]}
            />
            {visibleScoreChange ? (
              <Alert
                style={{ marginTop: 10 }}
                type={visibleScoreChange.delta !== null && visibleScoreChange.delta < 0 ? 'warning' : 'success'}
                showIcon
                message="采纳 AI 修订后自动复审结果"
                description={(
                  <Space wrap>
                    <Tag color="default">采纳前：{formatScore(visibleScoreChange.beforeScore)}（{visibleScoreChange.beforeGrade || '-'}）</Tag>
                    <Tag color="blue">采纳后：{formatScore(visibleScoreChange.afterScore)}（{visibleScoreChange.afterGrade || '-'}）</Tag>
                    {visibleScoreChange.delta !== null ? (
                      <Tag color={visibleScoreChange.delta >= 0 ? 'success' : 'error'}>
                        变化：{visibleScoreChange.delta >= 0 ? `+${formatScore(visibleScoreChange.delta)}` : formatScore(visibleScoreChange.delta)}
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
                  <Tag color="purple">最近：{formatScore(trendData[trendData.length - 1]?.score)}</Tag>
                  <Tag color="success">最佳：{formatScore(Math.max(...trendData.map((r) => Number(r.score) || 0)))}</Tag>
                  <Tag>{trendData[trendData.length - 1]?.grade || '-'}</Tag>
                </Space>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', minHeight: 74 }}>
                  {trendData.map((item, idx) => {
                    const score = Number(item.score) || 0
                    const h = Math.max(12, Math.round((score / maxScore) * 44))
                    return (
                      <div key={`trend-${idx}-${item.at}`} title={`${formatDateTime(item.at)} | ${formatScore(score)}`}>
                        <Typography.Text
                          style={{
                            display: 'block',
                            width: 38,
                            textAlign: 'center',
                            fontSize: 10,
                            color: '#64748b',
                            lineHeight: '12px',
                            marginBottom: 2
                          }}
                        >
                          {formatScore(score)}
                        </Typography.Text>
                        <div
                          style={{
                            width: 38,
                            height: h,
                            borderRadius: 6,
                            background: idx === trendData.length - 1 ? 'linear-gradient(180deg, #818cf8, #6366f1)' : 'linear-gradient(180deg, #c7d2fe, #a5b4fc)'
                          }}
                        />
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
              <Collapse
                size="small"
                style={{ marginBottom: 10 }}
                items={[
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
                  }
                ]}
              />
            </Card>
          ) : null}
        </div>
      )
    }

    if (stepKey === 'visual') {
      const shots = Array.isArray(output.shots) ? output.shots : []
      return (
        <div className="human-output-wrap">
          <Card size="small" className="human-output-card" title="视觉规划概览">
            <Space wrap>
              <Tag color="blue">模式：{output.mode || '-'}</Tag>
              {output.style_direction ? <Tag color="purple">风格：{output.style_direction}</Tag> : null}
              {output.target_duration_sec ? <Tag color="geekblue">目标时长：{output.target_duration_sec}s</Tag> : null}
              <Tag color={shots.length ? 'success' : 'warning'}>镜头数：{shots.length}</Tag>
            </Space>
            {output.summary ? (
              <Paragraph style={{ marginTop: 10, marginBottom: 0 }}>{output.summary}</Paragraph>
            ) : null}
          </Card>
          <Card size="small" className="human-output-card" title="镜头规划">
            {shots.length ? (
              <Collapse
                size="small"
                items={shots.map((item, idx) => ({
                  key: `shot-${item.shot_no ?? idx}`,
                  label: (
                    <Space wrap>
                      <Tag color="blue">镜头 {item.shot_no ?? idx + 1}</Tag>
                      <Tag color="purple">{item.duration_sec ?? '-'}s</Tag>
                      {item.transition ? <Tag>{item.transition}</Tag> : null}
                    </Space>
                  ),
                  children: (
                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                      {item.objective ? <Typography.Text strong>{item.objective}</Typography.Text> : null}
                      {item.visual_description ? <Typography.Text>{item.visual_description}</Typography.Text> : null}
                      {item.camera_language ? <Typography.Text type="secondary">机位/运镜：{item.camera_language}</Typography.Text> : null}
                      {item.on_screen_text ? <Typography.Text type="secondary">字幕：{item.on_screen_text}</Typography.Text> : null}
                      {item.music_sfx ? <Typography.Text type="secondary">音乐音效：{item.music_sfx}</Typography.Text> : null}
                      {Array.isArray(item.material_suggestion) && item.material_suggestion.length ? (
                        <Space wrap>
                          {item.material_suggestion.map((m, i) => (
                            <Tag key={`${item.shot_no || 'shot'}-mat-${i}`}>{m}</Tag>
                          ))}
                        </Space>
                      ) : null}
                      {item.risk_note ? <Alert type="warning" showIcon message={item.risk_note} /> : null}
                    </Space>
                  )
                }))}
              />
            ) : (
              <Alert type="info" showIcon message={output.message || '暂未产出镜头规划'} />
            )}
          </Card>
        </div>
      )
    }

    if (stepKey === 'audio') {
      const ttsInput = output.tts_input || {}
      const ttsChunks = Array.isArray(ttsInput.chunks) ? ttsInput.chunks : []
      return (
        <div className="human-output-wrap">
          <Card size="small" className="human-output-card" title="音频生成结果">
            <Space wrap>
              {output.provider ? <Tag color="blue">提供商：{output.provider}</Tag> : null}
              {output.voice ? <Tag color="purple">音色：{output.voice}</Tag> : null}
              {output.duration_sec ? <Tag color="geekblue">时长：{formatScore(output.duration_sec)}s</Tag> : null}
              {output.truncated ? <Tag color="warning">文本已截断</Tag> : null}
              {output.audio_path ? (
                <Button
                  size="small"
                  type="primary"
                  onClick={() => {
                    const downloadUrl = output.audio_download_url || `/api/projects/${id}/steps/audio/download`
                    window.open(downloadUrl, '_blank')
                  }}
                >
                  下载音频
                </Button>
              ) : null}
            </Space>
            {output.audio_path ? (
              <div style={{ marginTop: 10 }}>
                <Paragraph strong style={{ marginBottom: 6 }}>音频文件（绝对路径）</Paragraph>
                <Typography.Text
                  copyable={{ text: String(output.audio_path) }}
                  style={{
                    display: 'block',
                    padding: '10px 12px',
                    borderRadius: 8,
                    background: '#f5f5f5',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all'
                  }}
                >
                  {String(output.audio_path)}
                </Typography.Text>
              </div>
            ) : null}
            {output.message ? (
              <Alert style={{ marginTop: 10 }} type="success" showIcon message={output.message} />
            ) : null}
            {(ttsInput.full_text || ttsChunks.length) ? (
              <Collapse
                size="small"
                style={{ marginTop: 10 }}
                items={[
                  {
                    key: 'audio-tts-input',
                    label: `查看输入给 TTS 的内容（分段 ${ttsChunks.length}）`,
                    children: (
                      <Space direction="vertical" size={10} style={{ width: '100%' }}>
                        {ttsInput.full_text ? (
                          <Card size="small" title="完整输入文本">
                            <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: 0, whiteSpace: 'pre-wrap' }}>
                              {ttsInput.full_text}
                            </pre>
                          </Card>
                        ) : null}
                        {ttsChunks.length ? (
                          <Card size="small" title="分段输入列表">
                            <List
                              size="small"
                              dataSource={ttsChunks}
                              renderItem={(chunk, idx) => (
                                <List.Item>
                                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                    <Tag color="blue">分段 {idx + 1}</Tag>
                                    <Typography.Text style={{ whiteSpace: 'pre-wrap' }}>
                                      {String(chunk || '')}
                                    </Typography.Text>
                                  </Space>
                                </List.Item>
                              )}
                            />
                          </Card>
                        ) : null}
                      </Space>
                    )
                  }
                ]}
              />
            ) : null}
          </Card>
        </div>
      )
    }

    if (stepKey === 'video') {
      const meta = project?.metadata || {}
      const persistedVideo = meta.video && typeof meta.video === 'object' ? meta.video : {}
      const videoInfoRaw = output.video_info || {}
      const videoInfo = {
        duration: videoInfoRaw.duration ?? persistedVideo.duration_sec,
        width: videoInfoRaw.width ?? persistedVideo.width,
        height: videoInfoRaw.height ?? persistedVideo.height,
        fps: videoInfoRaw.fps ?? persistedVideo.fps
      }
      const videoPath = output.video_path || meta.video_path || persistedVideo.path
      const hasVideo = Boolean(videoPath)
      const shotStats = output.shot_timeline_stats || persistedVideo.shot_timeline_stats
      const synthesisMode = output.synthesis_mode || persistedVideo.synthesis_mode
      const wanUsed =
        shotStats && typeof shotStats.wan_i2v === 'number' && shotStats.wan_i2v > 0
          ? shotStats.wan_i2v
          : null
      const ltxBoardSaved = Array.isArray(output.ltx_shot_board) && output.ltx_shot_board.length
        ? output.ltx_shot_board
        : (Array.isArray(persistedVideo.ltx_shot_board) ? persistedVideo.ltx_shot_board : [])
      const withAudio = output.with_audio ?? persistedVideo.with_audio
      return (
        <div className="human-output-wrap">
          <Card size="small" className="human-output-card" title="视频合成结果">
            <Space wrap>
              <Tag color="blue">模式：{output.mode || '-'}</Tag>
              {synthesisMode ? <Tag color="cyan">时间轴：{synthesisMode}</Tag> : null}
              <Tag color="purple">素材数：{output.materials_count ?? 0}</Tag>
              {wanUsed !== null ? <Tag color="magenta">Wan I2V 镜头：{wanUsed}</Tag> : null}
              <Tag color={withAudio ? 'success' : 'warning'}>
                {withAudio ? '已挂载音轨' : '未挂载音轨'}
              </Tag>
              {videoInfo.duration ? <Tag color="geekblue">时长：{formatScore(videoInfo.duration)}s</Tag> : null}
              {(videoInfo.width && videoInfo.height) ? <Tag>{videoInfo.width}x{videoInfo.height}</Tag> : null}
              {videoInfo.fps ? <Tag>{formatScore(videoInfo.fps)} fps</Tag> : null}
              {videoPath ? (
                <Button
                  size="small"
                  type="primary"
                  onClick={() => {
                    const downloadUrl = output.video_download_url || `/api/projects/${id}/steps/video/download`
                    window.open(downloadUrl, '_blank')
                  }}
                >
                  下载视频
                </Button>
              ) : null}
            </Space>
            {shotStats ? (
              <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
                分镜统计：素材 {shotStats.from_material ?? '-'} / 静图 {shotStats.generated ?? '-'} / LTX {shotStats.ltx2_t2v ?? '-'}
                {typeof shotStats.wan_i2v === 'number' && shotStats.wan_i2v > 0 ? ` / Wan I2V ${shotStats.wan_i2v}` : ''} / 占位 {shotStats.placeholder ?? '-'}
                {Array.isArray(shotStats?.diagnostics?.hints) && shotStats.diagnostics.hints.length > 0 ? (
                  <Tooltip
                    title={(
                      <div>
                        <div style={{ marginBottom: 6 }}>管线说明（非成片错误）</div>
                        <ul style={{ margin: 0, paddingLeft: 18 }}>
                          {shotStats.diagnostics.hints.map((h, i) => (
                            <li key={i} style={{ marginBottom: 4 }}>{h}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  >
                    <InfoCircleOutlined style={{ marginLeft: 8, cursor: 'help', color: 'rgba(0,0,0,0.45)' }} />
                  </Tooltip>
                ) : null}
              </Paragraph>
            ) : null}
            {ltxBoardSaved.length > 0 ? (
              <div style={{ marginTop: 14 }}>
                <LtxShotBoardPanel
                  title="LTX 每镜输入与输出（本次合成已保存）"
                  ltxShots={ltxBoardSaved}
                  ltxShotsCompleted={ltxBoardSaved.filter((s) => s.status === 'done' || s.status === 'placeholder').length}
                  ltxShotsTotal={ltxBoardSaved.length}
                  pollFast={false}
                  showProgress
                />
              </div>
            ) : null}
            {videoPath ? (
              <div style={{ marginTop: 10 }}>
                <Paragraph strong style={{ marginBottom: 6 }}>视频文件（绝对路径）</Paragraph>
                <Typography.Text
                  copyable={{ text: String(videoPath) }}
                  style={{
                    display: 'block',
                    padding: '10px 12px',
                    borderRadius: 8,
                    background: '#f5f5f5',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all'
                  }}
                >
                  {String(videoPath)}
                </Typography.Text>
              </div>
            ) : null}
            {output.message ? (
              <Alert style={{ marginTop: 10 }} type="success" showIcon message={output.message} />
            ) : null}
          </Card>
          <div style={{ marginTop: 12 }}>
            <FinalVideoPreviewPlugin projectId={id} hasVideo={hasVideo} title="成片预览（插件）" />
          </div>
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

  const formatScore = (value) => {
    const n = Number(value)
    if (!Number.isFinite(n)) return '-'
    return n.toFixed(2)
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
    setQuickJumpFocus('script')
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

      <Card className="glass-card workflow-anchor-nav" size="small" style={{ marginBottom: 14 }}>
        <Space wrap size={8} align="center">
          <Tag color="blue" style={{ marginInlineEnd: 4 }}>快速跳转</Tag>
          <Tag color="geekblue" style={{ marginInlineEnd: 0 }}>流程步骤</Tag>
          {workflowSteps.map((step, wIdx) => {
            const isCurrent = workflowSteps[currentStep]?.key === step.key
            const focused = quickJumpFocus === step.key
            return (
              <Button
                key={`jump-${step.key}`}
                size="small"
                type={focused ? 'primary' : 'default'}
                className={isCurrent && !focused ? 'workflow-step-jump-current' : undefined}
                onClick={() => scrollToWorkflowStep(step.key)}
              >
                <span className="anchor-btn-inner">
                  {wIdx + 1}. {step.title}
                  <span className={`anchor-indicator ${quickJumpStepDotClass(step.key)}`} />
                </span>
              </Button>
            )
          })}
          {showScriptAnchors ? (
            <>
              <Divider type="vertical" style={{ height: 28, margin: '0 4px' }} />
              <Tag color="purple" style={{ marginInlineEnd: 0 }}>脚本卡片内</Tag>
              <Button
                size="small"
                type={quickJumpFocus === 'script' && activeAnchor === 'insight' ? 'primary' : 'default'}
                onClick={() => scrollToScriptSection('insight')}
              >
                <span className="anchor-btn-inner">
                  执行洞察
                  <span className={`anchor-indicator ${insightIndicatorClass}`} />
                </span>
              </Button>
              <Button
                size="small"
                type={quickJumpFocus === 'script' && activeAnchor === 'output' ? 'primary' : 'default'}
                onClick={() => scrollToScriptSection('output')}
              >
                <span className="anchor-btn-inner">
                  脚本输出
                  <span className={`anchor-indicator ${outputIndicatorClass}`} />
                </span>
              </Button>
              <Button
                size="small"
                type={quickJumpFocus === 'script' && activeAnchor === 'history' ? 'primary' : 'default'}
                onClick={() => scrollToScriptSection('history')}
              >
                <span className="anchor-btn-inner">
                  历史版本
                  <Badge size="small" count={scriptHistory.length} />
                </span>
              </Button>
            </>
          ) : null}
        </Space>
      </Card>

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
          const wallStepSeconds =
            inFlight && progressMeta.started_at
              ? getElapsedSeconds(progressMeta.started_at, null)
              : null
          void progressClock
          const displayTotalSeconds = wallStepSeconds != null ? wallStepSeconds : totalSeconds
          const etaSeconds = getEtaSeconds(progressMeta)
          const serverPercent = Number(progressMeta.percent)
          const showServerPct = Number.isFinite(serverPercent) && inFlight
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
                showInfo
                format={(pct) => `${pct}%`}
                style={{ marginBottom: 12 }}
                className="step-progress-bar"
              />
              {inFlight ? (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message={(
                    <span>
                      <strong>{stageLabel}</strong>
                      {showServerPct ? <Tag color="processing" style={{ marginLeft: 8 }}>后端 {serverPercent}%</Tag> : null}
                      <span style={{ marginLeft: 8 }}>{progressText || '处理中…'}</span>
                    </span>
                  )}
                  description={(
                    <Space align="start" wrap size={4}>
                      <span>
                        子阶段 <strong>{currentStageSeconds ?? 0}s</strong>
                        ｜ 累计 <strong>{displayTotalSeconds ?? '-'}</strong>s
                        ｜ 剩余约 <strong>{etaSeconds ?? '-'}</strong>s
                        {step.key === 'video' ? ' ｜ ~750ms 刷新' : ''}
                      </span>
                      <Tooltip
                        title={(
                          <span>
                            当前子阶段已进行 {currentStageSeconds ?? 0}s；本步累计 {displayTotalSeconds ?? '-'}s（本地时钟 + 服务端 started_at）；
                            预计剩余 {etaSeconds ?? '-'}s（按阶段历史估算）。
                            {step.key === 'video' ? ' 视频步会轮询项目状态以更新 LTX 分镜看板与日志。' : ''}
                          </span>
                        )}
                      >
                        <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)', cursor: 'help' }} />
                      </Tooltip>
                    </Space>
                  )}
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
              {step.key === 'video' ? (
                <div className="human-output-wrap" style={{ marginBottom: 12 }}>
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <VideoPipelineEnvPlugin />
                    <VideoGenerationMonitorPlugin
                      activityLog={Array.isArray(progressMeta.activity_log) ? progressMeta.activity_log : []}
                      pollFast={inFlight}
                      ltxShots={Array.isArray(progressMeta.ltx_shots) ? progressMeta.ltx_shots : []}
                      ltxShotsCompleted={Number(progressMeta.ltx_shots_completed) || 0}
                      ltxShotsTotal={Number(progressMeta.ltx_shots_total) || 0}
                    />
                  </Space>
                </div>
              ) : null}
              {stepData ? (
                <div>
                  <Paragraph className="step-status-line">
                    <strong>状态：</strong>
                    <Tag color={statusMeta.tagColor}>{stepData.status}</Tag>
                    {progressMeta.stage ? <Tag color="blue">阶段：{stageLabel}</Tag> : null}
                    {showServerPct ? <Tag color="purple">进度：{serverPercent}%</Tag> : null}
                    {displayTotalSeconds != null ? <Tag color="geekblue">本步累计：{displayTotalSeconds}s</Tag> : null}
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
                                const stagePromptText = (
                                  llmCall?.input
                                  || (
                                    step.key === 'visual'
                                    && item.stage === 'visual_planning'
                                    && String(stepData?.output?.llm_input?.prompt || '').trim()
                                      ? String(stepData?.output?.llm_input?.prompt || '')
                                      : ''
                                  )
                                )
                                const hasStagePrompt = String(stagePromptText || '').trim().length > 0
                                const hasModelCallTag = !!llmCall || (step.key === 'visual' && item.stage === 'visual_planning' && hasStagePrompt)
                                return (
                                  <List.Item>
                                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                                      <Space wrap>
                                        <Tag color={idx === stageTimeline.length - 1 && !item.exited_at ? 'processing' : 'default'}>
                                          {getStageLabel(item.stage)}
                                        </Tag>
                                        {hasModelCallTag ? (
                                          <Tag color={llmCall?.success === false ? 'error' : 'cyan'}>
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
                                      {hasStagePrompt ? (
                                        <Collapse
                                          className="inner-collapse-panel"
                                          size="small"
                                          items={[
                                            {
                                              key: `llm-stage-prompt-${step.key}-${item.stage || idx}`,
                                              label: '查看该阶段 Prompt',
                                              children: (
                                                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', margin: 0, whiteSpace: 'pre-wrap' }}>
                                                  {stagePromptText}
                                                </pre>
                                              )
                                            }
                                          ]}
                                        />
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
