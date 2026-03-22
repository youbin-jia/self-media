import { useMemo, useState } from 'react'
import { Card, Button, Space, Typography, Empty } from 'antd'
import { ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'

const { Text } = Typography

/**
 * 工作流插件：成片内嵌预览（HTML5 video，同源 /api 下载地址）
 */
export function FinalVideoPreviewPlugin({ projectId, hasVideo, title = '成片预览' }) {
  const [token, setToken] = useState(0)

  const src = useMemo(() => {
    if (!projectId || !hasVideo) return null
    const base = `${window.location.origin}/api/projects/${projectId}/steps/video/download`
    return `${base}?_=${token}`
  }, [projectId, hasVideo, token])

  if (!projectId || !hasVideo) {
    return null
  }

  return (
    <Card
      size="small"
      className="workflow-plugin-final-video"
      title={(
        <Space>
          <PlayCircleOutlined />
          <span>{title}</span>
        </Space>
      )}
      extra={(
        <Button type="link" size="small" icon={<ReloadOutlined />} onClick={() => setToken(Date.now())}>
          刷新画面
        </Button>
      )}
    >
      <video
        key={src}
        controls
        playsInline
        preload="metadata"
        style={{
          width: '100%',
          maxHeight: 520,
          borderRadius: 8,
          background: '#0f172a'
        }}
        src={src}
      >
        您的浏览器不支持视频标签
      </video>
      <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
        源：同源 API 流式下载；若无法播放请用「下载视频」保存后本地查看。
      </Text>
    </Card>
  )
}

export default FinalVideoPreviewPlugin
