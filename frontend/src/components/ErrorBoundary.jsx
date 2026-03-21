import React from 'react'
import { Button, Result, Space, Typography } from 'antd'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null
    }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error, errorInfo) {
    // Keep runtime details in console for debugging.
    // eslint-disable-next-line no-console
    console.error('Global ErrorBoundary caught an error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null
    })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Result
            status="error"
            title="页面发生错误"
            subTitle="应用遇到了运行时异常。你可以重试、刷新页面，或先返回首页。"
            extra={(
              <Space>
                <Button onClick={this.handleRetry}>重试</Button>
                <Button type="primary" onClick={this.handleReload}>刷新页面</Button>
                <Button onClick={this.handleGoHome}>回到首页</Button>
              </Space>
            )}
          >
            {this.state.error?.message ? (
              <Typography.Text type="secondary">
                错误信息：{this.state.error.message}
              </Typography.Text>
            ) : null}
          </Result>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
