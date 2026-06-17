import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Mail, CheckCircle, XCircle } from 'lucide-react';

interface Draft {
  id: number;
  original_subject: string;
  sender: string;
  category: string;
  draft_reply: string;
  status: string;
}

export const MailPage: React.FC = () => {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [isScanning, setIsScanning] = useState(false);

  const fetchDrafts = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/v1/mail-assistant/drafts?company_id=1');
      setDrafts(res.data.drafts);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, []);

  const handleScan = async () => {
    setIsScanning(true);
    try {
      await axios.post('http://localhost:8000/api/v1/mail-assistant/scan?company_id=1');
      await fetchDrafts();
    } catch (err) {
      console.error(err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleAction = async (id: number, action: string) => {
    try {
      await axios.post(`http://localhost:8000/api/v1/mail-assistant/drafts/${id}/action`, { action });
      await fetchDrafts();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">AI Mail Assistant</h1>
        <button
          onClick={handleScan}
          disabled={isScanning}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
        >
          <Mail className="w-5 h-5 mr-2" />
          {isScanning ? 'Scanning...' : 'Scan Inbox'}
        </button>
      </div>

      <div className="space-y-4">
        {drafts.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No AI drafts generated yet.</p>
        ) : (
          drafts.map(draft => (
            <div key={draft.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-lg">{draft.original_subject}</h3>
                  <p className="text-sm text-gray-500">From: {draft.sender}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  draft.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  draft.status === 'sent' ? 'bg-green-100 text-green-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {draft.status.toUpperCase()}
                </span>
              </div>

              <div className="mb-4">
                <span className="inline-block bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded mb-2">
                  의도 분류: {draft.category}
                </span>
                <div className="bg-gray-50 p-4 rounded-lg text-sm text-gray-700 whitespace-pre-wrap">
                  {draft.draft_reply}
                </div>
              </div>

              {draft.status === 'pending' && (
                <div className="flex space-x-3">
                  <button
                    onClick={() => handleAction(draft.id, 'approve')}
                    className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve & Send
                  </button>
                  <button
                    onClick={() => handleAction(draft.id, 'reject')}
                    className="flex items-center px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-sm font-medium"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
