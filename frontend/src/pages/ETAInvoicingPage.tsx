import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Modal, Space, Descriptions, Alert } from 'antd';
import { CheckCircleOutlined, EyeOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const ETAInvoicingPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getETADocuments();
      setDocuments(res.data.results || res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const columns = [
    {
      title: lang === 'ar' ? 'رقم الفاتورة الداخلية' : 'Internal Invoice #',
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
      title: lang === 'ar' ? 'الرقم التعريفي الموحد (ETA UUID)' : 'ETA UUID',
      dataIndex: 'eta_uuid',
      key: 'eta_uuid',
      render: (u: string) => <Tag color="geekblue">{u}</Tag>,
    },
    {
      title: lang === 'ar' ? 'رقم حزمة الإرسال' : 'Submission ID',
      dataIndex: 'submission_id',
      key: 'submission_id',
      render: (s: string) => s || '-',
    },
    {
      title: lang === 'ar' ? 'تاريخ الإرسال' : 'Submission Date',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      render: (d: string) => d ? new Date(d).toLocaleString(lang === 'ar' ? 'ar-EG' : 'en-US') : '-',
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        let color = 'default';
        let label = st;
        if (st === 'VALID') { color = 'green'; label = lang === 'ar' ? 'معتمدة وصحيحة' : 'VALID'; }
        else if (st === 'SUBMITTED') { color = 'gold'; label = lang === 'ar' ? 'قيد المعالجة' : 'SUBMITTED'; }
        else if (st === 'INVALID') { color = 'red'; label = lang === 'ar' ? 'خطأ بالتحقق' : 'INVALID'; }
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: t.actions,
      key: 'actions',
      render: (_: any, record: any) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => { setSelectedDoc(record); setIsModalOpen(true); }}
        >
          {lang === 'ar' ? 'عرض تفاصيل الـ JSON' : 'View Payload'}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0 }}>{t.nav_eta}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'منظومة الفاتورة والإيصال الإلكتروني لمصلحة الضرائب المصرية (ETA API v1.0)'
              : 'Egyptian Tax Authority (ETA) E-Invoicing & E-Receipt System Integration'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      <Alert
        message={
          lang === 'ar'
            ? 'الربط متوافق مع النشاط الضريبي 2012 (صناعة وتعبئة الكيماويات والأسمدة) ورقم التسجيل الضريبي 100-200-300'
            : 'Configured for Taxpayer Activity Code 2012 (Chemical & Fertilizer Manufacturing) with Tax ID 100-200-300'
        }
        type="info"
        showIcon
        icon={<SafetyCertificateOutlined />}
        style={{ marginBottom: 20 }}
      />

      <Card bordered={false}>
        <Table
          dataSource={documents}
          columns={columns}
          rowKey="id"
          loading={loading}
        />
      </Card>

      {/* JSON Payload Drill-down Modal */}
      <Modal
        title={lang === 'ar' ? `تفاصيل الفاتورة الإلكترونية المعتمدة: ${selectedDoc?.invoice_number || ''}` : 'ETA Canonical Document Payload'}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsModalOpen(false)}>
            {lang === 'ar' ? 'إغلاق' : 'Close'}
          </Button>,
        ]}
        width={800}
      >
        {selectedDoc && (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 15 }}>
              <Descriptions.Item label="ETA UUID">{selectedDoc.eta_uuid}</Descriptions.Item>
              <Descriptions.Item label="Submission ID">{selectedDoc.submission_id || '-'}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={selectedDoc.status === 'VALID' ? 'green' : 'blue'}>{selectedDoc.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="SHA-256 Hash">
                <span style={{ fontSize: 11, fontFamily: 'monospace' }}>{selectedDoc.document_hash}</span>
              </Descriptions.Item>
            </Descriptions>

            <h4>{lang === 'ar' ? 'الـ Payload القياسي الصادر لمنظومة الضرائب المصرية:' : 'ETA v1.0 Canonical JSON:'}</h4>
            <pre
              style={{
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
                padding: 12,
                borderRadius: 6,
                maxHeight: 350,
                overflowY: 'auto',
                fontSize: 12,
                direction: 'ltr',
              }}
            >
              {JSON.stringify(selectedDoc.raw_payload || {}, null, 2)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  );
};
