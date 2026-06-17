import React, { useState, useEffect } from 'react';
import { FileUpload } from '../components/FileUpload';
import axios from 'axios';

interface Contact {
  id: number;
  data: {
    name: string;
    email: string;
    company: string;
    phone_number: string;
  };
  synced_to_google: boolean;
}

export const ContactsPage: React.FC = () => {
  const [contacts, setContacts] = useState<Contact[]>([]);

  const fetchContacts = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/v1/contacts/?company_id=1');
      setContacts(res.data.contacts);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchContacts();
  }, []);

  const handleUploadSuccess = () => {
    fetchContacts();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">AI Business Card & Contacts</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-1">
          <FileUpload
            endpoint="/contacts/ocr"
            accept="image/*"
            label="Scan Business Card (OCR)"
            onSuccess={handleUploadSuccess}
          />
        </div>

        <div className="md:col-span-2">
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Synced Contacts</h3>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Google Sync</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {contacts.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500">No contacts synced yet.</td>
                  </tr>
                ) : (
                  contacts.map(contact => (
                    <tr key={contact.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{contact.data.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{contact.data.company}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>{contact.data.phone_number}</div>
                        <div className="text-xs text-gray-400">{contact.data.email}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {contact.synced_to_google ? <span className="text-green-600 font-semibold">Synced</span> : 'Pending'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
