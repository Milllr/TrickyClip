import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

interface Job {
  id: string;
  rq_job_id: string;
  job_type: string;
  status: string;
  file_id?: string;
  clip_id?: string;
  progress_percent: number;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  created_at?: string;
}

interface JobsData {
  running: Job[];
  queued: Job[];
  completed: Job[];
  failed: Job[];
  summary: {
    running_count: number;
    queued_count: number;
    completed_count: number;
    failed_count: number;
  };
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const res = await axios.get('/api/jobs/');
      setJobs(res.data);
    } catch (e) {
      console.error('error fetching jobs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchJobs, 1000); // refresh every 1s for live feel
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const formatTime = (isoString?: string) => {
    if (!isoString) return 'N/A';
    // ensure proper ISO parsing
    const dateStr = isoString.endsWith('Z') || isoString.includes('+') 
      ? isoString 
      : isoString + 'Z';
    const date = new Date(dateStr);
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    // handle negative times (future dates - shouldn't happen)
    if (diffSeconds < 0) return date.toLocaleTimeString();
    
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const getJobAction = (jobType: string, progress: number) => {
    if (jobType === 'analyze_original_file') {
      if (progress < 20) return 'loading video...';
      if (progress < 70) return 'detecting motion & tricks...';
      if (progress < 90) return 'creating segments...';
      return 'finalizing...';
    }
    if (jobType === 'render_and_upload_clip') {
      if (progress < 30) return 'rendering with ffmpeg...';
      if (progress < 60) return 'uploading to drive...';
      if (progress < 95) return 'organizing folders...';
      return 'cleaning up...';
    }
    return 'processing...';
  };

  if (loading) {
    return <div className="text-center mt-10">loading jobs...</div>;
  }

  if (!jobs) {
    return <div className="text-center mt-10 text-red-600">failed to load jobs</div>;
  }

  const hasJobs = (jobs.running?.length || 0) + (jobs.queued?.length || 0) + (jobs.completed?.length || 0) + (jobs.failed?.length || 0) > 0;

  return (
    <div className="max-w-6xl mx-auto mt-6 p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-4xl font-bold">background jobs</h1>
          <p className="text-gray-600 mt-1">real-time processing status</p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 cursor-pointer"
            />
            <span className="text-sm font-medium">auto-refresh</span>
          </label>
          <button
            onClick={fetchJobs}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold transition"
          >
            refresh now
          </button>
        </div>
      </div>

      {/* summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gradient-to-br from-yellow-100 to-yellow-200 p-6 rounded-lg shadow">
          <div className="text-4xl font-bold text-yellow-900">{jobs.summary?.running_count || 0}</div>
          <div className="text-sm font-medium text-yellow-800 mt-1">running now</div>
        </div>
        <div className="bg-gradient-to-br from-blue-100 to-blue-200 p-6 rounded-lg shadow">
          <div className="text-4xl font-bold text-blue-900">{jobs.summary?.queued_count || 0}</div>
          <div className="text-sm font-medium text-blue-800 mt-1">in queue</div>
        </div>
        <div className="bg-gradient-to-br from-green-100 to-green-200 p-6 rounded-lg shadow">
          <div className="text-4xl font-bold text-green-900">{jobs.summary?.completed_count || 0}</div>
          <div className="text-sm font-medium text-green-800 mt-1">completed</div>
        </div>
        <div className="bg-gradient-to-br from-red-100 to-red-200 p-6 rounded-lg shadow">
          <div className="text-4xl font-bold text-red-900">{jobs.summary?.failed_count || 0}</div>
          <div className="text-sm font-medium text-red-800 mt-1">failed</div>
        </div>
      </div>

      {/* running jobs - most prominent */}
      {jobs.running && jobs.running.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-yellow-700 flex items-center gap-2">
            <span className="animate-spin">⚙️</span> running jobs
          </h2>
          <div className="space-y-4">
            {jobs.running.map((job) => (
              <div key={job.id} className="bg-gradient-to-r from-yellow-50 to-white border-l-4 border-yellow-500 rounded-lg shadow-md p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="font-bold text-lg mb-1">{job.job_type.replace(/_/g, ' ')}</div>
                    <div className="text-sm text-gray-600 italic mb-2">
                      {getJobAction(job.job_type, job.progress_percent)}
                    </div>
                    {job.file_id && (
                      <div className="text-xs text-gray-500">file: {job.file_id.substring(0, 8)}...</div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-yellow-700">{job.progress_percent}%</div>
                    <div className="text-xs text-gray-500">{formatTime(job.started_at)}</div>
                  </div>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-yellow-400 to-yellow-600 h-3 transition-all duration-300 ease-out"
                    style={{ width: `${job.progress_percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* queued jobs */}
      {jobs.queued && jobs.queued.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-blue-700">⏳ queued jobs</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {jobs.queued.map((job) => (
              <div key={job.id} className="border-b last:border-0 p-4 hover:bg-blue-50 transition">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="font-semibold">{job.job_type.replace(/_/g, ' ')}</div>
                    {job.file_id && (
                      <div className="text-xs text-gray-500 mt-1">file: {job.file_id.substring(0, 12)}...</div>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatTime(job.created_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* completed jobs */}
      {jobs.completed && jobs.completed.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-green-700">✅ completed</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {jobs.completed.slice(0, 10).map((job) => (
              <div key={job.id} className="border-b last:border-0 p-4 hover:bg-green-50 transition">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="font-semibold">{job.job_type.replace(/_/g, ' ')}</div>
                    {job.file_id && (
                      <div className="text-xs text-gray-500 mt-1">file: {job.file_id.substring(0, 12)}...</div>
                    )}
                  </div>
                  <div className="text-sm text-green-600 font-medium">
                    {formatTime(job.finished_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* failed jobs */}
      {jobs.failed && jobs.failed.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 text-red-700">❌ failed jobs</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {jobs.failed.map((job) => (
              <div 
                key={job.id} 
                className="border-b last:border-0 p-4 hover:bg-red-50 transition cursor-pointer"
                onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="font-semibold text-red-700">{job.job_type.replace(/_/g, ' ')}</div>
                    {job.file_id && (
                      <div className="text-xs text-gray-500 mt-1">file: {job.file_id.substring(0, 12)}...</div>
                    )}
                    {expandedJob === job.id && job.error_message && (
                      <div className="mt-3 text-xs text-red-700 bg-red-100 p-3 rounded font-mono">
                        {job.error_message}
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-red-600 ml-4">
                    {formatTime(job.created_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* empty state */}
      {!hasJobs && (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📊</div>
          <div className="text-xl text-gray-500 mb-2">no jobs yet</div>
          <div className="text-gray-400">
            <Link to="/upload" className="text-blue-600 hover:underline">upload videos</Link> to start processing
          </div>
        </div>
      )}
    </div>
  );
}
