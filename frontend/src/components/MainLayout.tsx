import React from 'react';
import { Layout, Menu, Button, Space, Typography, Tag } from 'antd';
import {
  DashboardOutlined,
  GoldOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
  BranchesOutlined,
  AccountBookOutlined,
  ShoppingCartOutlined,
  FileProtectOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { translations, Language } from '../i18n/translations';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

interface Props {
  lang: Language;
  onLanguageChange: (lang: Language) => void;
  activeMenu: string;
  onMenuChange: (key: string) => void;
  children: React.ReactNode;
}

export const MainLayout: React.FC<Props> = ({
  lang,
  onLanguageChange,
  activeMenu,
  onMenuChange,
  children,
}) => {
  const t = translations[lang];

  const menuItems = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: t.nav_dashboard },
    { key: 'inventory', icon: <GoldOutlined />, label: t.nav_inventory },
    { key: 'manufacturing', icon: <ExperimentOutlined />, label: t.nav_manufacturing },
    { key: 'quality', icon: <SafetyCertificateOutlined />, label: t.nav_quality },
    { key: 'traceability', icon: <BranchesOutlined />, label: t.nav_traceability },
    { key: 'accounting', icon: <AccountBookOutlined />, label: t.nav_accounting },
    { key: 'sales', icon: <ShoppingCartOutlined />, label: t.nav_sales_purchases },
    { key: 'eta', icon: <FileProtectOutlined />, label: t.nav_eta },
  ];

  return (
    <Layout style={{ minHeight: '100vh', direction: t.direction as any }}>
      {/* Sidebar */}
      <Sider
        theme="dark"
        width={260}
        breakpoint="lg"
        collapsedWidth="0"
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ padding: '20px 16px', borderBottom: '1px solid #1f1f1f' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <ExperimentOutlined style={{ fontSize: 28, color: '#52c41a' }} />
            <div>
              <div style={{ color: '#fff', fontWeight: 'bold', fontSize: 16 }}>
                {lang === 'ar' ? 'إيجبشين أجرو ERP' : 'Egyptian Agro ERP'}
              </div>
              <div style={{ color: '#8c8c8c', fontSize: 11 }}>
                {lang === 'ar' ? 'صناعة المبيدات والأسمدة' : 'Chemical Formulation Plant'}
              </div>
            </div>
          </div>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[activeMenu]}
          onClick={({ key }) => onMenuChange(key)}
          items={menuItems}
          style={{ marginTop: 10, fontSize: 14 }}
        />
      </Sider>

      <Layout>
        {/* Header */}
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 1px 4px rgba(0,21,41,0.08)',
            zIndex: 1,
          }}
        >
          <div>
            <Text strong style={{ fontSize: 16 }}>
              {t.system_title}
            </Text>
            <Tag color="cyan" style={{ marginLeft: 10, marginRight: 10 }}>
              {lang === 'ar' ? 'بيئة الإنتاج الصناعي | مصر' : 'Industrial Production | Egypt'}
            </Tag>
          </div>

          <Space size="middle">
            <Tag color="green">
              {lang === 'ar' ? 'المستخدم: مدير النظام (Admin)' : 'User: System Admin'}
            </Tag>
            <Button
              icon={<GlobalOutlined />}
              onClick={() => onLanguageChange(lang === 'ar' ? 'en' : 'ar')}
            >
              {t.lang_toggle}
            </Button>
          </Space>
        </Header>

        {/* Main Content Body */}
        <Content style={{ margin: '24px', minHeight: 280 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};
