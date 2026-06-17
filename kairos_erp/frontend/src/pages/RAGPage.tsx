import React, { useState } from 'react';
import axios from 'axios';
import { Send, User, Bot, Loader2 } from 'lucide-react';

export const RAGPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<{role: 'user' | 'assistant', content: string}[]>([
    { role: 'assistant', content: '안녕하세요, 대표님. 사내의 모든 재무, 영업 미팅, 이메일 데이터를 바탕으로 경영 전략에 대해 질문해 주세요.' }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!query.trim()) return;

    const userMessage = query;
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setQuery('');
    setIsLoading(true);

    try {
      const res = await axios.post('http://localhost:8000/api/v1/rag/chat', {
        company_id: 1,
        query: userMessage
      });

      setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '데이터 분석 중 오류가 발생했습니다. 다시 시도해 주세요.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto h-[calc(100vh-4rem)] flex flex-col">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">CEO AI Consultant (RAG)</h1>

      <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-100 ml-3' : 'bg-purple-100 mr-3'}`}>
                  {msg.role === 'user' ? <User className="w-5 h-5 text-blue-600" /> : <Bot className="w-5 h-5 text-purple-600" />}
                </div>
                <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-gray-100 text-gray-800 rounded-tl-none'}`}>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex flex-row max-w-[80%]">
                 <div className="w-8 h-8 rounded-full bg-purple-100 mr-3 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-purple-600" />
                </div>
                <div className="p-4 rounded-2xl bg-gray-100 text-gray-800 rounded-tl-none flex items-center">
                  <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
                  <span className="ml-2 text-sm text-gray-500">사내 데이터 검색 및 분석 중...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 bg-gray-50 border-t border-gray-100">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="이번 달 수주 실패 원인을 분석해 줘..."
              className="w-full pl-4 pr-12 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !query.trim()}
              className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
