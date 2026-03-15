import { useState, useEffect } from 'react'
import { Card, Row, Col, Button, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { getTopics, deleteTopic } from '../services/api'

function Home() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadTopics()
  }, [])

  const loadTopics = async () => {
    setLoading(true)
    try {
      const response = await getTopics()
      setTopics(response.data)
    } catch (error) {
      message.error('加载选题失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteTopic(id)
      message.success('删除成功')
      loadTopics()
    } catch (error) {
      message.error('删除失败')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <Button type="primary" icon={<PlusOutlined />}>
          创建选题
        </Button>
      </div>
      <Row gutter={[16, 16]}>
        {topics.map(topic => (
          <Col xs={24} sm={12} md={8} lg={6} key={topic.id}>
            <Card
              hoverable
              actions={[
                <EditOutlined key="edit" />,
                <DeleteOutlined key="delete" onClick={() => handleDelete(topic.id)} />
              ]}
            >
              <Card.Meta
                title={topic.title}
                description={topic.description || '暂无描述'}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}

export default Home
