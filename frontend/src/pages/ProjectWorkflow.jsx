import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Steps, Card, Button, message, Spin, Typography, Divider } from 'antd'
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
    if (!projectData || !projectData.steps) return
    const stepIndex = workflowSteps.findIndex(
      step => projectData.steps[step.key]?.status !== 'completed'
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
    if (!project || !project.steps) return 'wait'
    const step = project.steps[stepKey]
    if (!step) return 'wait'
    return step.status === 'completed' ? 'finish' : step.status === 'processing' ? 'process' : 'wait'
  }

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
        <Card
          key={step.key}
          title={`${index + 1}. ${step.title}`}
          style={{ marginBottom: '16px' }}
          extra={
            <Space>
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
          {project.steps && project.steps[step.key] ? (
            <div>
              <Paragraph>
                <strong>状态：</strong>
                <Tag color={getStepStatus(step.key) === 'finish' ? 'green' : 'blue'}>
                  {project.steps[step.key].status}
                </Tag>
              </Paragraph>
              {project.steps[step.key].output && (
                <Paragraph>
                  <strong>输出：</strong>
                  <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                    {JSON.stringify(project.steps[step.key].output, null, 2)}
                  </pre>
                </Paragraph>
              )}
            </div>
          ) : (
            <Paragraph type="secondary">等待执行</Paragraph>
          )}
        </Card>
      ))}
    </div>
  )
}

export default ProjectWorkflow
