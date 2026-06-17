import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Plus } from 'lucide-react';

interface Invoice {
  id: number;
  client_name: string;
  amount: number;
  issued_date: string;
  hometax_status: string;
}

export const TaxPage: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isIssuing, setIsIssuing] = useState(false);

  const fetchInvoices = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/v1/tax/invoices?company_id=1');
      setInvoices(res.data.invoices);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleIssueInvoice = async () => {
    setIsIssuing(true);
    try {
      await axios.post('http://localhost:8000/api/v1/tax/invoice', {
        company_id: 1,
        sale_id: 999, // dummy
        client_name: "Mock Client Ltd.",
        client_business_number: "123-45-67890",
        amount: 2500000
      });
      await fetchInvoices();
    } catch (err) {
      console.error(err);
    } finally {
      setIsIssuing(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Tax Invoices (Hometax/Popbill)</h1>
        <button
          onClick={handleIssueInvoice}
          disabled={isIssuing}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
        >
          <Plus className="w-4 h-4 mr-2" />
          {isIssuing ? 'Issuing...' : 'Issue New Invoice'}
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issue Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Client</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hometax Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500">No invoices issued yet.</td>
              </tr>
            ) : (
              invoices.map(inv => (
                <tr key={inv.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{inv.issued_date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{inv.client_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(inv.amount)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className="flex items-center text-blue-600 font-medium bg-blue-50 px-2 py-1 rounded-md w-fit">
                      <FileText className="w-4 h-4 mr-1" /> {inv.hometax_status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
