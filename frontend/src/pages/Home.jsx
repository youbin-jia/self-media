import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Button, message, Modal, Form, Input, InputNumber, Select, Space, Typography, Tabs, Tag, Spin } from 'antd'
import { PlusOutlined, ReloadOutlined, ClockCircleOutlined, FireOutlined } from '@ant-design/icons'
import { getTopics, refreshTopics, createProject, getTopicPlatforms, getTopicStats } from '../services/api'
import AnimatedNumber from '../components/AnimatedNumber'

const { Title, Text } = Typography

// Platform icons/colors mapping
const PLATFORM_CONFIG = {
  weibo: { name: '微博', color: '#ff8200' },
  douyin: { name: '抖音', color: '#000000' },
  bilibili: { name: 'B站', color: '#00a1d6' },
  zhihu: { name: '知乎', color: '#0066ff' },
  baidu: { name: '百度', color: '#2932e1' },
  toutiao: { name: '今日头条', color: '#f85959' },
  kuaishou: { name: '快手', color: '#ff4906' },
  tieba: { name: '贴吧', color: '#4879bd' },
  douban: { name: '豆瓣', color: '#00b51d' },
  juejin: { name: '掘金', color: '#1e80ff' },
  v2ex: { name: 'V2EX', color: '#333333' },
  xiaohongshu: { name: '小红书', color: '#fe2c55' },
  default: { name: '其他', color: '#999999' }
}

function Home() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  // New state for platform filtering
  const [platforms, setPlatforms] = useState([])
  const [activePlatform, setActivePlatform] = useState('all')
  const [stats, setStats] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadPlatforms()
    loadTopics()
    loadStats()
  }, [])

  useEffect(() => {
    loadTopics()
  }, [activePlatform])

  const loadPlatforms = async () => {
    try {
      const response = await getTopicPlatforms()
      setPlatforms(response.data?.data || [])
    } catch (error) {
      console.error('Failed to load platforms:', error)
    }
  }

  const loadStats = async () => {
    try {
      const response = await getTopicStats()
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const loadTopics = async () => {
    setLoading(true)
    try {
      const params = {}
      if (activePlatform && activePlatform !== 'all') {
        params.source = activePlatform
      }
      const response = await getTopics(params)
      setTopics(response.data?.data || [])
    } catch (error) {
      message.error('加载选题失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const response = await refreshTopics()
      message.success(response.data?.message || '选题已刷新')
      await loadTopics()
      await loadStats()
    } catch (error) {
      message.error('刷新选题失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      setRefreshing(false)
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

  const formatTime = (isoString) => {
    if (!isoString) return '--'
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return null
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleTopicClick = (topic) => {
    // 优先使用移动端链接（适合手机浏览），否则使用普通链接
    const url = topic.mobile_url || topic.url
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  const getPlatformConfig = (source) => {
    return PLATFORM_CONFIG[source] || PLATFORM_CONFIG.default
  }

  // Generate tab items - only show main platforms
  const mainPlatforms = ['weibo', 'xiaohongshu', 'douyin', 'bilibili', 'zhihu', 'toutiao', 'baidu']
  const tabItems = [
    { key: 'all', label: `全部 (${stats?.total_topics || 0})` },
    ...(mainPlatforms.map(pid => {
      const config = PLATFORM_CONFIG[pid] || PLATFORM_CONFIG.default
      const count = stats?.platforms?.find(s => s.source === pid)?.count || 0
      return { key: pid, label: `${config.name} (${count})` }
    }) || [])
  ]

  return (
    <div className="page-home">
      <Card className="hero-card" bordered={false}>
        <div className="hero-main">
          <div>
            <Title level={2} style={{ marginBottom: 8 }}>发现热门选题，快速生成项目</Title>
            <Text type="secondary">从话题监控到脚本生成，一步进入创作工作流。</Text>
          </div>
          <div className="hero-metrics">
            <span><strong><AnimatedNumber value={stats?.total_topics || topics.length} /></strong> 个热门选题</span>
            {stats?.last_updated && (
              <span style={{ marginLeft: 16, color: '#999' }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                {formatTime(stats.last_updated)}
              </span>
            )}
          </div>
        </div>
      </Card>

      <div className="topic-toolbar">
        <div className="topic-tabs-wrap">
          <Tabs
            activeKey={activePlatform}
            onChange={setActivePlatform}
            items={tabItems}
            size="small"
            style={{ marginBottom: 0 }}
          />
        </div>
        <Space className="topic-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal} className="cta-btn">
            创建选题
          </Button>
          <Button
            icon={<ReloadOutlined spin={refreshing} />}
            loading={refreshing}
            onClick={handleRefresh}
            className="subtle-btn"
          >
            刷新热榜
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[24, 24]}>
          {topics.map((topic, index) => {
            const platformConfig = getPlatformConfig(topic.source)
            const originalTime = formatTimestamp(topic.original_timestamp)
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={topic.id}>
                <Card
                  hoverable
                  className="topic-card hover-tilt stagger-fade-in"
                  style={{ animationDelay: `${Math.min(0.06 * (index + 1), 0.5)}s` }}
                  onClick={() => handleTopicClick(topic)}
                >
                  <Card.Meta
                    title={
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <span style={{ flex: 1 }}>
                          {topic.title}
                        </span>
                      </div>
                    }
                    description={
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <Tag color={platformConfig.color} style={{ margin: 0 }}>
                            {platformConfig.name}
                          </Tag>
                          <span style={{ color: '#ff4d4f', fontSize: 13 }}>
                            <FireOutlined style={{ marginRight: 4 }} />
                            {topic.hot_score?.toLocaleString() || '--'}
                          </span>
                        </div>
                        {originalTime && (
                          <div style={{ fontSize: 12, color: '#999' }}>
                            <ClockCircleOutlined style={{ marginRight: 4 }} />
                            {originalTime}
                          </div>
                        )}
                      </div>
                    }
                  />
                </Card>
              </Col>
            )
          })}
        </Row>

        {topics.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
            <Text type="secondary">暂无热榜数据，请点击"刷新热榜"获取最新数据</Text>
          </div>
        )}
      </Spin>

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
                { value: 'douyin', label: '抖音' },
                { value: 'toutiao', label: '头条' }
              ]}
            />
          </Form.Item>

          <Form.Item label="话题原始标题（可选）" name="topic_title">
            <Input placeholder="如来自热榜，可填写原始标题" />
          </Form.Item>

          <Form.Item label="热度分（可选）" name="topic_hot_score">
            <InputNumber min={0} max={10000000} style={{ width: '100%' }} />
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
