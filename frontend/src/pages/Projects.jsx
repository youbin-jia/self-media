import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Tag, Space, message, Card, Typography, Tooltip, Popconfirm, Grid, Row, Col, Statistic } from 'antd'
import { PlusOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import { getProjects, deleteProject } from '../services/api'

const { Text, Title } = Typography
const { useBreakpoint } = Grid

function Projects() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const screens = useBreakpoint()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const response = await getProjects()
      setProjects(response.data)
    } catch (error) {
      message.error('加载项目失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteProject(id)
      message.success('删除成功')
      loadProjects()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const formatDateTime = (value) => {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('zh-CN', { hour12: false })
  }

  const renderStatus = (status) => {
    const statusMap = {
      completed: { color: 'success', text: '已完成' },
      processing: { color: 'processing', text: '处理中' },
      pending: { color: 'default', text: '待处理' }
    }
    const item = statusMap[status] || { color: 'default', text: status || '未知' }
    return <Tag color={item.color}>{item.text}</Tag>
  }

  const pendingCount = projects.filter((item) => item.status === 'pending').length
  const processingCount = projects.filter((item) => item.status === 'processing').length
  const completedCount = projects.filter((item) => item.status === 'completed').length
  const latestProject = projects[0]
  const showSidebar = screens.xl

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 300,
      render: (id) => (
        <Tooltip title={id}>
          <Text copyable={{ text: id }} style={{ fontSize: 12 }}>
            {id?.slice(0, 8)}...{id?.slice(-8)}
          </Text>
        </Tooltip>
      )
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: renderStatus
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 220,
      render: formatDateTime
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            size="small"
            onClick={() => navigate(`/projects/${record.id}`)}
          >
            查看
          </Button>
          <Popconfirm title="确认删除该项目？" okText="删除" cancelText="取消" onConfirm={() => handleDelete(record.id)}>
            <Button icon={<DeleteOutlined />} danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <Row gutter={showSidebar ? 16 : 0}>
      <Col xs={24} xl={18}>
        <Card bordered={false} style={{ width: '100%' }} bodyStyle={{ padding: screens.md ? 20 : 12 }}>
          <div
            style={{
              marginBottom: 16,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: screens.sm ? 'center' : 'flex-start',
              gap: 12,
              flexWrap: 'wrap'
            }}
          >
            <div>
              <Title level={4} style={{ margin: 0 }}>项目列表</Title>
              <Text type="secondary">共 {projects.length} 个项目</Text>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/')}>
              创建项目
            </Button>
          </div>
          <Table
            columns={columns}
            dataSource={projects}
            rowKey="id"
            loading={loading}
            style={{ width: '100%' }}
            bordered
            size="middle"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            scroll={{ x: 960 }}
            locale={{ emptyText: '暂无项目，点击右上角创建项目' }}
          />
        </Card>
      </Col>
      {showSidebar ? (
        <Col xs={24} xl={6}>
          <div style={{ position: 'sticky', top: 'calc(var(--app-header-height, 64px) + 16px)' }}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Card title="数据概览" bordered={false}>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <Statistic title="项目总数" value={projects.length} />
                <Row gutter={12}>
                  <Col span={8}><Statistic title="待处理" value={pendingCount} /></Col>
                  <Col span={8}><Statistic title="处理中" value={processingCount} /></Col>
                  <Col span={8}><Statistic title="已完成" value={completedCount} /></Col>
                </Row>
              </Space>
              </Card>
              <Card title="最近项目" bordered={false}>
              {latestProject ? (
                <Space direction="vertical" size={8}>
                  <Text strong>{latestProject.title}</Text>
                  <Text type="secondary">创建于：{formatDateTime(latestProject.created_at)}</Text>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/projects/${latestProject.id}`)}>
                    查看最近项目
                  </Button>
                </Space>
              ) : (
                <Text type="secondary">暂无项目数据</Text>
              )}
              </Card>
            </Space>
          </div>
        </Col>
      ) : null}
    </Row>
  )
}

export default Projects
