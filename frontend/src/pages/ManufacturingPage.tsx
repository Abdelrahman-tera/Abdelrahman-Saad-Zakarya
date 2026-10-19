import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tabs, Row, Col, Statistic, Descriptions } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined, ExperimentOutlined, ReloadOutlined, PlusOutlined, LineChartOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const ManufacturingPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [recipes, setRecipes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [batches, setBatches] = useState([]);
  const [products, setProducts] = useState([]);

  // Modals state
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [isCostingModalOpen, setIsCostingModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [costingData, setCostingData] = useState<any>(null);

  const [issueForm] = Form.useForm();
  const [completeForm] = Form.useForm();

  const loadData = async () => {
    setLoading(true);
    try {
      const [recRes, ordRes, batchRes, prodRes] = await Promise.all([
        apiClient.getRecipes(),
        apiClient.getProductionOrders(),
        apiClient.getBatches(),
        apiClient.getProducts(),
      ]);
      setRecipes(recRes.data.results || recRes.data || []);
      setOrders(ordRes.data.results || ordRes.data || []);
      setBatches(batchRes.data.results || batchRes.data || []);
      setProducts(prodRes.data.results || prodRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleReleaseOrder = async (id: number) => {
    try {
      await apiClient.releaseProductionOrder(id);
      message.success(lang === 'ar' ? 'تم اعتماد وتجهيز أمر الإنتاج للصرف والتشغيل' : 'Production order released');
      loadData();
    } catch (err) {}
  };

  const handleIssueMaterial = async (values: any) => {
    try {
      await apiClient.issueMaterial(selectedOrder.id, {
        product_id: values.product_id,
        batch_id: values.batch_id,
        quantity: values.quantity,
      });
      message.success(lang === 'ar' ? 'تم صرف الخامات الكيميائية إلى خط الإنتاج (WIP) وتحديث القيود' : 'Materials issued to WIP');
      setIsIssueModalOpen(false);
      issueForm.resetFields();
      loadData();
    } catch (err) {}
  };

  const handleCompleteProduction = async (values: any) => {
    try {
      await apiClient.completeProduction(selectedOrder.id, {
        actual_output_quantity: values.actual_output,
        scrap_quantity: values.scrap_loss || 0,
        batch_number: values.batch_number,
      });
      message.success(lang === 'ar' ? 'تم إنهاء التشغيلة وإيداع المنتج التام بالحجر الصحي (Quarantine) لحين فحص الجودة' : 'Production completed. Batch in quarantine.');
      setIsCompleteModalOpen(false);
      completeForm.resetFields();
      loadData();
    } catch (err) {}
  };

  const handleViewCosting = async (order: any) => {
    setSelectedOrder(order);
    try {
      const res = await apiClient.getOrderCosting(order.id);
      setCostingData(res.data);
      setIsCostingModalOpen(true);
    } catch (err) {}
  };

  const orderColumns = [
    {
      title: lang === 'ar' ? 'رقم أمر الإنتاج' : 'Order #',
      dataIndex: 'order_number',
      key: 'order_number',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: lang === 'ar' ? 'المنتج / التركيبة' : 'Product / Recipe',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: t.target_qty,
      dataIndex: 'target_quantity',
      key: 'target_quantity',
      render: (val: string, record: any) => `${Number(val).toFixed(2)} ${record.uom_code || ''}`,
    },
    {
      title: t.actual_output,
      dataIndex: 'actual_output_quantity',
      key: 'actual_output_quantity',
      render: (val: string) => Number(val) > 0 ? <Tag color="blue">{Number(val).toFixed(2)}</Tag> : '-',
    },
    {
      title: lang === 'ar' ? 'التشغيلة المنتجة' : 'Finished Batch',
      dataIndex: 'finished_batch_number',
      key: 'finished_batch_number',
      render: (text: string) => text ? <Tag color="purple">{text}</Tag> : '-',
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        let color = 'default';
        let label = st;
        if (st === 'DRAFT') { color = 'default'; label = lang === 'ar' ? 'مسودة' : 'DRAFT'; }
        else if (st === 'RELEASED') { color = 'processing'; label = lang === 'ar' ? 'معتمد للصرف' : 'RELEASED'; }
        else if (st === 'IN_PROGRESS') { color = 'gold'; label = lang === 'ar' ? 'قيد الخلط والتصنيع' : 'IN PROGRESS'; }
        else if (st === 'COMPLETED') { color = 'cyan'; label = lang === 'ar' ? 'مكتمل (بالحجر)' : 'COMPLETED'; }
        else if (st === 'CLOSED') { color = 'green'; label = lang === 'ar' ? 'مغلق ومحسوب التكلفة' : 'CLOSED'; }
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: t.actions,
      key: 'actions',
      render: (_: any, record: any) => (
        <Space size="small">
          {record.status === 'DRAFT' && (
            <Button size="small" type="primary" onClick={() => handleReleaseOrder(record.id)}>
              {lang === 'ar' ? 'اعتماد الأمر' : 'Release'}
            </Button>
          )}

          {(record.status === 'RELEASED' || record.status === 'IN_PROGRESS') && (
            <Button
              size="small"
              icon={<ExperimentOutlined />}
              onClick={() => { setSelectedOrder(record); setIsIssueModalOpen(true); }}
            >
              {t.issue_materials}
            </Button>
          )}

          {(record.status === 'IN_PROGRESS' || record.status === 'RELEASED') && (
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => { setSelectedOrder(record); setIsCompleteModalOpen(true); }}
            >
              {t.complete_order}
            </Button>
          )}

          {record.actual_output_quantity > 0 && (
            <Button size="small" icon={<LineChartOutlined />} onClick={() => handleViewCosting(record)}>
              {lang === 'ar' ? 'تحليل التكلفة' : 'Costing'}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_manufacturing}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'إدارة التركيبات الكيميائية، أوامر الخلط والتصنيع، وصرف الخامات لخطوط التشغيل'
              : 'Formulation recipes, batch execution orders, and material issue to WIP'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="orders"
          items={[
            {
              key: 'orders',
              label: lang === 'ar' ? 'أوامر الخلط والتصنيع الفعلي' : 'Production Batch Orders',
              children: (
                <Table
                  dataSource={orders}
                  columns={orderColumns}
                  rowKey="id"
                  loading={loading}
                />
              ),
            },
            {
              key: 'recipes',
              label: lang === 'ar' ? 'التركيبات وجداول المكونات المعتمدة (BOM)' : 'Approved Formulation Recipes',
              children: (
                <Table
                  dataSource={recipes}
                  columns={[
                    { title: lang === 'ar' ? 'المنتج' : 'Product', dataIndex: 'product_name', key: 'product_name' },
                    { title: lang === 'ar' ? 'اسم التركيبة' : 'Recipe Name', dataIndex: 'name', key: 'name' },
                    { title: lang === 'ar' ? 'الإصدار' : 'Version', dataIndex: 'version', key: 'version', render: (v: string) => <Tag color="blue">{v}</Tag> },
                    { title: lang === 'ar' ? 'حجم الخلطة المرجعي' : 'Ref Batch Size', dataIndex: 'reference_batch_size', key: 'reference_batch_size' },
                    { title: lang === 'ar' ? 'نسبة الإنتاج المتوقعة' : 'Expected Yield', dataIndex: 'expected_yield_percent', key: 'expected_yield_percent', render: (y: string) => `${y}%` },
                    { title: t.status, dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'APPROVED' ? 'green' : 'orange'}>{s}</Tag> },
                  ]}
                  rowKey="id"
                  loading={loading}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Material Issue Modal */}
      <Modal
        title={lang === 'ar' ? `صرف خامات كيميائية لأمر الإنتاج: ${selectedOrder?.order_number || ''}` : 'Issue Raw Materials to WIP'}
        open={isIssueModalOpen}
        onCancel={() => setIsIssueModalOpen(false)}
        onOk={() => issueForm.submit()}
        okText={t.save}
        cancelText={t.cancel}
      >
        <Form form={issueForm} layout="vertical" onFinish={handleIssueMaterial}>
          <Form.Item name="product_id" label={lang === 'ar' ? 'الخامة / المادة الفعالة / المذيب' : 'Raw Chemical'} rules={[{ required: true }]}>
            <Select placeholder={t.search}>
              {products.map((p: any) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.code} - {p.name_ar}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="batch_id" label={lang === 'ar' ? 'لوت الخامة المعتمد بالمستودع' : 'Approved Raw Material Batch'} rules={[{ required: true }]}>
            <Select placeholder={t.search}>
              {batches
                .filter((b: any) => b.status === 'RELEASED')
                .map((b: any) => (
                  <Select.Option key={b.id} value={b.id}>
                    {b.product_code} - Batch {b.batch_number} (Exp: {b.expiry_date})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item name="quantity" label={lang === 'ar' ? 'الكمية المصروفة فعلياً للخلط' : 'Actual Issued Quantity'} rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} precision={4} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Complete Production Modal */}
      <Modal
        title={lang === 'ar' ? `إنهاء وتعبئة التشغيلة: ${selectedOrder?.order_number || ''}` : 'Complete Batch Formulation'}
        open={isCompleteModalOpen}
        onCancel={() => setIsCompleteModalOpen(false)}
        onOk={() => completeForm.submit()}
        okText={t.complete_order}
        cancelText={t.cancel}
      >
        <Form form={completeForm} layout="vertical" onFinish={handleCompleteProduction}>
          <Form.Item name="actual_output" label={t.actual_output} rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} precision={4} placeholder="e.g. 980" />
          </Form.Item>

          <Form.Item name="scrap_loss" label={t.scrap_loss}>
            <InputNumber style={{ width: '100%' }} precision={4} placeholder="e.g. 20" />
          </Form.Item>

          <Form.Item name="batch_number" label={t.batch_number} rules={[{ required: true }]}>
            <Input placeholder="BATCH-PYRI-2026-001" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Costing & Variance Modal */}
      <Modal
        title={lang === 'ar' ? `تحليل التكلفة والانحرافات لأمر الإنتاج: ${selectedOrder?.order_number || ''}` : 'Batch Costing & Variance Analysis'}
        open={isCostingModalOpen}
        onCancel={() => setIsCostingModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsCostingModalOpen(false)}>
            {lang === 'ar' ? 'إغلاق' : 'Close'}
          </Button>,
        ]}
        width={800}
      >
        {costingData && (
          <div>
            <Row gutter={16} style={{ marginBottom: 20 }}>
              <Col span={6}>
                <Statistic title={lang === 'ar' ? 'التكلفة المعيارية' : 'Planned Cost'} value={costingData.total_planned_cost} suffix={t.currency} />
              </Col>
              <Col span={6}>
                <Statistic title={lang === 'ar' ? 'التكلفة الفعلية' : 'Actual Cost'} value={costingData.total_actual_cost} suffix={t.currency} />
              </Col>
              <Col span={6}>
                <Statistic
                  title={lang === 'ar' ? 'صافي الانحراف' : 'Net Variance'}
                  value={costingData.net_variance}
                  suffix={t.currency}
                  valueStyle={{ color: Number(costingData.net_variance) > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic title={lang === 'ar' ? 'تكلفة اللتر/الوحدة الفعلي' : 'Actual Unit Cost'} value={costingData.actual_cost_per_unit} suffix={t.currency} />
              </Col>
            </Row>

            <Table
              dataSource={costingData.material_breakdown || []}
              columns={[
                { title: lang === 'ar' ? 'الخامة' : 'Material', dataIndex: 'product_name', key: 'product_name' },
                { title: lang === 'ar' ? 'المخطط' : 'Planned Qty', dataIndex: 'planned_quantity', key: 'planned_quantity' },
                { title: lang === 'ar' ? 'الفعلي' : 'Actual Qty', dataIndex: 'actual_quantity', key: 'actual_quantity' },
                {
                  title: lang === 'ar' ? 'انحراف الكمية (MUV)' : 'Usage Variance',
                  dataIndex: 'usage_variance',
                  key: 'usage_variance',
                  render: (val: string, r: any) => <Tag color={r.usage_status === 'FAVORABLE' ? 'green' : 'red'}>{val} {t.currency}</Tag>,
                },
                {
                  title: lang === 'ar' ? 'انحراف السعر (MPV)' : 'Price Variance',
                  dataIndex: 'price_variance',
                  key: 'price_variance',
                  render: (val: string, r: any) => <Tag color={r.price_status === 'FAVORABLE' ? 'green' : 'red'}>{val} {t.currency}</Tag>,
                },
              ]}
              pagination={false}
              rowKey="product_code"
            />
          </div>
        )}
      </Modal>
    </div>
  );
};
