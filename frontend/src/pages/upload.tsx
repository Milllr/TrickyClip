import React, { useState } from 'react';
import axios from 'axios';

export default function UploadPage() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files || files.length === 0) return;

    setUploading(true);
    setMessage('');

    try {
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);

        await axios.post('/api/upload/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }
      setMessage(`Successfully uploaded ${files.length} files.`);
      setFiles(null);
    } catch (err) {
      console.error(err);
      setMessage('Error uploading files.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 bg-white p-6 rounded shadow">
      <h2 className="text-2xl font-bold mb-4">Upload Raw Videos</h2>
      <form onSubmit={handleUpload}>
        <div className="mb-4">
          <input
            type="file"
            multiple
            accept="video/*"
            onChange={(e) => setFiles(e.target.files)}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
          />
        </div>
        <button
          type="submit"
          disabled={!files || uploading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
      {message && <div className="mt-4 text-center">{message}</div>}
    </div>
  );
}

