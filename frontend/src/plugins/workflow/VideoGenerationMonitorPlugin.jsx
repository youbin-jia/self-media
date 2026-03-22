import { useEffect, useRef, useState } from 'react'
import { Card, Space, Tag, Typography, Progress, Alert, Tooltip, Divider, Collapse } from 'antd'
import {
  ThunderboltOutlined,
  DesktopOutlined,
  HddOutlined,
  VideoCameraOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import { getVideoHostMetrics } from '../../services/api'
import { LtxShotBoardPanel } from '../../components/LtxShotBoardPanel'

const { Text, Paragraph } = Typography

const levelColor = {
  info: 'default',
  warning: 'warning',
  error: 'error',
  debug: 'processing'
}

const RESOURCE_HELP =
  'CPU/内存：运行后端 API 的本机。\n' +
  'GPU：nvidia-smi 瞬时采样。显存占用通常比「核心利用率」更能反映推理负载；核心% 在空闲或短脉冲时易为 0。\n' +
  '若 ComfyUI / LTX 侧车在其它主机或容器内用 GPU，本机 GPU 可能长期接近空闲。'

const ACTIVITY_LOG_HELP =
  '文本日志来自后端步骤 progress.activity_log，记录关键节点（加载素材、侧车请求、MoviePy 等）。'

/**
 * 视频合成步骤：LTX 分镜看板 + 活动日志 + CPU/GPU（轮询）
 */
export function VideoGenerationMonitorPlugin({
  activityLog = [],
  pollFast = false,
  ltxShots = [],
  ltxShotsCompleted = 0,
  ltxShotsTotal = 0
}) {
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
  const gpuHelpBody = [RESOURCE_HELP.trim()]
  if (metrics?.metrics_hint) {
    gpuHelpBody.push(String(metrics.metrics_hint))
  }
  const gpuHelpText = gpuHelpBody.join('\n\n')

  const showLtxBoard =
    Array.isArray(ltxShots) &&
    (ltxShots.length > 0 || (Number(ltxShotsTotal) > 0 && pollFast))

  return (
    <Card
      size="small"
      className="workflow-plugin-video-monitor"
      title={(
        <Space>
          <VideoCameraOutlined />
          <span>生成日志与资源监控</span>
          {pollFast ? <Tag color="processing">实时</Tag> : <Tag>闲时 2s 刷新</Tag>}
          <Tooltip title={gpuHelpText}>
            <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)', cursor: 'help' }} />
          </Tooltip>
        </Space>
      )}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {showLtxBoard ? (
          <>
            <LtxShotBoardPanel
              title="LTX 分镜进度（每镜输入 / 输出）"
              ltxShots={ltxShots}
              ltxShotsCompleted={ltxShotsCompleted}
              ltxShotsTotal={ltxShotsTotal}
              pollFast={pollFast}
              showProgress
            />
            <Divider style={{ margin: '4px 0 8px' }} />
          </>
        ) : null}

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
            <Tooltip title={gpuHelpText}>
              <InfoCircleOutlined style={{ marginLeft: 8, color: 'rgba(0,0,0,0.45)', cursor: 'help' }} />
            </Tooltip>
          </Paragraph>
          {!metrics?.gpu_available ? (
            <Text type="secondary">未检测到 NVIDIA GPU 或 nvidia-smi 不可用</Text>
          ) : (
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              {gpus.map((g) => {
                const vramPct = Math.min(100, Number(g.mem_percent) || 0)
                const sm = g.utilization_gpu
                const smNum = sm == null ? null : Number(sm)
                const memCtrl = g.utilization_memory
                const memCtrlNum = memCtrl == null ? null : Number(memCtrl)
                return (
                  <div key={g.index}>
                    <Text ellipsis style={{ display: 'block', maxWidth: '100%' }} title={g.name}>
                      GPU {g.index}：{g.name}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>显存</Text>
                    <Progress
                      percent={vramPct}
                      size="small"
                      strokeColor="#1890ff"
                      format={() =>
                        `${g.mem_used_mb ?? '-'}/${g.mem_total_mb ?? '-'} MiB (${vramPct}%)`
                      }
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>核心</Text>
                    <Progress
                      percent={smNum == null ? 0 : Math.min(100, smNum)}
                      size="small"
                      strokeColor="#52c41a"
                      format={() => (smNum == null ? 'N/A' : `${smNum}%`)}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>显存控制器</Text>
                    <Progress
                      percent={memCtrlNum == null ? 0 : Math.min(100, memCtrlNum)}
                      size="small"
                      strokeColor="#faad14"
                      format={() => (memCtrlNum == null ? 'N/A' : `${memCtrlNum}%`)}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {g.temperature_c != null ? `${g.temperature_c}°C` : ''}
                    </Text>
                  </div>
                )
              })}
            </Space>
          )}
        </div>

        <Collapse
          bordered={false}
          className="video-activity-log-collapse"
          style={{ background: 'transparent' }}
          defaultActiveKey={['activity-log']}
          items={[
            {
              key: 'activity-log',
              label: (
                <Space align="center" size={8}>
                  <span style={{ fontWeight: 600 }}>活动日志</span>
                  {activityLog.length > 0 ? (
                    <Tag style={{ margin: 0 }}>{activityLog.length} 条</Tag>
                  ) : (
                    <Tag style={{ margin: 0 }} color="default">空</Tag>
                  )}
                  <Tooltip title={ACTIVITY_LOG_HELP}>
                    <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)', cursor: 'help' }} />
                  </Tooltip>
                </Space>
              ),
              children: (
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
                      暂无日志
                      <Tooltip title="执行或重新生成「视频合成」步骤后，将显示关键节点。">
                        <InfoCircleOutlined style={{ marginLeft: 6, cursor: 'help' }} />
                      </Tooltip>
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
              )
            }
          ]}
        />
      </Space>
    </Card>
  )
}

export default VideoGenerationMonitorPlugin
