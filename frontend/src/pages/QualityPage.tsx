import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Modal, Form, Input, InputNumber, message, Space, Descriptions } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined, FileDoneOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const QualityPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [inspections, setInspections] = useState([]);
  const [selectedInspection, setSelectedInspection] = useState<any>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getQualityInspections();
      setInspections(res.data.results || res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (inspection: any) => {
    try {
      await apiClient.approveInspection(inspection.id, `COA-${inspection.batch_number}`);
      message.success(lang === 'ar' ? 'تم اعتماد التحليل الكيميائي وإصدار شهادة التحليل (COA) والإفراج عن التشغيلة' : 'Batch released and COA issued');
      loadData();
      setIsDetailModalOpen(false);
    } catch (err) {}
  };

  const handleReject = async (inspection: any) => {
    try {
      await apiClient.rejectInspection(inspection.id, 'Non-conforming chemical assay');
      message.warning(lang === 'ar' ? 'تم رفض التشغيلة وقفلها في المخازن لمنع صرفها نهائياً' : 'Batch rejected and locked');
      loadData();
      setIsDetailModalOpen(false);
    } catch (err) {}
  };

  const columns = [
    {
      title: lang === 'ar' ? 'رقم إذن الفحص' : 'Inspection #',
      dataIndex: 'inspection_number',
      key: 'inspection_number',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: lang === 'ar' ? 'المنتج / الخامة' : 'Product',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: t.batch_number,
      dataIndex: 'batch_number',
      key: 'batch_number',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: lang === 'ar' ? 'حالة التشغيلة بالمخزن' : 'Batch Status',
      dataIndex: 'batch_status',
      key: 'batch_status',
      render: (st: string) => {
        let color = 'gold';
        if (st === 'RELEASED') color = 'green';
        if (st === 'REJECTED') color = 'red';
        return <Tag color={color}>{st}</Tag>;
      },
    },
    {
      title: t.coa,
      dataIndex: 'coa_number',
      key: 'coa_number',
      render: (text: string) => text ? <Tag color="green">{text}</Tag> : <span style={{ color: '#bfbfbf' }}>-</span>,
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        let color = 'default';
        let label = st;
        if (st === 'APPROVED') { color = 'green'; label = lang === 'ar' ? 'معتمد ومطابق' : 'APPROVED'; }
        else if (st === 'PENDING') { color = 'gold'; label = lang === 'ar' ? 'قيد الفحص' : 'PENDING'; }
        else if (st === 'REJECTED') { color = 'red'; label = lang === 'ar' ? 'مرفوض' : 'REJECTED'; }
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: t.actions,
      key: 'actions',
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            size="small"
            icon={<FileDoneOutlined />}
            onClick={() => { setSelectedInspection(record); setIsDetailModalOpen(true); }}
          >
            {lang === 'ar' ? 'نتائج التحليل' : 'Test Results'}
          </Button>

          {record.status !== 'APPROVED' && record.status !== 'REJECTED' && (
            <>
              <Button
                size="small"
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApprove(record)}
              >
                {t.approve_release}
              </Button>
              <Button
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleReject(record)}
              >
                {t.reject}
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_quality}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'مواصفات الفحص الكيميائي، تسجيل نتائج المعامل، وإصدار شهادات التحليل (COA) للإفراج عن المخزون'
              : 'Chemical quality specifications, laboratory assay testing, and Certificate of Analysis release'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      <Card bordered={false}>
        <Table
          dataSource={inspections}
          columns={columns}
          rowKey="id"
          loading={loading}
        />
      </Card>

      {/* Test Results & COA Modal */}
      <Modal
        title={lang === 'ar' ? `نتائج الفحص الكيميائي: ${selectedInspection?.inspection_number || ''}` : 'Inspection Results & Parameters'}
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsDetailModalOpen(false)}>
            {lang === 'ar' ? 'إغلاق' : 'Close'}
          </Button>,
          selectedInspection?.status !== 'APPROVED' && selectedInspection?.status !== 'REJECTED' && (
            <Button key="approve" type="primary" icon={<CheckCircleOutlined />} onClick={() => handleApprove(selectedInspection)}>
              {t.approve_release}
            </Button>
          ),
        ]}
        width={750}
      >
        {selectedInspection && (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 20 }}>
              <Descriptions.Item label={lang === 'ar' ? 'المنتج' : 'Product'}>
                {selectedInspection.product_name} ({selectedInspection.product_code})
              </Descriptions.Item>
              <Descriptions.Item label={t.batch_number}>
                {selectedInspection.batch_number}
              </Descriptions.Item>
              <Descriptions.Item label={t.date}>
                {selectedInspection.inspection_date}
              </Descriptions.Item>
              <Descriptions.Item label={t.status}>
                <Tag color={selectedInspection.status === 'APPROVED' ? 'green' : 'gold'}>{selectedInspection.status}</Tag>
              </Descriptions.Item>
            </Descriptions>

            <h4>{lang === 'ar' ? 'القياسات المعملية ومطابقة الحدود المسموحة:' : 'Laboratory Measurements & Tolerances:'}</h4>
            <Table
              dataSource={selectedInspection.results || []}
              columns={[
                { title: lang === 'ar' ? 'الخاصية / العنصر الكيميائي' : 'Parameter', dataIndex: 'parameter_name', key: 'parameter_name' },
                {
                  title: lang === 'ar' ? 'الحد الأدنى' : 'Min Limit',
                  dataIndex: 'min_value',
                  key: 'min_value',
                  render: (v: string, r: any) => v ? `${v} ${r.unit_of_measure || ''}` : '-',
                },
                {
                  title: lang === 'ar' ? 'الحد الأقصى' : 'Max Limit',
                  dataIndex: 'max_value',
                  key: 'max_value',
                  render: (v: string, r: any) => v ? `${v} ${r.unit_of_measure || ''}` : '-',
                },
                {
                  title: lang === 'ar' ? 'القيمة الفعلية المقاسة' : 'Observed Value',
                  dataIndex: 'observed_value_numeric',
                  key: 'observed_value_numeric',
                  render: (v: string, r: any) => <strong>{v || r.observed_value_text} {r.unit_of_measure || ''}</strong>,
                },
                {
                  title: lang === 'ar' ? 'النتيجة' : 'Conformance',
                  dataIndex: 'is_conforming',
                  key: 'is_conforming',
                  render: (conf: boolean) => conf ? <Tag color="green">{lang === 'ar' ? 'مطابق' : 'PASS'}</Tag> : <Tag color="red">{lang === 'ar' ? 'غير مطابق' : 'FAIL'}</Tag>,
                },
              ]}
              pagination={false}
              rowKey="id"
            />
          </div>
        )}
      </Modal>
    </div>
  );
};
