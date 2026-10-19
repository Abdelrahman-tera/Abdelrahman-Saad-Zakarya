import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Alert, Space } from 'antd';
import {
  ExperimentOutlined,
  GoldOutlined,
  CheckCircleOutlined,
  AlertOutlined,
  DollarOutlined,
  FileTextOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
  onNavigate: (key: string) => void;
}

export const DashboardPage: React.FC<Props> = ({ lang, onNavigate }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    batchesCount: 0,
    quarantineCount: 0,
    productionOrdersCount: 0,
    invoicesCount: 0,
    etaValidCount: 0,
    totalProfit: '0.00',
  });
  const [recentBatches, setRecentBatches] = useState([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [batchesRes, ordersRes, invoicesRes, etaRes, plRes] = await Promise.all([
        apiClient.getBatches(),
        apiClient.getProductionOrders(),
        apiClient.getSalesInvoices(),
        apiClient.getETADocuments(),
        apiClient.getProfitLoss(),
      ]);

      const batches = batchesRes.data.results || batchesRes.data || [];
      const orders = ordersRes.data.results || ordersRes.data || [];
      const invoices = invoicesRes.data.results || invoicesRes.data || [];
      const etaDocs = etaRes.data.results || etaRes.data || [];

      const quarCount = batches.filter((b: any) => b.status === 'QUARANTINE').length;
      const etaValid = etaDocs.filter((d: any) => d.status === 'VALID').length;

      setStats({
        batchesCount: batches.length,
        quarantineCount: quarCount,
        productionOrdersCount: orders.length,
        invoicesCount: invoices.length,
        etaValidCount: etaValid,
        totalProfit: plRes.data.net_profit || '0.00',
      });
      setRecentBatches(batches.slice(0, 5));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const batchColumns = [
    {
      title: t.batch_number,
      dataIndex: 'batch_number',
      key: 'batch_number',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: lang === 'ar' ? 'المنتج' : 'Product',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: t.mfg_date,
      dataIndex: 'manufacturing_date',
      key: 'manufacturing_date',
    },
    {
      title: t.exp_date,
      dataIndex: 'expiry_date',
      key: 'expiry_date',
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'blue';
        let text = status;
        if (status === 'RELEASED') { color = 'green'; text = lang === 'ar' ? 'معتمد ومفرج عنه' : 'RELEASED'; }
        else if (status === 'QUARANTINE') { color = 'gold'; text = lang === 'ar' ? 'تحت الحجر والفحص' : 'QUARANTINE'; }
        else if (status === 'REJECTED') { color = 'red'; text = lang === 'ar' ? 'مرفوض' : 'REJECTED'; }
        return <Tag color={color}>{text}</Tag>;
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_dashboard}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'نظرة عامة حية على خطوط الإنتاج الكيميائي، الأرصدة، الفحص، ومنظومة الضرائب المصرية'
              : 'Real-time overview of chemical formulation, perpetual inventory, and ETA tax submissions'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      {stats.quarantineCount > 0 && (
        <Alert
          message={
            lang === 'ar'
              ? `يوجد عدد (${stats.quarantineCount}) تشغيلة قيد الحجر والفحص الكيميائي بانتظار الإفراج أو الرفض!`
              : `There are (${stats.quarantineCount}) chemical batches currently in quarantine awaiting QC release or rejection!`
          }
          type="warning"
          showIcon
          style={{ marginBottom: 20 }}
          action={
            <Button size="small" type="primary" onClick={() => onNavigate('quality')}>
              {lang === 'ar' ? 'الانتقال لرقابة الجودة' : 'Go to QC'}
            </Button>
          }
        />
      )}

      {/* KPI Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} hoverable onClick={() => onNavigate('inventory')}>
            <Statistic
              title={lang === 'ar' ? 'إجمالي لوتات وتشغيلات المخزون' : 'Total Tracked Batches'}
              value={stats.batchesCount}
              prefix={<GoldOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} hoverable onClick={() => onNavigate('quality')}>
            <Statistic
              title={lang === 'ar' ? 'تشغيلات قيد الحجر والفحص' : 'Batches in Quarantine'}
              value={stats.quarantineCount}
              prefix={<AlertOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: stats.quarantineCount > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} hoverable onClick={() => onNavigate('manufacturing')}>
            <Statistic
              title={lang === 'ar' ? 'أوامر تصنيع وخلط كيميائي' : 'Production Formulation Orders'}
              value={stats.productionOrdersCount}
              prefix={<ExperimentOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} hoverable onClick={() => onNavigate('eta')}>
            <Statistic
              title={lang === 'ar' ? 'فواتير معتمدة بمصلحة الضرائب (ETA)' : 'ETA Validated E-Invoices'}
              value={stats.etaValidCount}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Financial Snapshot */}
      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} md={12}>
          <Card title={lang === 'ar' ? 'صافي الربح التشغيلي المحاسبي' : 'Operating Net Profit (P&L)'} bordered={false}>
            <Statistic
              value={stats.totalProfit}
              suffix={t.currency}
              prefix={<DollarOutlined />}
              valueStyle={{ color: Number(stats.totalProfit) >= 0 ? '#3f8600' : '#cf1322', fontSize: 32 }}
            />
            <p style={{ marginTop: 10, color: '#8c8c8c' }}>
              {lang === 'ar'
                ? 'محسوب بدقة من واقع قيود اليومية لدفتر الأستاذ العام (إيرادات المبيعات - تكلفة البضاعة المباعة والمصروفات)'
                : 'Calculated strictly from authoritative general ledger journal items (Revenue minus COGS & Expenses)'}
            </p>
            <Button type="link" onClick={() => onNavigate('accounting')} style={{ padding: 0 }}>
              {lang === 'ar' ? 'عرض ميزان المراجعة وقائمة الدخل ←' : 'View Trial Balance & Income Statement →'}
            </Button>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title={lang === 'ar' ? 'شجرة التتبع واستدعاء التشغيلات' : 'Batch Recall & Genealogy Engine'} bordered={false}>
            <p>
              {lang === 'ar'
                ? 'يوفر النظام محرك تتبع ثنائي الاتجاه بالكامل (من الخامة الفنية المستوردة إلى المستهلك النهائي في المزارع، والعكس من المنتج التام إلى أرقام اللوتات والموردين).'
                : 'Full bidirectional agrochemical traceability connecting imported raw active lots to farm deliveries and vice versa.'}
            </p>
            <Space direction="horizontal">
              <Button type="primary" onClick={() => onNavigate('traceability')}>
                {t.nav_traceability}
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Recent Batches Table */}
      <Card
        title={lang === 'ar' ? 'أحدث التشغيلات الكيميائية بالمخازن' : 'Recent Chemical Formulation Batches'}
        style={{ marginTop: 20 }}
        bordered={false}
      >
        <Table
          dataSource={recentBatches}
          columns={batchColumns}
          rowKey="id"
          pagination={false}
          loading={loading}
        />
      </Card>
    </div>
  );
};
