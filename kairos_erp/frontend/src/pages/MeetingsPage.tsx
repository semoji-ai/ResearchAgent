import React, { useState, useEffect } from 'react';
import { FileUpload } from '../components/FileUpload';
import axios from 'axios';

interface Meeting {
  id: number;
  date: string;
  data: {
    client_name: string;
    project_id: string;
    summary: string;
    action_items: string[];
  };
}

export const MeetingsPage: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);

  const fetchMeetings = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/v1/meetings/?company_id=1');
      setMeetings(res.data.meetings);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">AI Meeting Transcripts & Summaries</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-1">
          <FileUpload
            endpoint="/meetings/"
            accept="audio/*,text/plain"
            label="Upload Audio (Pliaud/Device)"
            onSuccess={fetchMeetings}
          />
        </div>

        <div className="md:col-span-2 space-y-4">
          <h3 className="text-lg font-semibold text-gray-800">Recent Meetings</h3>
          {meetings.length === 0 ? (
            <p className="text-gray-500 text-sm bg-white p-4 rounded-xl shadow-sm border border-gray-100">No meeting records yet.</p>
          ) : (
            meetings.map(meeting => (
              <div key={meeting.id} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-bold text-gray-900">{meeting.data.client_name}</h4>
                    <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-md">{meeting.data.project_id}</span>
                  </div>
                  <span className="text-xs text-gray-400">{meeting.date}</span>
                </div>
                <p className="text-sm text-gray-700 mb-4">{meeting.data.summary}</p>
                <div>
                  <h5 className="text-xs font-semibold text-gray-500 uppercase mb-2">Action Items</h5>
                  <ul className="list-disc pl-5 text-sm text-gray-600">
                    {meeting.data.action_items.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
