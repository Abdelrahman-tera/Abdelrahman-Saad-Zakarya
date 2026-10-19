import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Tabs, Space, message } from 'antd';
import { SendOutlined, CheckCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const SalesPurchasingPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [arAging, setArAging] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [invRes, arRes, poRes] = await Promise.all([
        apiClient.getSalesInvoices(),
        apiClient.getARAging(),
        apiClient.getPurchaseOrders(),
      ]);
      setInvoices(invRes.data.results || invRes.data || []);
      setArAging(arRes.data || []);
      setPurchaseOrders(poRes.data.results || poRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmitToETA = async (invoiceId: number) => {
    try {
      const res = await apiClient.submitETAInvoice(invoiceId);
      message.success(lang === 'ar' ? 'تم إرسال الفاتورة لمنظومة الضرائب المصرية واعتمادها بنجاح' : 'Invoice submitted and validated by ETA');
      loadData();
    } catch (err) {}
  };

  const invoiceColumns = [
    {
      title: lang === 'ar' ? 'رقم الفاتورة' : 'Invoice #',
      dataIndex: 'invoice_number',
      key: 'invoice_number',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: lang === 'ar' ? 'العميل' : 'Customer',
      dataIndex: 'customer_name',
      key: 'customer_name',
    },
    {
      title: t.date,
      dataIndex: 'invoice_date',
      key: 'invoice_date',
    },
    {
      title: lang === 'ar' ? 'المبلغ قبل الضريبة' : 'Subtotal',
      dataIndex: 'subtotal',
      key: 'subtotal',
      render: (v: string) => `${Number(v).toFixed(2)} ${t.currency}`,
    },
    {
      title: lang === 'ar' ? 'ضريبة القيمة المضافة 14%' : 'VAT 14%',
      dataIndex: 'vat_amount',
      key: 'vat_amount',
      render: (v: string) => `${Number(v).toFixed(2)} ${t.currency}`,
    },
    {
      title: lang === 'ar' ? 'خصم أرباح تجارية 1%' : 'WHT 1%',
      dataIndex: 'wht_amount',
      key: 'wht_amount',
      render: (v: string) => `${Number(v).toFixed(2)} ${t.currency}`,
    },
    {
      title: t.total,
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (v: string) => <strong>{Number(v).toFixed(2)} {t.currency}</strong>,
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        let color = 'default';
        if (st === 'POSTED') color = 'blue';
        if (st === 'PAID') color = 'green';
        return <Tag color={color}>{st}</Tag>;
      },
    },
    {
      title: t.actions,
      key: 'actions',
      render: (_: any, record: any) => (
        <Space size="small">
          {record.status === 'POSTED' && (
            <Button
              size="small"
              type="primary"
              icon={<SendOutlined />}
              onClick={() => handleSubmitToETA(record.id)}
            >
              {lang === 'ar' ? 'إرسال للضرائب (ETA)' : 'Submit to ETA'}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const arAgingColumns = [
    {
      title: lang === 'ar' ? 'العميل' : 'Customer',
      dataIndex: 'customer_name',
      key: 'customer_name',
      render: (t: string, r: any) => <strong>{t} ({r.customer_code})</strong>,
    },
    {
      title: lang === 'ar' ? 'الحد الائتماني' : 'Credit Limit',
      dataIndex: 'credit_limit',
      key: 'credit_limit',
      render: (v: string) => `${Number(v).toFixed(2)} ${t.currency}`,
    },
    {
      title: lang === 'ar' ? 'جاري (غير مستحق)' : 'Current',
      dataIndex: 'current',
      key: 'current',
      render: (v: string) => Number(v) > 0 ? `${Number(v).toFixed(2)}` : '-',
    },
    {
      title: '1-30 ' + (lang === 'ar' ? 'يوم' : 'Days'),
      dataIndex: 'days_1_30',
      key: 'days_1_30',
      render: (v: string) => Number(v) > 0 ? `${Number(v).toFixed(2)}` : '-',
    },
    {
      title: '31-60 ' + (lang === 'ar' ? 'يوم' : 'Days'),
      dataIndex: 'days_31_60',
      key: 'days_31_60',
      render: (v: string) => Number(v) > 0 ? <Tag color="gold">{Number(v).toFixed(2)}</Tag> : '-',
    },
    {
      title: '61-90 ' + (lang === 'ar' ? 'يوم' : 'Days'),
      dataIndex: 'days_61_90',
      key: 'days_61_90',
      render: (v: string) => Number(v) > 0 ? <Tag color="orange">{Number(v).toFixed(2)}</Tag> : '-',
    },
    {
      title: '+90 ' + (lang === 'ar' ? 'يوم' : 'Days'),
      dataIndex: 'over_90',
      key: 'over_90',
      render: (v: string) => Number(v) > 0 ? <Tag color="red">{Number(v).toFixed(2)}</Tag> : '-',
    },
    {
      title: lang === 'ar' ? 'إجمالي المديونية' : 'Total Outstanding',
      dataIndex: 'total_outstanding',
      key: 'total_outstanding',
      render: (v: string) => <strong>{Number(v).toFixed(2)} {t.currency}</strong>,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_sales_purchases}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'إدارة الفواتير الضريبية، أعمار ديون العملاء (AR Aging)، ومطابقة أوامر الشراء الثلاثية'
              : 'Sales tax invoices, Accounts Receivable aging, and purchasing 3-way matching'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="invoices"
          items={[
            {
              key: 'invoices',
              label: lang === 'ar' ? 'فواتير المبيعات الضريبية (14% VAT + 1% WHT)' : 'Sales Tax Invoices',
              children: (
                <Table
                  dataSource={invoices}
                  columns={invoiceColumns}
                  rowKey="id"
                  loading={loading}
                />
              ),
            },
            {
              key: 'ar_aging',
              label: lang === 'ar' ? 'تقرير أعمار ديون العملاء (AR Aging)' : 'Accounts Receivable Aging',
              children: (
                <Table
                  dataSource={arAging}
                  columns={arAgingColumns}
                  rowKey="customer_id"
                  loading={loading}
                />
              ),
            },
            {
              key: 'purchases',
              label: lang === 'ar' ? 'أوامر الشراء والتوريد (Purchase Orders)' : 'Purchase Orders',
              children: (
                <Table
                  dataSource={purchaseOrders}
                  columns={[
                    { title: lang === 'ar' ? 'رقم أمر الشراء' : 'PO #', dataIndex: 'po_number', key: 'po_number', render: (t: string) => <strong>{t}</strong> },
                    { title: lang === 'ar' ? 'المورد' : 'Supplier', dataIndex: 'supplier_name', key: 'supplier_name' },
                    { title: t.date, dataIndex: 'order_date', key: 'order_date' },
                    { title: t.total, dataIndex: 'total_amount', key: 'total_amount', render: (v: string) => `${Number(v).toFixed(2)} ${t.currency}` },
                    {
                      title: t.status,
                      dataIndex: 'status',
                      key: 'status',
                      render: (st: string) => {
                        let color = 'default';
                        if (st === 'APPROVED') color = 'blue';
                        if (st === 'RECEIVED_FULL') color = 'green';
                        if (st === 'RECEIVED_PARTIAL') color = 'gold';
                        return <Tag color={color}>{st}</Tag>;
                      },
                    },
                  ]}
                  rowKey="id"
                  loading={loading}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};
