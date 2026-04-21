import { Layout, Menu } from 'antd';
import {
  ApartmentOutlined,
  CompassOutlined,
  RadarChartOutlined
} from '@ant-design/icons';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import ScenarioPage from './pages/ScenarioPage';
import ParameterPage from './pages/ParameterPage';
import SimulationPage from './pages/SimulationPage';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/scenarios', icon: <ApartmentOutlined />, label: 'Scenario Management' },
  { key: '/parameters', icon: <CompassOutlined />, label: 'Parameter Input' },
  { key: '/simulation', icon: <RadarChartOutlined />, label: 'Simulation View' }
];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKey = location.pathname.startsWith('/simulation')
    ? '/simulation'
    : location.pathname;

  return (
    <Layout className="app-layout">
      <Sider width={220} theme="light" breakpoint="lg" collapsedWidth={0}>
        <div className="logo">Mini Simulation</div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={item => navigate(item.key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">Algorithm 3D Visualization</Header>
        <Content className="app-content">
          <Routes>
            <Route path="/" element={<Navigate to="/scenarios" replace />} />
            <Route path="/scenarios" element={<ScenarioPage />} />
            <Route path="/parameters" element={<ParameterPage />} />
            <Route path="/simulation/:id" element={<SimulationPage />} />
            <Route path="*" element={<Navigate to="/scenarios" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
