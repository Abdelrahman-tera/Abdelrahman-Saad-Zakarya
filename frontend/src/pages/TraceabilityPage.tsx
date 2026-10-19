import React, { useEffect, useState } from 'react';
import { Card, Select, Button, Tabs, Table, Tag, Alert, Row, Col, Statistic, Space, Descriptions } from 'antd';
import { SearchOutlined, AlertOutlined, SafetyCertificateOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const TraceabilityPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [batches, setBatches] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);

  const [forwardData, setForwardData] = useState<any>(null);
  const [reverseData, setReverseData] = useState<any>(null);
  const [recallData, setRecallData] = useState<any>(null);

  useEffect(() => {
    loadBatches();
  }, []);

  const loadBatches = async () => {
    try {
      const res = await apiClient.getBatches();
      const list = res.data.results || res.data || [];
      setBatches(list);
      if (list.length > 0 && !selectedBatchId) {
        setSelectedBatchId(list[0].id);
        runTrace(list[0].id);
      }
    } catch (err) {}
  };

  const runTrace = async (batchId: number) => {
    setLoading(true);
    try {
      const [fRes, rRes, recRes] = await Promise.all([
        apiClient.getForwardTrace(batchId),
        apiClient.getReverseTrace(batchId),
        apiClient.getRecallExposure(batchId),
      ]);
      setForwardData(fRes.data);
      setReverseData(rRes.data);
      setRecallData(recRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectBatch = (id: number) => {
    setSelectedBatchId(id);
    runTrace(id);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_traceability}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'محرك التتبع الزراعي الدقيق ثنائي الاتجاه، شجرة الأنساب الكيميائية، وتحليل مخاطر الاستدعاء للتشغيلات'
              : 'Bidirectional batch genealogy, full chemical traceability tree, and market recall risk analysis'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => selectedBatchId && runTrace(selectedBatchId)} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      {/* Batch Selector Bar */}
      <Card style={{ marginBottom: 20 }} bordered={false}>
        <Row gutter={16} align="middle">
          <Col xs={24} md={18}>
            <span style={{ fontWeight: 'bold', marginLeft: 10, marginRight: 10 }}>
              {lang === 'ar' ? 'اختر التشغيلة أو اللوت المطلوب تتبعه:' : 'Select Batch / Lot to Trace:'}
            </span>
            <Select
              style={{ width: '70%' }}
              showSearch
              placeholder={t.search}
              value={selectedBatchId}
              onChange={handleSelectBatch}
              optionFilterProp="children"
            >
              {batches.map((b: any) => (
                <Select.Option key={b.id} value={b.id}>
                  {b.product_code} - {b.product_name} | Batch: {b.batch_number} [{b.status}]
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} md={6} style={{ textAlign: 'end' }}>
            <Button type="primary" icon={<SearchOutlined />} onClick={() => selectedBatchId && runTrace(selectedBatchId)} loading={loading}>
              {lang === 'ar' ? 'تشغيل محرك التتبع' : 'Execute Trace'}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Recall Urgency Alert if delivered to market */}
      {recallData && Number(recallData.total_delivered_to_market) > 0 && (
        <Alert
          type="error"
          showIcon
          icon={<AlertOutlined />}
          message={
            lang === 'ar'
              ? `تنبيه حرج للاستدعاء: تم تسليم كمية (${recallData.total_delivered_to_market}) من هذه التشغيلة للمزارع والموزعين في السوق!`
              : `Critical Market Recall Notice: Quantity of (${recallData.total_delivered_to_market}) from this batch has already been delivered to customers!`
          }
          description={
            lang === 'ar'
              ? `الكمية المتبقية بمستودعات الشركة الواجب حجرها فوراً: ${recallData.total_remaining_in_warehouses}. راجع تبويب تحليل الاستدعاء بالأسفل للتفاصيل.`
              : `Remaining company warehouse stock to quarantine immediately: ${recallData.total_remaining_in_warehouses}. See Recall Analysis tab.`
          }
          style={{ marginBottom: 20 }}
        />
      )}

      {/* Tabs */}
      <Card bordered={false}>
        <Tabs
          defaultActiveKey="forward"
          items={[
            {
              key: 'forward',
              label: t.forward_trace,
              children: (
                <div>
                  {forwardData && (
                    <>
                      <Descriptions bordered size="small" column={3} style={{ marginBottom: 20 }}>
                        <Descriptions.Item label={t.batch_number}>
                          {forwardData.source_raw_batch.batch_number}
                        </Descriptions.Item>
                        <Descriptions.Item label={lang === 'ar' ? 'اسم الخامة / المنتج' : 'Material'}>
                          {forwardData.source_raw_batch.product_name}
                        </Descriptions.Item>
                        <Descriptions.Item label={t.status}>
                          <Tag color="blue">{forwardData.source_raw_batch.status}</Tag>
                        </Descriptions.Item>
                      </Descriptions>

                      <h4>{lang === 'ar' ? '1. أوامر التصنيع والتشغيلات التي استهلكت هذه الخامة:' : '1. Formulation Batches Produced:'}</h4>
                      <Table
                        dataSource={forwardData.production_batches_produced || []}
                        columns={[
                          { title: lang === 'ar' ? 'أمر الإنتاج' : 'MO #', dataIndex: 'production_order_number', key: 'production_order_number' },
                          { title: lang === 'ar' ? 'المنتج التام المصنع' : 'Finished Product', dataIndex: 'formulation_product_name', key: 'formulation_product_name' },
                          { title: lang === 'ar' ? 'الكمية المستهلكة' : 'Consumed Qty', dataIndex: 'quantity_consumed', key: 'quantity_consumed', render: (v: string, r: any) => `${v} ${r.uom}` },
                          { title: lang === 'ar' ? 'رقم تشغيلة المنتج التام' : 'Output Batch #', dataIndex: 'finished_batch_number', key: 'finished_batch_number', render: (t: string) => <Tag color="purple">{t}</Tag> },
                          { title: t.exp_date, dataIndex: 'expiry_date', key: 'expiry_date' },
                        ]}
                        pagination={false}
                        rowKey="production_order_number"
                        style={{ marginBottom: 25 }}
                      />

                      <h4>{lang === 'ar' ? '2. المبيعات والتسليمات للعملاء المتأثرين بهذه التشغيلة:' : '2. Customer Deliveries Affected:'}</h4>
                      <Table
                        dataSource={forwardData.affected_customer_deliveries || []}
                        columns={[
                          { title: lang === 'ar' ? 'إذن التسليم' : 'Delivery #', dataIndex: 'delivery_number', key: 'delivery_number' },
                          { title: t.date, dataIndex: 'delivery_date', key: 'delivery_date' },
                          { title: lang === 'ar' ? 'العميل / الموزع' : 'Customer', dataIndex: 'customer_name_ar', key: 'customer_name_ar' },
                          { title: lang === 'ar' ? 'المحافظة / النطاق' : 'Territory', dataIndex: 'territory', key: 'territory' },
                          { title: lang === 'ar' ? 'هاتف العميل' : 'Phone', dataIndex: 'phone', key: 'phone' },
                          { title: lang === 'ar' ? 'الكمية المسلمة' : 'Delivered Qty', dataIndex: 'quantity_dispatched', key: 'quantity_dispatched', render: (v: string, r: any) => <Tag color="volcano">{v} {r.uom}</Tag> },
                        ]}
                        pagination={false}
                        rowKey="delivery_number"
                      />
                    </>
                  )}
                </div>
              ),
            },
            {
              key: 'reverse',
              label: t.reverse_trace,
              children: (
                <div>
                  {reverseData && (
                    <>
                      <Descriptions bordered size="small" column={3} style={{ marginBottom: 20 }}>
                        <Descriptions.Item label={t.batch_number}>
                          {reverseData.finished_batch.batch_number}
                        </Descriptions.Item>
                        <Descriptions.Item label={lang === 'ar' ? 'المنتج التام' : 'Finished Product'}>
                          {reverseData.finished_batch.product_name}
                        </Descriptions.Item>
                        <Descriptions.Item label={lang === 'ar' ? 'أمر التصنيع' : 'Production Order'}>
                          <Tag color="cyan">{reverseData.production_order_number}</Tag>
                        </Descriptions.Item>
                      </Descriptions>

                      <h4>{lang === 'ar' ? 'المكونات والخامات الكيميائية ومصادر التوريد:' : 'Consumed Raw Materials & Supplier Origins:'}</h4>
                      <Table
                        dataSource={reverseData.consumed_raw_materials || []}
                        columns={[
                          { title: lang === 'ar' ? 'الخامة' : 'Raw Chemical', dataIndex: 'raw_material_name', key: 'raw_material_name' },
                          { title: lang === 'ar' ? 'لوت الخامة' : 'Raw Lot #', dataIndex: 'batch_number', key: 'batch_number', render: (t: string) => <Tag color="blue">{t}</Tag> },
                          { title: lang === 'ar' ? 'الكمية المستهلكة' : 'Qty Consumed', dataIndex: 'quantity_consumed', key: 'quantity_consumed', render: (v: string, r: any) => `${v} ${r.uom}` },
                          {
                            title: lang === 'ar' ? 'المورد الأصلي' : 'Supplier',
                            dataIndex: 'supplier_origin',
                            key: 'supplier_origin',
                            render: (s: any) => s?.supplier_name || 'Stock Buffer',
                          },
                          {
                            title: lang === 'ar' ? 'إذن استلام الوارد (GRN)' : 'GRN #',
                            dataIndex: 'supplier_origin',
                            key: 'grn',
                            render: (s: any) => s?.grn_number ? <Tag color="geekblue">{s.grn_number}</Tag> : '-',
                          },
                        ]}
                        pagination={false}
                        rowKey="batch_number"
                      />
                    </>
                  )}
                </div>
              ),
            },
            {
              key: 'recall',
              label: t.recall_analysis,
              children: (
                <div>
                  {recallData && (
                    <>
                      <Row gutter={16} style={{ marginBottom: 20 }}>
                        <Col span={8}>
                          <Card>
                            <Statistic
                              title={lang === 'ar' ? 'إجمالي الكمية المسلمة للسوق' : 'Total Dispatched to Market'}
                              value={recallData.total_delivered_to_market}
                              valueStyle={{ color: Number(recallData.total_delivered_to_market) > 0 ? '#cf1322' : '#3f8600' }}
                            />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card>
                            <Statistic
                              title={lang === 'ar' ? 'المتبقي بالمستودعات (واجب حجزه)' : 'Remaining in Warehouses (Hold)'}
                              value={recallData.total_remaining_in_warehouses}
                              valueStyle={{ color: '#1890ff' }}
                            />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card>
                            <Statistic
                              title={lang === 'ar' ? 'مستوى الخطورة' : 'Urgency Level'}
                              value={recallData.urgency_level}
                              valueStyle={{ color: recallData.urgency_level === 'HIGH' ? '#cf1322' : '#52c41a' }}
                            />
                          </Card>
                        </Col>
                      </Row>

                      <h4>{lang === 'ar' ? 'قائمة العملاء المطلوب الاتصال بهم وسحب البضاعة:' : 'Actionable Customer Recall Contact List:'}</h4>
                      <Table
                        dataSource={recallData.affected_market_customers || []}
                        columns={[
                          { title: lang === 'ar' ? 'كود العميل' : 'Code', dataIndex: 'customer_code', key: 'customer_code' },
                          { title: lang === 'ar' ? 'اسم العميل / التاجر' : 'Customer Name', dataIndex: 'customer_name', key: 'customer_name' },
                          { title: lang === 'ar' ? 'المحافظة' : 'Territory', dataIndex: 'territory', key: 'territory' },
                          { title: lang === 'ar' ? 'الهاتف' : 'Phone', dataIndex: 'phone', key: 'phone' },
                          { title: lang === 'ar' ? 'إذن التسليم' : 'Delivery Ref', dataIndex: 'delivery_number', key: 'delivery_number' },
                          { title: lang === 'ar' ? 'الكمية المسلمة' : 'Delivered Qty', dataIndex: 'quantity', key: 'quantity', render: (q: string) => <Tag color="red">{q}</Tag> },
                        ]}
                        pagination={false}
                        rowKey="delivery_number"
                      />
                    </>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};
