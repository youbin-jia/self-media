import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Steps, Card, Button, message, Spin, Typography, Divider, Space, Tag, Alert, Progress } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined
} from '@ant-design/icons'
import { getProject, executeStep, regenerateStep } from '../services/api'

const { Title, Paragraph } = Typography

const workflowSteps = [
  { key: 'script', title: '脚本生成' },
  { key: 'review', title: '脚本审核' },
  { key: 'visual', title: '视觉规划' },
  { key: 'audio', title: '音频生成' },
  { key: 'video', title: '视频合成' }
]

function ProjectWorkflow() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    loadProject()
  }, [id])

  const loadProject = async () => {
    setLoading(true)
    try {
      const response = await getProject(id)
      setProject(response.data)
      updateCurrentStep(response.data)
    } catch (error) {
      message.error('加载项目失败')
    } finally {
      setLoading(false)
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

  const handleExecuteStep = async (stepName) => {
    try {
      message.loading({ content: '执行中...', key: 'execute' })
      await executeStep(id, stepName)
      message.success({ content: '执行成功', key: 'execute' })
      loadProject()
    } catch (error) {
      message.error({ content: '执行失败', key: 'execute' })
    }
  }

  const handleRegenerateStep = async (stepName) => {
    try {
      message.loading({ content: '重新生成中...', key: 'regenerate' })
      await regenerateStep(id, stepName)
      message.success({ content: '重新生成成功', key: 'regenerate' })
      loadProject()
    } catch (error) {
      message.error({ content: '重新生成失败', key: 'regenerate' })
    }
  }

  const getStepStatus = (stepKey) => {
    const step = project?.steps?.[stepKey] || project?.metadata?.steps?.[stepKey]
    if (!step) return 'wait'
    return step.status === 'completed' ? 'finish' : step.status === 'processing' ? 'process' : 'wait'
  }

  const getStatusMeta = (stepKey) => {
    const step = project?.steps?.[stepKey] || project?.metadata?.steps?.[stepKey]
    const status = step?.status || 'wait'
    if (status === 'completed') {
      return { cardColor: '#f6ffed', borderColor: '#b7eb8f', tagColor: 'success', text: '已完成', progress: 100 }
    }
    if (status === 'processing') {
      return { cardColor: '#e6f4ff', borderColor: '#91caff', tagColor: 'processing', text: '执行中', progress: 60 }
    }
    return { cardColor: '#fafafa', borderColor: '#d9d9d9', tagColor: 'default', text: '待执行', progress: 0 }
  }

  const completedCount = workflowSteps.filter((step) => getStepStatus(step.key) === 'finish').length
  const overallPercent = Math.round((completedCount / workflowSteps.length) * 100)

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
    <div>
      <Title level={2}>{project.title}</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <div>
            <Paragraph style={{ marginBottom: 4 }}>
              <strong>总体进度：</strong>{completedCount}/{workflowSteps.length} 步
            </Paragraph>
            <Tag color={overallPercent === 100 ? 'success' : 'processing'}>
              {overallPercent === 100 ? '流程完成' : '进行中'}
            </Tag>
          </div>
          <div style={{ minWidth: 260 }}>
            <Progress percent={overallPercent} status={overallPercent === 100 ? 'success' : 'active'} />
          </div>
        </Space>
      </Card>
      <Divider />

      <Steps current={currentStep} style={{ marginBottom: '24px' }}>
        {workflowSteps.map((step, index) => (
          <Steps.Step
            key={step.key}
            title={step.title}
            status={getStepStatus(step.key)}
            icon={
              getStepStatus(step.key) === 'finish' ? <CheckCircleOutlined /> :
              getStepStatus(step.key) === 'process' ? <PlayCircleOutlined /> :
              <ClockCircleOutlined />
            }
          />
        ))}
      </Steps>

      {workflowSteps.map((step, index) => (
        (() => {
          const stepData = project?.steps?.[step.key] || project?.metadata?.steps?.[step.key]
          const statusMeta = getStatusMeta(step.key)
          return (
            <Card
              key={step.key}
              title={`${index + 1}. ${step.title}`}
              style={{
                marginBottom: '16px',
                background: statusMeta.cardColor,
                borderColor: statusMeta.borderColor
              }}
              extra={
                <Space>
                  <Tag color={statusMeta.tagColor}>{statusMeta.text}</Tag>
                  <Button
                    type="primary"
                    onClick={() => handleExecuteStep(step.key)}
                    disabled={getStepStatus(step.key) === 'finish'}
                  >
                    执行
                  </Button>
                  <Button
                    onClick={() => handleRegenerateStep(step.key)}
                    disabled={getStepStatus(step.key) === 'wait'}
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
              />
              {stepData ? (
                <div>
                  <Paragraph>
                    <strong>状态：</strong>
                    <Tag color={statusMeta.tagColor}>{stepData.status}</Tag>
                  </Paragraph>
                  {stepData.output && (
                    <Paragraph>
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
                      <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                        {JSON.stringify(stepData.output, null, 2)}
                      </pre>
                    </Paragraph>
                  )}
                </div>
              ) : (
                <Paragraph type="secondary">等待执行</Paragraph>
              )}
            </Card>
          )
        })()
      ))}
    </div>
  )
}

export default ProjectWorkflow
