import { Card, Space, Tag, Typography, Progress, Spin, Row, Col, Alert } from 'antd'

const { Text } = Typography

const shotStatusMeta = (status) => {
  switch (status) {
    case 'generating':
      return { color: 'processing', text: '生成中' }
    case 'done':
      return { color: 'success', text: '已生成' }
    case 'placeholder':
      return { color: 'warning', text: '占位' }
    case 'pending':
      return { color: 'default', text: '等待' }
    default:
      return { color: 'default', text: status || '-' }
  }
}

/**
 * LTX 分镜：左侧模型输入（提示词/口播），右侧缓存片段路径；用于视频步监控与完成后回看。
 */
export function LtxShotBoardPanel({
  ltxShots = [],
  ltxShotsCompleted = 0,
  ltxShotsTotal = 0,
  pollFast = false,
  showProgress = true,
  title = 'LTX 分镜明细'
}) {
  const shots = Array.isArray(ltxShots) ? ltxShots : []
  const total = Math.max(Number(ltxShotsTotal) || 0, shots.length || 0)
  const done = Math.min(Number(ltxShotsCompleted) || 0, total || 0)
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  if (!shots.length && !total) {
    return null
  }

  return (
    <div className="ltx-shot-board-panel">
      <Typography.Paragraph strong style={{ marginBottom: 8 }}>
        {title}
      </Typography.Paragraph>
      {showProgress && total > 0 ? (
        <Progress
          percent={pct}
          size="small"
          status={done < total && pollFast ? 'active' : 'normal'}
          format={() => `${done}/${total} 镜`}
          style={{ marginBottom: 10 }}
        />
      ) : null}
      {!shots.length && total > 0 ? (
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          正在同步分镜数据…（约 750ms 刷新）
        </Text>
      ) : null}
      <Space direction="vertical" size={10} style={{ width: '100%' }}>
        {shots.map((row, i) => {
          const st = shotStatusMeta(row.status)
          const sn = row.shot_no != null ? row.shot_no : i + 1
          const pt = String(row.prompt || '').trim()
          const nt = String(row.narration || '').trim()
          let inputBody = ''
          if (pt) inputBody = pt
          if (pt && nt) inputBody += `\n\n【口播】${nt}`
          else if (!pt && nt) inputBody = `【口播】${nt}`
          if (!inputBody) inputBody = '—'
          return (
            <Card key={`ltx-${row.shot_index ?? i}-${sn}`} size="small" type="inner">
              <Space wrap style={{ marginBottom: 8 }}>
                <Tag color="blue">镜头 {sn}</Tag>
                <Tag color={st.color}>{st.text}</Tag>
                {row.status === 'generating' ? <Spin size="small" /> : null}
              </Space>
              <Row gutter={[12, 8]}>
                <Col xs={24} md={12}>
                  <Text type="secondary" style={{ fontSize: 12 }}>模型输入（提示词 / 口播）</Text>
                  <pre
                    style={{
                      margin: '6px 0 0',
                      padding: 8,
                      borderRadius: 6,
                      background: '#f5f5f5',
                      fontSize: 11,
                      maxHeight: 160,
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}
                  >
                    {inputBody}
                  </pre>
                </Col>
                <Col xs={24} md={12}>
                  <Text type="secondary" style={{ fontSize: 12 }}>视频输出（侧车缓存）</Text>
                  {row.status === 'generating' ? (
                    <div style={{ marginTop: 8 }}><Text type="secondary">等待侧车返回…</Text></div>
                  ) : row.status === 'done' && row.output_path ? (
                    <Typography.Paragraph
                      copyable={{ text: String(row.output_path) }}
                      style={{
                        margin: '6px 0 0',
                        padding: 8,
                        borderRadius: 6,
                        background: '#f6ffed',
                        fontSize: 11,
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                        wordBreak: 'break-all',
                        marginBottom: 0
                      }}
                    >
                      {String(row.output_path)}
                      {row.size_kb != null ? (
                        <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
                          约 {row.size_kb} KiB
                        </Text>
                      ) : null}
                    </Typography.Paragraph>
                  ) : row.status === 'placeholder' ? (
                    <Alert
                      style={{ marginTop: 8 }}
                      type="warning"
                      showIcon
                      message="占位片段"
                      description="侧车未返回有效文件。请查侧车 / Comfy 日志。"
                    />
                  ) : (
                    <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>—</Text>
                  )}
                </Col>
              </Row>
            </Card>
          )
        })}
      </Space>
    </div>
  )
}

export default LtxShotBoardPanel
