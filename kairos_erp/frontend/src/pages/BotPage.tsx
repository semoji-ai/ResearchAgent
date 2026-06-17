import React from 'react';
import { MessageSquare, Link, Copy } from 'lucide-react';

export const BotPage: React.FC = () => {
  const slackWebhookUrl = "http://api.kairos-erp.local/api/v1/bot/slack/webhook";
  const chatWebhookUrl = "http://api.kairos-erp.local/api/v1/bot/chat/webhook";

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Messenger Bot Integration</h1>
      <p className="text-gray-600 mb-8">
        Connect Kairos ERP with your company's communication tools to use natural language scheduling and AI data queries.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Slack Integration */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-[#E01E5A]/10 rounded-lg">
              <MessageSquare className="w-6 h-6 text-[#E01E5A]" />
            </div>
            <h2 className="text-xl font-semibold">Slack Bot</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Paste this Webhook URL into your Slack App Event Subscriptions configuration.
          </p>
          <div className="flex items-center bg-gray-50 rounded-lg border border-gray-200 p-2">
            <code className="flex-1 text-xs text-gray-800 truncate px-2">{slackWebhookUrl}</code>
            <button
              onClick={() => copyToClipboard(slackWebhookUrl)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-200 rounded-md transition-colors"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Google Chat Integration */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-[#00832D]/10 rounded-lg">
              <MessageSquare className="w-6 h-6 text-[#00832D]" />
            </div>
            <h2 className="text-xl font-semibold">Google Chat</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Use this HTTP endpoint URL when configuring your custom Google Chat API bot.
          </p>
          <div className="flex items-center bg-gray-50 rounded-lg border border-gray-200 p-2">
            <code className="flex-1 text-xs text-gray-800 truncate px-2">{chatWebhookUrl}</code>
            <button
              onClick={() => copyToClipboard(chatWebhookUrl)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-200 rounded-md transition-colors"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
