import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function AdminAuthPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    checkStatus();
    
    // Check for success/error in URL params
    const params = new URLSearchParams(window.location.search);
    if (params.get('success')) {
      setTimeout(() => checkStatus(), 1000);
    }
    if (params.get('error')) {
      setError(params.get('error') || 'Authentication failed');
    }
  }, []);

  const checkStatus = async () => {
    try {
      const res = await axios.get('/api/auth/google/status');
      setStatus(res.data);
    } catch (e) {
      console.error('Error checking auth status:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      const res = await axios.get('/api/auth/google/login');
      // Redirect to Google consent
      window.location.href = res.data.authorization_url;
    } catch (e) {
      console.error('Error initiating login:', e);
      setError('Failed to initiate login');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Google Drive Authentication</h1>
      
      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 p-4 rounded">
          <p className="text-red-700">{error}</p>
        </div>
      )}
      
      {status?.authenticated ? (
        <div className="bg-green-100 border border-green-400 p-4 rounded">
          <h2 className="text-xl font-semibold text-green-800 mb-2">✅ Authenticated</h2>
          <p className="text-green-700">
            Drive uploads are using your personal Google account.
          </p>
          <p className="text-sm text-green-600 mt-2">
            Token expires: {new Date(status.expires_at).toLocaleString()}
          </p>
          {status.is_expired && (
            <p className="text-yellow-600 mt-2">
              ⚠️ Token is expired but will auto-refresh on next upload.
            </p>
          )}
          <button
            onClick={checkStatus}
            className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
          >
            Refresh Status
          </button>
        </div>
      ) : (
        <div className="bg-yellow-100 border border-yellow-400 p-4 rounded">
          <h2 className="text-xl font-semibold text-yellow-800 mb-2">⚠️ Not Authenticated</h2>
          <p className="text-yellow-700 mb-4">
            You need to authorize TrickyClip to upload files to your Google Drive.
          </p>
          <button
            onClick={handleLogin}
            className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold"
          >
            Authorize with Google Drive
          </button>
        </div>
      )}
      
      <div className="mt-8 p-4 bg-gray-100 rounded">
        <h3 className="font-semibold mb-2">What this does:</h3>
        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
          <li>Redirects you to Google login page</li>
          <li>You grant TrickyClip access to your Drive</li>
          <li>Clips upload to YOUR Drive quota (no restrictions!)</li>
          <li>Tokens auto-refresh, no need to re-auth</li>
        </ul>
      </div>
      
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded">
        <h3 className="font-semibold text-blue-900 mb-2">Why OAuth?</h3>
        <p className="text-sm text-blue-800">
          Service accounts have zero storage quota on personal Google Drives. 
          By using OAuth with your personal account, clips upload using YOUR quota, 
          which solves the 403 quota errors permanently.
        </p>
      </div>
    </div>
  );
}

