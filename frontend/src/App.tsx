import React, { useState } from 'react';
import { ConfigProvider } from 'antd';
import arEG from 'antd/locale/ar_EG';
import enUS from 'antd/locale/en_US';
import { MainLayout } from './components/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { InventoryPage } from './pages/InventoryPage';
import { ManufacturingPage } from './pages/ManufacturingPage';
import { QualityPage } from './pages/QualityPage';
import { TraceabilityPage } from './pages/TraceabilityPage';
import { AccountingPage } from './pages/AccountingPage';
import { SalesPurchasingPage } from './pages/SalesPurchasingPage';
import { ETAInvoicingPage } from './pages/ETAInvoicingPage';
import { Language } from './i18n/translations';

export const App: React.FC = () => {
  const [lang, setLang] = useState<Language>('ar'); // Arabic is default
  const [activeMenu, setActiveMenu] = useState<string>('dashboard');

  const renderContent = () => {
    switch (activeMenu) {
      case 'dashboard':
        return <DashboardPage lang={lang} onNavigate={setActiveMenu} />;
      case 'inventory':
        return <InventoryPage lang={lang} />;
      case 'manufacturing':
        return <ManufacturingPage lang={lang} />;
      case 'quality':
        return <QualityPage lang={lang} />;
      case 'traceability':
        return <TraceabilityPage lang={lang} />;
      case 'accounting':
        return <AccountingPage lang={lang} />;
      case 'sales':
        return <SalesPurchasingPage lang={lang} />;
      case 'eta':
        return <ETAInvoicingPage lang={lang} />;
      default:
        return <DashboardPage lang={lang} onNavigate={setActiveMenu} />;
    }
  };

  return (
    <ConfigProvider
      direction={lang === 'ar' ? 'rtl' : 'ltr'}
      locale={lang === 'ar' ? arEG : enUS}
      theme={{
        token: {
          colorPrimary: '#1b7f3b', // Agricultural Emerald Green
          fontFamily: "'Cairo', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          borderRadius: 6,
        },
      }}
    >
      <MainLayout
        lang={lang}
        onLanguageChange={setLang}
        activeMenu={activeMenu}
        onMenuChange={setActiveMenu}
      >
        {renderContent()}
      </MainLayout>
    </ConfigProvider>
  );
};

export default App;
