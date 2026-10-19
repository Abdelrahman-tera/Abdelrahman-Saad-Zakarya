import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Button, Modal, message, Space, Tabs, Row, Col, Statistic, Descriptions } from 'antd';
import { CheckCircleOutlined, RollbackOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';
import { translations, Language } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const AccountingPage: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [loading, setLoading] = useState(false);
  const [journalEntries, setJournalEntries] = useState([]);
  const [trialBalanceData, setTrialBalanceData] = useState<any>(null);
  const [profitLossData, setProfitLossData] = useState<any>(null);

  const [selectedEntry, setSelectedEntry] = useState<any>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [jrnRes, tbRes, plRes] = await Promise.all([
        apiClient.getJournalEntries(),
        apiClient.getTrialBalance(),
        apiClient.getProfitLoss(),
      ]);
      setJournalEntries(jrnRes.data.results || jrnRes.data || []);
      setTrialBalanceData(tbRes.data);
      setProfitLossData(plRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePostEntry = async (id: number) => {
    try {
      await apiClient.postJournalEntry(id);
      message.success(lang === 'ar' ? 'تم ترحيل القيد لدفتر الأستاذ العام بنجاح' : 'Journal entry posted');
      loadData();
    } catch (err) {}
  };

  const handleReverseEntry = async (id: number) => {
    try {
      await apiClient.reverseJournalEntry(id, 'Audit reversal from UI');
      message.success(lang === 'ar' ? 'تم إنشاء قيد عكسي مطابق وإلغاء القيد الأصلي بنجاح' : 'Reversal journal entry posted');
      loadData();
    } catch (err) {}
  };

  const journalColumns = [
    {
      title: lang === 'ar' ? 'رقم القيد' : 'Entry #',
      dataIndex: 'entry_number',
      key: 'entry_number',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: t.date,
      dataIndex: 'entry_date',
      key: 'entry_date',
    },
    {
      title: lang === 'ar' ? 'المستند المرجعي' : 'Reference Doc',
      dataIndex: 'reference_document',
      key: 'reference_document',
      render: (text: string) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: lang === 'ar' ? 'البيان / الشرح' : 'Memo',
      dataIndex: 'memo',
      key: 'memo',
    },
    {
      title: t.debit,
      dataIndex: 'total_debit',
      key: 'total_debit',
      render: (val: string) => `${Number(val).toFixed(2)} ${t.currency}`,
    },
    {
      title: t.credit,
      dataIndex: 'total_credit',
      key: 'total_credit',
      render: (val: string) => `${Number(val).toFixed(2)} ${t.currency}`,
    },
    {
      title: t.status,
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        let color = 'default';
        let label = st;
        if (st === 'POSTED') { color = 'green'; label = lang === 'ar' ? 'مرحل' : 'POSTED'; }
        else if (st === 'DRAFT') { color = 'gold'; label = lang === 'ar' ? 'مسودة' : 'DRAFT'; }
        else if (st === 'REVERSED') { color = 'red'; label = lang === 'ar' ? 'معكوس' : 'REVERSED'; }
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
            icon={<FileTextOutlined />}
            onClick={() => { setSelectedEntry(record); setIsDetailModalOpen(true); }}
          >
            {lang === 'ar' ? 'عرض السطور' : 'Lines'}
          </Button>

          {record.status === 'DRAFT' && (
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => handlePostEntry(record.id)}
            >
              {lang === 'ar' ? 'ترحيل' : 'Post'}
            </Button>
          )}

          {record.status === 'POSTED' && (
            <Button
              size="small"
              danger
              icon={<RollbackOutlined />}
              onClick={() => handleReverseEntry(record.id)}
            >
              {lang === 'ar' ? 'قيد عكسي' : 'Reverse'}
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
          <h2 style={{ margin: 0 }}>{t.nav_accounting}</h2>
          <span style={{ color: '#8c8c8c' }}>
            {lang === 'ar'
              ? 'نظام القيد المزدوج، قيود اليومية المحكمة، ميزان المراجعة، وقائمة الدخل (الأرباح والخسائر)'
              : 'Double-entry general ledger, journal entries, trial balance, and profit & loss statement'}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          {t.refresh}
        </Button>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="journals"
          items={[
            {
              key: 'journals',
              label: lang === 'ar' ? 'قيود اليومية العامة (Journal Entries)' : 'Journal Entries',
              children: (
                <Table
                  dataSource={journalEntries}
                  columns={journalColumns}
                  rowKey="id"
                  loading={loading}
                />
              ),
            },
            {
              key: 'trial_balance',
              label: lang === 'ar' ? 'ميزان المراجعة بالأرصدة (Trial Balance)' : 'Trial Balance',
              children: (
                <div>
                  {trialBalanceData && (
                    <>
                      <Row gutter={16} style={{ marginBottom: 20 }}>
                        <Col span={8}>
                          <Statistic title={lang === 'ar' ? 'إجمالي المدين' : 'Total Debit'} value={trialBalanceData.total_debit} suffix={t.currency} />
                        </Col>
                        <Col span={8}>
                          <Statistic title={lang === 'ar' ? 'إجمالي الدائن' : 'Total Credit'} value={trialBalanceData.total_credit} suffix={t.currency} />
                        </Col>
                        <Col span={8}>
                          <Statistic
                            title={lang === 'ar' ? 'حالة التوازن المحاسبي' : 'Balance Integrity'}
                            value={trialBalanceData.is_balanced ? (lang === 'ar' ? 'متزن ومحكم' : 'BALANCED') : 'UNBALANCED'}
                            valueStyle={{ color: trialBalanceData.is_balanced ? '#52c41a' : '#cf1322' }}
                          />
                        </Col>
                      </Row>

                      <Table
                        dataSource={trialBalanceData.trial_balance || []}
                        columns={[
                          { title: t.code, dataIndex: 'account_code', key: 'account_code', render: (c: string) => <strong>{c}</strong> },
                          { title: lang === 'ar' ? 'اسم الحساب' : 'Account Name', dataIndex: 'account_name_ar', key: 'account_name_ar' },
                          { title: lang === 'ar' ? 'نوع الحساب' : 'Type', dataIndex: 'account_type', key: 'account_type', render: (tp: string) => <Tag color="blue">{tp}</Tag> },
                          { title: t.debit, dataIndex: 'debit', key: 'debit', render: (d: string) => Number(d) > 0 ? `${Number(d).toFixed(2)} ${t.currency}` : '-' },
                          { title: t.credit, dataIndex: 'credit', key: 'credit', render: (c: string) => Number(c) > 0 ? `${Number(c).toFixed(2)} ${t.currency}` : '-' },
                        ]}
                        pagination={false}
                        rowKey="account_code"
                      />
                    </>
                  )}
                </div>
              ),
            },
            {
              key: 'profit_loss',
              label: lang === 'ar' ? 'قائمة الدخل والأرباح والخسائر (P&L)' : 'Profit & Loss Statement',
              children: (
                <div>
                  {profitLossData && (
                    <Row gutter={16}>
                      <Col span={8}>
                        <Card>
                          <Statistic title={lang === 'ar' ? 'إجمالي الإيرادات' : 'Total Revenue'} value={profitLossData.total_revenue} suffix={t.currency} valueStyle={{ color: '#3f8600' }} />
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card>
                          <Statistic title={lang === 'ar' ? 'تكلفة المبيعات والمصروفات' : 'COGS & Expenses'} value={profitLossData.total_expense} suffix={t.currency} valueStyle={{ color: '#cf1322' }} />
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card>
                          <Statistic
                            title={lang === 'ar' ? 'صافي الربح / (الخسارة)' : 'Net Operating Profit'}
                            value={profitLossData.net_profit}
                            suffix={t.currency}
                            valueStyle={{ color: Number(profitLossData.net_profit) >= 0 ? '#3f8600' : '#cf1322', fontWeight: 'bold' }}
                          />
                        </Card>
                      </Col>
                    </Row>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Journal Lines Drill-down Modal */}
      <Modal
        title={lang === 'ar' ? `تفاصيل سطور القيد المحاسبي: ${selectedEntry?.entry_number || ''}` : 'Journal Entry Lines'}
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsDetailModalOpen(false)}>
            {lang === 'ar' ? 'إغلاق' : 'Close'}
          </Button>,
        ]}
        width={750}
      >
        {selectedEntry && (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 20 }}>
              <Descriptions.Item label={t.date}>{selectedEntry.entry_date}</Descriptions.Item>
              <Descriptions.Item label={lang === 'ar' ? 'المستند' : 'Doc'}>{selectedEntry.reference_document || '-'}</Descriptions.Item>
              <Descriptions.Item label={t.debit}>{Number(selectedEntry.total_debit).toFixed(2)} {t.currency}</Descriptions.Item>
              <Descriptions.Item label={t.credit}>{Number(selectedEntry.total_credit).toFixed(2)} {t.currency}</Descriptions.Item>
            </Descriptions>

            <Table
              dataSource={selectedEntry.items || []}
              columns={[
                { title: lang === 'ar' ? 'رقم الحساب' : 'Account #', dataIndex: 'account_code', key: 'account_code' },
                { title: lang === 'ar' ? 'اسم الحساب' : 'Account Name', dataIndex: 'account_name', key: 'account_name' },
                { title: lang === 'ar' ? 'الطرف / الشريك' : 'Partner', dataIndex: 'partner_name', key: 'partner_name', render: (p: string) => p || '-' },
                { title: t.debit, dataIndex: 'debit', key: 'debit', render: (d: string) => Number(d) > 0 ? `${Number(d).toFixed(2)} ${t.currency}` : '-' },
                { title: t.credit, dataIndex: 'credit', key: 'credit', render: (c: string) => Number(c) > 0 ? `${Number(c).toFixed(2)} ${t.currency}` : '-' },
                { title: lang === 'ar' ? 'البيان' : 'Memo', dataIndex: 'memo', key: 'memo' },
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
