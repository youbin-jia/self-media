import { useEffect, useState } from 'react'
import { Card, Space, Tag, Alert, Spin, Typography } from 'antd'
import { CloudServerOutlined } from '@ant-design/icons'
import { getVideoPipelineEnv } from '../../services/api'

const { Paragraph } = Typography

/**
 * 工作流插件：视频管线 / 通义万相环境自检
 */
export function VideoPipelineEnvPlugin() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getVideoPipelineEnv()
      .then((res) => {
        if (!cancelled) setData(res?.data || res)
      })
      .catch((e) => {
        if (!cancelled) setErr(e?.message || '无法读取管线环境')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <Card size="small" title={(<Space><CloudServerOutlined /><span>视频生成环境</span></Space>)}>
        <Spin size="small" /> 正在检测后端配置…
      </Card>
    )
  }

  if (err) {
    return (
      <Card size="small" title={(<Space><CloudServerOutlined /><span>视频生成环境</span></Space>)}>
        <Alert type="warning" showIcon message={err} />
      </Card>
    )
  }

  const wanOk = data?.wan_i2v_ready
  const wanOn = data?.wan_i2v_enabled

  return (
    <Card
      size="small"
      className="workflow-plugin-pipeline-env"
      title={(<Space><CloudServerOutlined /><span>视频生成环境（通义万相 Wan I2V）</span></Space>)}
    >
      <Space wrap style={{ marginBottom: 8 }}>
        <Tag color={wanOn ? 'blue' : 'default'}>WAN_I2V {wanOn ? '已启用' : '未启用'}</Tag>
        <Tag color={wanOk ? 'success' : 'warning'}>{wanOk ? 'I2V 可调用' : 'I2V 未就绪'}</Tag>
        <Tag>模式：{data?.wan_i2v_mode || '-'}</Tag>
        <Tag>任务：{data?.wan_task || '-'}</Tag>
        <Tag>分辨率：{data?.wan_size || '-'}</Tag>
      </Space>
      <Space wrap size={[4, 4]} style={{ marginBottom: 8 }}>
        <Tag color={data?.wan_endpoint_configured ? 'processing' : 'default'}>
          HTTP 端点{data?.wan_endpoint_configured ? '已配' : '未配'}
        </Tag>
        <Tag color={data?.wan_repo_has_generate_py ? 'success' : 'default'}>
          仓库 generate.py {data?.wan_repo_has_generate_py ? 'OK' : '—'}
        </Tag>
        <Tag color={data?.wan_ckpt_dir_populated ? 'success' : 'default'}>
          权重目录{data?.wan_ckpt_dir_populated ? '已有文件' : '空/未配'}
        </Tag>
      </Space>
      {Array.isArray(data?.hints) && data.hints.length ? (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {data.hints.map((h, i) => (
            <Alert key={`hint-${i}`} type="info" showIcon message={h} />
          ))}
        </Space>
      ) : (
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>暂无提示</Paragraph>
      )}
    </Card>
  )
}

export default VideoPipelineEnvPlugin
