import { useEffect, useRef, useState } from 'react'
import { Card, Space, Tag, Typography, Progress, Alert } from 'antd'
import {
  ThunderboltOutlined,
  DesktopOutlined,
  HddOutlined,
  VideoCameraOutlined
} from '@ant-design/icons'
import { getVideoHostMetrics } from '../../services/api'

const { Text, Paragraph } = Typography

const levelColor = {
  info: 'default',
  warning: 'warning',
  error: 'error',
  debug: 'processing'
}

/**
 * 视频合成步骤：活动日志 + CPU/GPU 实时监控（轮询后端 /api/video/host-metrics）
 */
export function VideoGenerationMonitorPlugin({ activityLog = [], pollFast = false }) {
  const logRef = useRef(null)
  const [metrics, setMetrics] = useState(null)
  const [metricsErr, setMetricsErr] = useState(null)

  useEffect(() => {
    const el = logRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [activityLog])

  useEffect(() => {
    let cancelled = false
    const tick = async () => {
      try {
        const res = await getVideoHostMetrics()
        if (!cancelled) {
          setMetrics(res?.data ?? res)
          setMetricsErr(null)
        }
      } catch (e) {
        if (!cancelled) {
          setMetricsErr(e?.message || '无法读取主机指标')
        }
      }
    }
    tick()
    const ms = pollFast ? 1000 : 2000
    const id = window.setInterval(tick, ms)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [pollFast])

  const gpus = Array.isArray(metrics?.gpus) ? metrics.gpus : []

  return (
    <Card
      size="small"
      className="workflow-plugin-video-monitor"
      title={(
        <Space>
          <VideoCameraOutlined />
          <span>生成日志与资源监控</span>
          {pollFast ? <Tag color="processing">实时</Tag> : <Tag>闲时 2s 刷新</Tag>}
        </Space>
      )}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div>
          <Paragraph strong style={{ marginBottom: 8 }}>
            <DesktopOutlined style={{ marginRight: 6 }} />
            CPU / 内存
          </Paragraph>
          {metricsErr ? (
            <Alert type="warning" showIcon message={metricsErr} style={{ marginBottom: 8 }} />
          ) : null}
          {metrics ? (
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <div>
                <Text type="secondary">CPU</Text>
                <Progress
                  percent={Math.min(100, Number(metrics.cpu_percent) || 0)}
                  size="small"
                  status="active"
                  format={() => `${metrics.cpu_percent ?? '-'}%`}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  逻辑核 {metrics.cpu_count_logical ?? '-'}
                </Text>
              </div>
              <div>
                <Text type="secondary"><HddOutlined /> 内存</Text>
                <Progress
                  percent={Math.min(100, Number(metrics.mem_percent) || 0)}
                  size="small"
                  strokeColor="#722ed1"
                  format={() => `${metrics.mem_percent ?? '-'}%`}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {metrics.mem_used_mb ?? '-'} / {metrics.mem_total_mb ?? '-'} MiB
                </Text>
              </div>
            </Space>
          ) : (
            <Text type="secondary">加载中…</Text>
          )}
        </div>

        <div>
          <Paragraph strong style={{ marginBottom: 8 }}>
            <ThunderboltOutlined style={{ marginRight: 6 }} />
            GPU（nvidia-smi）
          </Paragraph>
          {!metrics?.gpu_available ? (
            <Text type="secondary">未检测到 NVIDIA GPU 或 nvidia-smi 不可用</Text>
          ) : (
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              {gpus.map((g) => (
                <div key={g.index}>
                  <Text ellipsis style={{ display: 'block', maxWidth: '100%' }} title={g.name}>
                    GPU {g.index}：{g.name}
                  </Text>
                  <Progress
                    percent={Math.min(100, Number(g.utilization_gpu) || 0)}
                    size="small"
                    strokeColor="#52c41a"
                    format={() => `${g.utilization_gpu ?? '-'}%`}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    显存 {g.mem_used_mb ?? '-'}/{g.mem_total_mb ?? '-'} MiB
                    {g.temperature_c != null ? ` ｜ ${g.temperature_c}°C` : ''}
                  </Text>
                </div>
              ))}
            </Space>
          )}
        </div>

        <div>
          <Paragraph strong style={{ marginBottom: 6 }}>活动日志</Paragraph>
          <div
            ref={logRef}
            className="video-activity-log-pre"
            style={{
              margin: 0,
              maxHeight: 280,
              overflow: 'auto',
              padding: '10px 12px',
              borderRadius: 8,
              background: '#0d1117',
              color: '#c9d1d9',
              fontSize: 12,
              lineHeight: 1.5,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
            }}
          >
            {activityLog.length === 0 ? (
              <span style={{ color: '#8b949e' }}>
                暂无日志；点击「执行 / 重新生成」视频步骤后将在此显示关键节点。
              </span>
            ) : (
              activityLog.map((row, i) => {
                const t = row.at || row.time || ''
                const lv = (row.level || 'info').toLowerCase()
                const msg = row.message || row.msg || ''
                return (
                  <div key={`${t}-${i}`} style={{ marginBottom: 8 }}>
                    <div>
                      <Tag color={levelColor[lv] || 'default'} style={{ marginRight: 8, fontSize: 11 }}>
                        {lv}
                      </Tag>
                      <span style={{ color: '#8b949e' }}>{t}</span>
                    </div>
                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{msg}</div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </Space>
    </Card>
  )
}

export default VideoGenerationMonitorPlugin
