import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tabs } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const InventoryPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [balances, setBalances] = useState([]);
  const [batches, setBatches] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [isAdjModalOpen, setIsAdjModalOpen] = useState(false);
  const [form] = Form.useForm();

  const loadData = async () => {
    setLoading(true);
    try {
      const [balRes, batchRes, prodRes, whRes] = await Promise.all([
        apiClient.getStockBalances(),
        apiClient.getBatches(),
        apiClient.getProducts(),
        apiClient.getWarehouses(),
      ]);
      setBalances(balRes.data.results || balRes.data || []);
      setBatches(batchRes.data.results || batchRes.data || []);
      setProducts(prodRes.data.results || prodRes.data || []);
      setWarehouses(whRes.data.results || whRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleManualAdjustment = async (values: any) => {
    try {
      await apiClient.manualAdjustment({
        product_id: values.product_id,
        warehouse_id: values.warehouse_id,
        batch_id: values.batch_id || null,
        quantity: values.quantity,
        unit_cost: values.unit_cost,
        source_document: values.source_document || 'ADJ-MANUAL',
        notes: values.notes || 'Manual stock adjustment',
      });
      message.success(lang === 'ar' ? 'تم تسجيل تسوية المخزون وتحديث الأستاذ المستمر بنجاح' : 'Stock adjustment recorded successfully');
      setIsAdjModalOpen(false);
      form.resetFields();
      loadData();
    } catch (err) {
      // Error handled by interceptor
    }
  };

  const balanceColumns = [
    {
      title: lang === 'ar' ? 'كود الصنف' : 'Product Code',
      dataIndex: 'product_code',
      key: 'product_code',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: lang === 'ar' ? 'اسم الصنف / المبيد / السماد' : 'Product Name',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: t.warehouse,
      dataIndex: 'warehouse_name',
      key: 'warehouse_name',
    },
    {
      title: t.batch_number,
      dataIndex: 'batch_number',
      key: 'batch_number',
      render: (text: string) => text ? <Tag color="geekblue">{text}</Tag> : <span style={{ color: '#bfbfbf' }}>-</span>,
    },
    {
      title: t.on_hand,
      dataIndex: 'quantity_on_hand',
      key: 'quantity_on_hand',
      render: (val: string) => Number(val).toFixed(2),
    },
    {
      title: t.available,
      dataIndex: 'quantity_available',
      key: 'quantity_available',
      render: (val: string) => <Tag color={Number(val) > 0 ? 'green' : 'red'}>{Number(val).toFixed(2)}</Tag>,
    },
    {
      title: lang === 'ar' ? 'تكلفة الوحدة (ج.م)' : 'Unit Cost (EGP)',
      dataIndex: 'valuation_unit_cost',
      key: 'valuation_unit_cost',
      render: (val: string) => `${Number(val).toFixed(2)} ${t.currency}`,
    },
  ];

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
      title: lang === 'ar' ? 'لوت المورد الأصلي' : 'Supplier Lot',
      dataIndex: 'supplier_lot_number',
      key: 'supplier_lot_number',
      render: (text: string) => text || '-',
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
        else if (status === 'QUALITY_HOLD') { color = 'orange'; text = lang === 'ar' ? 'موقوف للجودة' : 'QUALITY HOLD'; }
        else if (status === 'REJECTED') { color = 'red'; text = lang === 'ar' ? 'مرفوض' : 'REJECTED'; }
        else if (status === 'EXPIRED') { color = 'magenta'; text = lang === 'ar' ? 'منتهي الصلاحية' : 'EXPIRED'; }
        return <Tag color={color}>{text}</Tag>;
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_inventory}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'دفتر الأستاذ المستمر للمخازن، تتبع اللوتات الكيميائية، وتواريخ الصلاحية (FEFO/FIFO)'
              : 'Perpetual stock ledger, chemical batch balances, and expiry tracking'}
          </span>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            {t.refresh}
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsAdjModalOpen(true)}>
            {lang === 'ar' ? 'تسوية مخزنية يدوية' : 'Stock Adjustment'}
          </Button>
        </Space>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="balances"
          items={[
            {
              key: 'balances',
              label: lang === 'ar' ? 'الأرصدة الحية بالمستودعات' : 'Live Stock Balances',
              children: (
                <Table
                  dataSource={balances}
                  columns={balanceColumns}
                  rowKey="id"
                  loading={loading}
                  pagination={{ pageSize: 15 }}
                />
              ),
            },
            {
              key: 'batches',
              label: lang === 'ar' ? 'سجل اللوتات والتشغيلات الكيميائية' : 'Batch & Lot Registry',
              children: (
                <Table
                  dataSource={batches}
                  columns={batchColumns}
                  rowKey="id"
                  loading={loading}
                  pagination={{ pageSize: 15 }}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Manual Stock Adjustment Modal */}
      <Modal
        title={lang === 'ar' ? 'تسجيل تسوية مخزنية معتمدة' : 'Record Manual Stock Adjustment'}
        open={isAdjModalOpen}
        onCancel={() => setIsAdjModalOpen(false)}
        onOk={() => form.submit()}
        okText={t.save}
        cancelText={t.cancel}
      >
        <Form form={form} layout="vertical" onFinish={handleManualAdjustment}>
          <Form.Item name="product_id" label={lang === 'ar' ? 'الصنف الكيميائي / المنتج' : 'Product'} rules={[{ required: true }]}>
            <Select placeholder={t.search}>
              {products.map((p: any) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.code} - {p.name_ar}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="warehouse_id" label={t.warehouse} rules={[{ required: true }]}>
            <Select placeholder={t.search}>
              {warehouses.map((w: any) => (
                <Select.Option key={w.id} value={w.id}>
                  {w.code} - {w.name_ar}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="batch_id" label={t.batch_number}>
            <Select placeholder={lang === 'ar' ? 'اختياري: اللوت أو التشغيلة' : 'Optional batch'}>
              {batches.map((b: any) => (
                <Select.Option key={b.id} value={b.id}>
                  {b.product_code} - Batch {b.batch_number} [{b.status}]
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="quantity"
            label={lang === 'ar' ? 'الكمية (موجبة للزيادة، سالبة للعجز)' : 'Quantity (positive for gain, negative for loss)'}
            rules={[{ required: true }]}
          >
            <InputNumber style={{ width: '100%' }} precision={4} />
          </Form.Item>

          <Form.Item name="unit_cost" label={lang === 'ar' ? 'تكلفة الوحدة (ج.م)' : 'Unit Cost (EGP)'}>
            <InputNumber style={{ width: '100%' }} precision={2} />
          </Form.Item>

          <Form.Item name="source_document" label={lang === 'ar' ? 'الرقم المرجعي للإذن' : 'Reference Number'}>
            <Input placeholder="ADJ-2026-001" />
          </Form.Item>

          <Form.Item name="notes" label={lang === 'ar' ? 'سبب التسوية' : 'Adjustment Reason'}>
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
