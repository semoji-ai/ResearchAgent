import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ContactsPage } from './pages/ContactsPage';
import { MeetingsPage } from './pages/MeetingsPage';
import { RAGPage } from './pages/RAGPage';
import { MailPage } from './pages/MailPage';
import { BotPage } from './pages/BotPage';
import { FinancePage } from './pages/FinancePage';
import { TaxPage } from './pages/TaxPage';
import { LayoutDashboard, Users, Calendar, Mail, DollarSign, FileText, MessageSquare, Bot } from 'lucide-react';

const Sidebar = () => (
  <div className="w-64 bg-gray-900 h-screen text-white p-6 fixed">
    <h2 className="text-2xl font-bold mb-8 text-blue-400">Kairos ERP</h2>
    <nav className="space-y-4">
      <Link to="/" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <LayoutDashboard className="h-5 w-5" /> <span>Dashboard</span>
      </Link>
      <Link to="/contacts" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <Users className="h-5 w-5" /> <span>AI Contacts (OCR)</span>
      </Link>
      <Link to="/meetings" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <Calendar className="h-5 w-5" /> <span>Meetings Sync</span>
      </Link>
      <Link to="/mail" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <Mail className="h-5 w-5" /> <span>Mail Assistant</span>
      </Link>
      <Link to="/bot" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <Bot className="h-5 w-5" /> <span>Slack / Chat Bot</span>
      </Link>
      <Link to="/finance" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <DollarSign className="h-5 w-5" /> <span>Finance & Sales</span>
      </Link>
      <Link to="/tax" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <FileText className="h-5 w-5" /> <span>Tax Invoices</span>
      </Link>
      <Link to="/rag" className="flex items-center space-x-3 text-gray-300 hover:text-white hover:bg-gray-800 p-2 rounded-lg">
        <MessageSquare className="h-5 w-5" /> <span>CEO AI Consultant</span>
      </Link>
    </nav>
  </div>
);

const Dashboard = () => {
  const queryParams = new URLSearchParams(window.location.search);
  const authSuccess = queryParams.get('auth') === 'success';

  const handleGoogleLogin = () => {
    // Redirect to backend OAuth initiation
    window.location.href = 'http://localhost:8000/api/v1/auth/login/google';
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Welcome to Kairos ERP</h1>
      <p className="text-gray-600 mb-8">Select a module from the sidebar to get started.</p>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 max-w-md">
        <h2 className="text-lg font-semibold mb-2">Connect Integrations</h2>
        <p className="text-sm text-gray-500 mb-6">Connect your Google Workspace to enable Google Drive storage, Contacts Sync, and Gmail Assistant.</p>

        {authSuccess ? (
          <div className="flex items-center text-green-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            Google Workspace Connected
          </div>
        ) : (
          <button
            onClick={handleGoogleLogin}
            className="flex items-center justify-center w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="h-5 w-5 mr-2" />
            Connect Google Workspace
          </button>
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 ml-64 p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/contacts" element={<ContactsPage />} />
            <Route path="/meetings" element={<MeetingsPage />} />
            <Route path="/mail" element={<MailPage />} />
            <Route path="/bot" element={<BotPage />} />
            <Route path="/finance" element={<FinancePage />} />
            <Route path="/tax" element={<TaxPage />} />
            <Route path="/rag" element={<RAGPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
