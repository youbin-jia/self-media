import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Button, message, Modal, Form, Input, InputNumber, Select, Space } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { getTopics, refreshTopics, createProject } from '../services/api'

function Home() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  useEffect(() => {
    loadTopics()
  }, [])

  const loadTopics = async () => {
    setLoading(true)
    try {
      const response = await getTopics()
      setTopics(response.data?.data || [])
    } catch (error) {
      message.error('加载选题失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateTopic = async () => {
    try {
      setLoading(true)
      const response = await refreshTopics()
      message.success(response.data?.message || '选题已刷新')
      await loadTopics()
    } catch (error) {
      message.error('创建选题失败')
    } finally {
      setLoading(false)
    }
  }

  const openCreateModal = () => {
    form.resetFields()
    setCreateOpen(true)
  }

  const handleCreateProject = async () => {
    try {
      const values = await form.validateFields()
      setCreating(true)

      const payload = {
        title: values.title,
        topic_source: values.topic_source,
        topic_title: values.topic_title || values.title,
        topic_hot_score: values.topic_hot_score,
        metadata: {
          description: values.description || '',
          created_from: 'home_create_topic'
        }
      }

      const response = await createProject(payload)
      message.success('选题创建成功')
      setCreateOpen(false)
      navigate(`/projects/${response.data.id}`)
    } catch (error) {
      if (error?.errorFields) {
        return
      }
      message.error('创建选题失败')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            创建选题
          </Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={handleCreateTopic}>
            刷新热门选题
          </Button>
        </Space>
      </div>
      <Row gutter={[16, 16]}>
        {topics.map(topic => (
          <Col xs={24} sm={12} md={8} lg={6} key={topic.id}>
            <Card hoverable>
              <Card.Meta
                title={topic.title}
                description={`${topic.source || '未知来源'} · 热度 ${topic.hot_score ?? '--'}`}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        title="创建选题"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreateProject}
        okText="创建"
        cancelText="取消"
        confirmLoading={creating}
        destroyOnClose
      >
        <Form form={form} layout="vertical" requiredMark={false}>
          <Form.Item
            label="选题标题"
            name="title"
            rules={[{ required: true, message: '请输入选题标题' }]}
          >
            <Input placeholder="例如：AI 在短视频创作中的 5 个高效场景" maxLength={255} />
          </Form.Item>

          <Form.Item label="话题来源" name="topic_source" initialValue="manual">
            <Select
              options={[
                { value: 'manual', label: '手动创建' },
                { value: 'weibo', label: '微博' },
                { value: 'zhihu', label: '知乎' },
                { value: 'bilibili', label: 'B站' },
                { value: 'toutiao', label: '头条' }
              ]}
            />
          </Form.Item>

          <Form.Item label="话题原始标题（可选）" name="topic_title">
            <Input placeholder="如来自热榜，可填写原始标题" />
          </Form.Item>

          <Form.Item label="热度分（可选）" name="topic_hot_score">
            <InputNumber min={0} max={10000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="备注（可选）" name="description">
            <Input.TextArea rows={3} placeholder="补充创作方向、受众、风格等信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Home
