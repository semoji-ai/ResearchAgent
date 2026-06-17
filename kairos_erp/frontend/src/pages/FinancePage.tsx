import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DollarSign, Check, AlertCircle } from 'lucide-react';

interface Sale {
  id: number;
  client_name: string;
  amount: number;
  status: string;
  date: string;
}

export const FinancePage: React.FC = () => {
  const [sales, setSales] = useState<Sale[]>([]);

  useEffect(() => {
    const fetchSales = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/v1/finance/sales?company_id=1');
        setSales(res.data.sales);
      } catch (err) {
        console.error(err);
      }
    };
    fetchSales();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Finance & Auto-Sync</h1>
      <p className="text-gray-600 mb-6">
        Pending sales are automatically matched and marked as complete when bank push notifications are received.
      </p>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Client</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sales.map(sale => (
              <tr key={sale.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{sale.date}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{sale.client_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(sale.amount)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {sale.status === 'completed' ? (
                    <span className="flex items-center text-green-600 font-medium bg-green-50 px-2 py-1 rounded-md w-fit">
                      <Check className="w-4 h-4 mr-1" /> Paid
                    </span>
                  ) : (
                    <span className="flex items-center text-yellow-600 font-medium bg-yellow-50 px-2 py-1 rounded-md w-fit">
                      <AlertCircle className="w-4 h-4 mr-1" /> Pending
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
