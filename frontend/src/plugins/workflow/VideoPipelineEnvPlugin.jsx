import { useEffect, useState } from 'react'
import { Card, Space, Tag, Alert, Spin, Typography, Tooltip } from 'antd'
import { CloudServerOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { getVideoPipelineEnv } from '../../services/api'

const { Paragraph } = Typography

/**
 * 工作流插件：视频管线环境自检（主力 LTX-2，Wan I2V 可选）
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
  const ltxOn = data?.ltx2_t2v_enabled
  const ltxOk = data?.ltx2_t2v_ready
  const hints = Array.isArray(data?.hints) ? data.hints : []
  const hintTooltip = hints.length
    ? (
      <div style={{ maxWidth: 420 }}>
        {hints.map((h, i) => (
          <Paragraph key={`h-${i}`} style={{ marginBottom: i === hints.length - 1 ? 0 : 8, whiteSpace: 'pre-wrap' }}>
            {i + 1}. {h}
          </Paragraph>
        ))}
      </div>
    )
    : '当前无额外说明'

  return (
    <Card
      size="small"
      className="workflow-plugin-pipeline-env"
      title={(
        <Space wrap>
          <CloudServerOutlined />
          <span>视频生成环境（LTX-2 主力 · Wan I2V 可选）</span>
          <Tooltip title={hintTooltip} placement="bottomLeft">
            <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)', cursor: 'help' }} />
          </Tooltip>
        </Space>
      )}
    >
      <Space wrap style={{ marginBottom: 8 }}>
        <Tag color={ltxOn ? 'blue' : 'default'}>LTX2 T2V {ltxOn ? '已启用' : '未启用'}</Tag>
        <Tag color={ltxOk ? 'success' : 'default'}>{ltxOk ? 'LTX 侧车可调用' : 'LTX 未就绪'}</Tag>
        <Tag>{data?.ltx2_resolution || '-'} @ {data?.ltx2_fps ?? '-'} fps</Tag>
      </Space>
      <Space wrap style={{ marginBottom: 8 }}>
        <Tag color={wanOn ? 'blue' : 'default'}>WAN_I2V {wanOn ? '已启用' : '未启用'}</Tag>
        <Tag color={wanOk ? 'success' : 'warning'}>{wanOk ? 'I2V 可调用' : 'I2V 未就绪'}</Tag>
        <Tag>模式：{data?.wan_i2v_mode || '-'}</Tag>
        <Tag>任务：{data?.wan_task || '-'}</Tag>
        <Tag>分辨率：{data?.wan_size || '-'}</Tag>
      </Space>
      <Space wrap size={[4, 4]} style={{ marginBottom: 0 }}>
        <Tag color={data?.ltx2_endpoint_configured ? 'processing' : 'default'}>
          LTX 端点{data?.ltx2_endpoint_configured ? '已配' : '未配'}
        </Tag>
        <Tag color={data?.wan_endpoint_configured ? 'processing' : 'default'}>
          Wan HTTP 端点{data?.wan_endpoint_configured ? '已配' : '未配'}
        </Tag>
        <Tag color={data?.wan_repo_has_generate_py ? 'success' : 'default'}>
          仓库 generate.py {data?.wan_repo_has_generate_py ? 'OK' : '—'}
        </Tag>
        <Tag color={data?.wan_ckpt_dir_populated ? 'success' : 'default'}>
          权重目录{data?.wan_ckpt_dir_populated ? '已有文件' : '空/未配'}
        </Tag>
      </Space>
    </Card>
  )
}

export default VideoPipelineEnvPlugin
