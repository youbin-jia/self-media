import { Routes, Route } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import { HomeOutlined, ProjectOutlined } from '@ant-design/icons'
import Home from './pages/Home'
import Projects from './pages/Projects'
import ProjectWorkflow from './pages/ProjectWorkflow'

const { Header, Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: '18px', fontWeight: 'bold', marginRight: '40px' }}>
          自媒体视频自动化系统
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={['/']}
          items={[
            { key: '/', icon: <HomeOutlined />, label: '首页' },
            { key: '/projects', icon: <ProjectOutlined />, label: '项目列表' }
          ]}
          onClick={({ key }) => window.location.href = key}
        />
      </Header>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectWorkflow />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
