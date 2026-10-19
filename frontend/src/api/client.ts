import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response error interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMsg =
      error.response?.data?.error ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred';
    message.error(errorMsg);
    return Promise.reject(error);
  }
);

export const apiClient = {
  // Core
  getProducts: () => api.get('/core/products/'),
  getPartners: () => api.get('/core/partners/'),
  getWarehouses: () => api.get('/core/warehouses/'),

  // Inventory
  getStockBalances: () => api.get('/inventory/balances/'),
  getBatches: () => api.get('/inventory/batches/'),
  releaseBatch: (id: number) => api.post(`/inventory/batches/${id}/release/`),
  holdBatch: (id: number) => api.post(`/inventory/batches/${id}/hold/`),
  rejectBatch: (id: number) => api.post(`/inventory/batches/${id}/reject/`),
  manualAdjustment: (data: any) => api.post('/inventory/movements/manual_adjustment/', data),

  // Manufacturing
  getRecipes: () => api.get('/manufacturing/recipes/'),
  getProductionOrders: () => api.get('/manufacturing/production-orders/'),
  createProductionOrder: (data: any) => api.post('/manufacturing/production-orders/', data),
  releaseProductionOrder: (id: number) => api.post(`/manufacturing/production-orders/${id}/release/`),
  issueMaterial: (orderId: number, data: any) => api.post(`/manufacturing/production-orders/${orderId}/issue_material/`, data),
  completeProduction: (orderId: number, data: any) => api.post(`/manufacturing/production-orders/${orderId}/complete/`, data),

  // Quality
  getQualitySpecifications: () => api.get('/quality/specifications/'),
  getQualityInspections: () => api.get('/quality/inspections/'),
  approveInspection: (id: number, coaNumber?: string) => api.post(`/quality/inspections/${id}/approve_and_release/`, { coa_number: coaNumber }),
  rejectInspection: (id: number, reason: string) => api.post(`/quality/inspections/${id}/reject/`, { reason }),

  // Traceability
  getForwardTrace: (batchId: number) => api.get(`/traceability/forward/${batchId}/`),
  getReverseTrace: (batchId: number) => api.get(`/traceability/reverse/${batchId}/`),
  getRecallExposure: (batchId: number) => api.get(`/traceability/recall-exposure/${batchId}/`),

  // Costing
  getOrderCosting: (orderId: number) => api.get(`/costing/order/${orderId}/`),

  // Accounting
  getJournalEntries: () => api.get('/accounting/journal-entries/'),
  postJournalEntry: (id: number) => api.post(`/accounting/journal-entries/${id}/post_entry/`),
  reverseJournalEntry: (id: number, memo?: string) => api.post(`/accounting/journal-entries/${id}/reverse_entry/`, { memo }),
  getTrialBalance: () => api.get('/accounting/journal-entries/reports/trial-balance/'),
  getProfitLoss: () => api.get('/accounting/journal-entries/reports/profit-loss/'),

  // Sales & Purchasing
  getSalesOrders: () => api.get('/sales/orders/'),
  getSalesInvoices: () => api.get('/sales/invoices/'),
  getARAging: () => api.get('/sales/invoices/reports/ar-aging/'),
  getPurchaseOrders: () => api.get('/purchasing/orders/'),
  getGoodsReceipts: () => api.get('/purchasing/receipts/'),

  // ETA E-Invoicing
  getETADocuments: () => api.get('/tax-egypt/documents/'),
  submitETAInvoice: (invoiceId: number) => api.post('/tax-egypt/documents/submit-invoice/', { invoice_id: invoiceId }),
};

export default api;
