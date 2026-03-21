import { Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu, Breadcrumb, Typography, Grid, Switch } from 'antd'
import { HomeOutlined, ProjectOutlined, MoonOutlined, SunOutlined } from '@ant-design/icons'
import Home from './pages/Home'
import Projects from './pages/Projects'
import ProjectWorkflow from './pages/ProjectWorkflow'
import { useThemeMode } from './context/ThemeContext'

const { Header, Content } = Layout
const { Text } = Typography
const { useBreakpoint } = Grid

function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const screens = useBreakpoint()
  const { themeMode, setThemeMode } = useThemeMode()
  const isDark = themeMode === 'dark'
  const headerHeight = screens.md ? 64 : 56
  const selectedKey = location.pathname.startsWith('/projects') ? '/projects' : '/'
  const pathSegments = location.pathname.split('/').filter(Boolean)
  const isProjectDetail = location.pathname.startsWith('/projects/')

  const contentMaxWidth = (() => {
    if (screens.xxl) return isProjectDetail ? 1880 : 1760
    if (screens.xl) return isProjectDetail ? 1680 : 1560
    if (screens.lg) return isProjectDetail ? 1480 : 1360
    if (screens.md) return 1120
    return '100%'
  })()

  const contentPadding = screens.md ? '20px 24px' : '16px 12px'

  const breadcrumbItems = [{ title: <span style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>首页</span> }]
  if (pathSegments[0] === 'projects') {
    breadcrumbItems.push({
      title: <span style={{ cursor: 'pointer' }} onClick={() => navigate('/projects')}>项目列表</span>
    })
    if (pathSegments[1]) {
      breadcrumbItems.push({
        title: (
          <Text type="secondary">
            项目详情（{pathSegments[1].slice(0, 8)}...）
          </Text>
        )
      })
    }
  }

  return (
    <Layout
      className={`app-shell ${isDark ? 'theme-dark' : 'theme-light'}`}
      style={{ minHeight: '100vh', '--app-header-height': `${headerHeight}px` }}
    >
      <Header
        className="app-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          height: headerHeight,
          lineHeight: `${headerHeight}px`
        }}
      >
        <div className="app-brand">
          自媒体视频自动化系统
        </div>
        <Menu
          className="app-nav-menu"
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          style={{ minWidth: 240 }}
          items={[
            { key: '/', icon: <HomeOutlined />, label: '首页' },
            { key: '/projects', icon: <ProjectOutlined />, label: '项目列表' }
          ]}
          onClick={({ key }) => navigate(key)}
        />
        <div className="theme-switch-wrap">
          <Switch
            checked={isDark}
            checkedChildren={<MoonOutlined />}
            unCheckedChildren={<SunOutlined />}
            onChange={(checked) => setThemeMode(checked ? 'dark' : 'light')}
          />
        </div>
      </Header>
      <Content className="app-content" style={{ padding: contentPadding }}>
        <div className="app-content-inner" style={{ width: '100%', maxWidth: contentMaxWidth, margin: '0 auto' }}>
          <div className="app-breadcrumb-wrap" style={{ marginBottom: 12 }}>
            <Breadcrumb items={breadcrumbItems} />
          </div>
          <div key={location.pathname} className="page-transition">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id" element={<ProjectWorkflow />} />
            </Routes>
          </div>
        </div>
      </Content>
    </Layout>
  )
}

export default App
