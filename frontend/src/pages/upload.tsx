import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

interface UploadProgress {
  filename: string;
  progress: number;
  status: string;
  fileId?: string;
  jobId?: string;
  error?: string;
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);

  const updateProgress = (index: number, updates: Partial<UploadProgress>) => {
    setUploadProgress(prev => {
      const updated = [...prev];
      if (updated[index]) {
        updated[index] = { ...updated[index], ...updates };
      }
      return updated;
    });
  };

  const uploadSingleFile = async (file: File, index: number) => {
    try {
      updateProgress(index, { status: 'uploading', progress: 5 });
      
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.min(90, Math.round((progressEvent.loaded * 90) / progressEvent.total));
            updateProgress(index, { progress: percent, status: 'uploading' });
          }
        }
      });

      updateProgress(index, { 
        progress: 95, 
        status: 'processing',
        fileId: response.data.id 
      });

      // wait a moment
      await new Promise(resolve => setTimeout(resolve, 300));
      
      updateProgress(index, { 
        progress: 100,
        status: 'complete',
        fileId: response.data.id
      });
      
    } catch (error: any) {
      console.error('upload error:', error);
      updateProgress(index, { 
        status: 'error',
        progress: 0,
        error: error.response?.data?.detail || error.message || 'upload failed'
      });
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files || files.length === 0) return;

    setUploading(true);
    
    // initialize progress tracking
    const initialProgress: UploadProgress[] = Array.from(files).map(f => ({
      filename: f.name,
      progress: 0,
      status: 'pending'
    }));
    setUploadProgress(initialProgress);

    // upload all files concurrently
    const uploadPromises = Array.from(files).map((file, index) => 
      uploadSingleFile(file, index)
    );

    await Promise.allSettled(uploadPromises);
    setUploading(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'processing': return 'bg-yellow-500';
      case 'uploading': return 'bg-blue-500';
      default: return 'bg-gray-400';
    }
  };

  const completedCount = uploadProgress.filter(p => p.status === 'complete').length;
  const errorCount = uploadProgress.filter(p => p.status === 'error').length;

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h2 className="text-3xl font-bold mb-2">upload raw videos</h2>
        <p className="text-gray-600 mb-6">
          upload multiple videos - they'll process automatically in the background
        </p>
        
        <form onSubmit={handleUpload}>
          <div className="mb-6">
            <label className="block w-full cursor-pointer">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-400 hover:bg-blue-50 transition">
                {files && files.length > 0 ? (
                  <div>
                    <div className="text-2xl mb-2">📹</div>
                    <div className="font-semibold text-lg">{files.length} file(s) selected</div>
                    <div className="text-sm text-gray-500 mt-2">
                      {Array.from(files).map(f => f.name).join(', ').substring(0, 100)}...
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="text-4xl mb-3">📁</div>
                    <div className="text-xl font-semibold mb-2">drop videos here</div>
                    <div className="text-gray-500">or click to browse</div>
                    <div className="text-xs text-gray-400 mt-2">supports 100GB+ files</div>
                  </div>
                )}
              </div>
              <input
                type="file"
                multiple
                accept="video/*"
                onChange={(e) => setFiles(e.target.files)}
                className="hidden"
              />
            </label>
          </div>
          
          <button
            type="submit"
            disabled={!files || uploading}
            className="w-full bg-blue-600 text-white py-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-lg transition"
          >
            {uploading ? `uploading... (${completedCount}/${uploadProgress.length})` : 'start upload'}
          </button>
        </form>

        {/* progress section */}
        {uploadProgress.length > 0 && (
          <div className="mt-8">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">upload progress</h3>
              {completedCount > 0 && (
                <div className="text-sm">
                  <span className="text-green-600 font-semibold">{completedCount} complete</span>
                  {errorCount > 0 && <span className="text-red-600 font-semibold ml-3">{errorCount} errors</span>}
                </div>
              )}
            </div>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {uploadProgress.map((item, idx) => (
                <div key={idx} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold truncate">{item.filename}</div>
                      <div className="text-xs text-gray-500 mt-1 capitalize">{item.status}</div>
                    </div>
                    <div className="text-sm font-semibold ml-4">
                      {item.progress}%
                    </div>
                  </div>
                  
                  <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                    <div 
                      className={`h-3 rounded-full transition-all ${getStatusColor(item.status)}`}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                  
                  {item.error && (
                    <div className="text-xs text-red-600 mt-2 bg-red-50 p-2 rounded">
                      {item.error}
                    </div>
                  )}
                  
                  {item.fileId && item.status === 'complete' && (
                    <div className="mt-2 flex gap-2">
                      <Link
                        to="/jobs"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        view processing →
                      </Link>
                      <Link
                        to="/sort"
                        className="text-xs text-green-600 hover:underline"
                      >
                        start sorting →
                      </Link>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {completedCount === uploadProgress.length && completedCount > 0 && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg text-center">
                <div className="text-green-800 font-semibold mb-2">
                  🎉 all uploads complete!
                </div>
                <div className="text-sm text-green-700 mb-3">
                  videos are being analyzed in the background
                </div>
                <div className="flex gap-3 justify-center">
                  <Link
                    to="/jobs"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                  >
                    monitor progress
                  </Link>
                  <Link
                    to="/sort"
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
                  >
                    start sorting
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
