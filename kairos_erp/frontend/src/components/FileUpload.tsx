import React, { useState, useRef } from 'react';
import { Upload, X, File, CheckCircle } from 'lucide-react';
import axios from 'axios';

interface FileUploadProps {
  endpoint: string; // The backend API endpoint to send the file to
  accept?: string;  // e.g., 'image/*,audio/*'
  onSuccess?: (data: any) => void;
  label?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({ endpoint, accept = "*", onSuccess, label = "Upload File" }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
      setSuccessMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    // Simulating a company_id for the MVP
    formData.append('company_id', '1');

    try {
      const response = await axios.post(`http://localhost:8000/api/v1${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setSuccessMsg('Upload successful! Action triggered.');
      if (onSuccess) {
        onSuccess(response.data);
      }
      // Reset file after successful upload
      setTimeout(() => setFile(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full max-w-md p-6 bg-white rounded-xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold mb-4 text-gray-800">{label}</h3>

      {!file ? (
        <div
          onClick={triggerFileInput}
          className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-50 transition-colors"
        >
          <Upload className="mx-auto h-12 w-12 text-blue-500 mb-3" />
          <p className="text-sm text-gray-600">Tap to select a file from your device</p>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept={accept}
            className="hidden"
          />
        </div>
      ) : (
        <div className="bg-gray-50 p-4 rounded-lg flex items-center justify-between border border-gray-200">
          <div className="flex items-center space-x-3 overflow-hidden">
            <File className="h-6 w-6 text-blue-500 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-700 truncate">{file.name}</span>
          </div>
          {!isUploading && !successMsg && (
            <button onClick={() => setFile(null)} className="text-gray-400 hover:text-red-500">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
      {successMsg && (
        <div className="mt-3 flex items-center text-sm text-green-600">
          <CheckCircle className="h-4 w-4 mr-1" />
          {successMsg}
        </div>
      )}

      {file && !successMsg && (
        <button
          onClick={handleUpload}
          disabled={isUploading}
          className={`mt-4 w-full py-2.5 rounded-lg text-white font-medium transition-colors ${
            isUploading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isUploading ? 'Processing...' : 'Upload & Process'}
        </button>
      )}
    </div>
  );
};
