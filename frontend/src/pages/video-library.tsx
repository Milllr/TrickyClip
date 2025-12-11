import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

interface VideoInfo {
  id: string;
  filename: string;
  uploaded_at: string;
  recorded_at: string;
  duration_ms: number;
  resolution: string;
  fps: number;
  camera_id: string;
  segments: {
    total: number;
    unreviewed: number;
    accepted: number;
    trashed: number;
  };
  progress_percent: number;
  processing_status: string;
}

export default function VideoLibraryPage() {
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const res = await axios.get('/api/videos/library');
      setVideos(res.data);
    } catch (e) {
      console.error('Error fetching videos:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleManualSync = async () => {
    setSyncing(true);
    try {
      const res = await axios.post('/api/admin/sync-from-drive');
      console.log('Sync result:', res.data);
      
      const jobsQueued = res.data.jobs_queued?.length || 0;
      alert(`Sync complete! ${jobsQueued} new videos queued for processing`);
      
      // Refresh video list after a short delay
      setTimeout(() => {
        fetchVideos();
      }, 2000);
    } catch (e) {
      console.error('Sync failed:', e);
      alert('Sync failed - check console');
    } finally {
      setSyncing(false);
    }
  };

  const handleVideoClick = async (videoId: string) => {
    // Navigate to sort page with first unreviewed segment from this video
    try {
      const segments = await axios.get(`/api/sort/segments/${videoId}`);
      const firstUnreviewed = segments.data.find((s: any) => s.status === 'UNREVIEWED');
      if (firstUnreviewed) {
        navigate(`/sort?segment=${firstUnreviewed.segment_id}`);
      }
    } catch (e) {
      console.error('Error loading segment:', e);
    }
  };

  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading videos...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">Video Library</h1>
          <p className="text-gray-600">
            {videos.length} videos with unreviewed clips
          </p>
        </div>
        
        {/* Manual Sync Button */}
        <button
          onClick={handleManualSync}
          disabled={syncing}
          className={`px-6 py-3 rounded font-semibold text-white flex items-center gap-2 ${
            syncing 
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {syncing ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Syncing...
            </>
          ) : (
            <>
              🔄 Sync from Drive
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {videos.map((video) => (
          <div
            key={video.id}
            onClick={() => handleVideoClick(video.id)}
            className="bg-white rounded-lg shadow hover:shadow-lg transition cursor-pointer p-4 border-2 border-gray-200 hover:border-blue-400"
          >
            {/* Header */}
            <div className="mb-3">
              <h3 className="font-semibold text-lg truncate" title={video.filename}>
                {video.filename}
              </h3>
              <p className="text-sm text-gray-500">
                {new Date(video.recorded_at || video.uploaded_at).toLocaleDateString()}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="mb-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600">Progress</span>
                <span className="font-semibold">{video.progress_percent}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all"
                  style={{ width: `${video.progress_percent}%` }}
                />
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 text-sm mb-3">
              <div>
                <span className="text-gray-600">Duration:</span>
                <span className="ml-1 font-semibold">{formatDuration(video.duration_ms)}</span>
              </div>
              <div>
                <span className="text-gray-600">FPS:</span>
                <span className="ml-1 font-semibold">{video.fps}</span>
              </div>
              <div>
                <span className="text-gray-600">Resolution:</span>
                <span className="ml-1 font-semibold">{video.resolution}</span>
              </div>
              <div>
                <span className="text-gray-600">Camera:</span>
                <span className="ml-1 font-semibold">{video.camera_id}</span>
              </div>
            </div>

            {/* Segment Counts */}
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                {video.segments.unreviewed} unreviewed
              </span>
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded">
                {video.segments.accepted} saved
              </span>
              <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded">
                {video.segments.trashed} trashed
              </span>
            </div>
          </div>
        ))}
      </div>

      {videos.length === 0 && (
        <div className="text-center text-gray-500 mt-12">
          <p className="text-xl">No videos need sorting!</p>
          <p className="mt-2">All clips have been reviewed.</p>
        </div>
      )}
    </div>
  );
}

