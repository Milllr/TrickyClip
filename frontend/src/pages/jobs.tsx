import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface LogEntry {
  timestamp: string;
  source: string;
  level: string;
  message: string;
  metadata?: any;
}

interface SystemStats {
  cpu_percent: number;
  memory: {
    percent: number;
    used: number;
    total: number;
  };
  disk: {
    percent: number;
    used: number;
    total: number;
    free: number;
  };
  containers: Record<string, string>;
}

interface Job {
  id: string;
  job_type: string;
  status: string;
  progress_percent: number;
  created_at: string;
  file_id?: string;
}

export default function MissionControlPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [jobs, setJobs] = useState<any>(null);
  const [nextPollSeconds, setNextPollSeconds] = useState<number>(120);
  const [filter, setFilter] = useState<string>('all');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket for live logs
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
    
    ws.onopen = () => {
      console.log('🔌 Log stream connected');
    };
    
    ws.onmessage = (event) => {
      const log = JSON.parse(event.data);
      
      // Update countdown if available
      if (log.metadata?.next_poll_seconds) {
        setNextPollSeconds(log.metadata.next_poll_seconds);
      }
      
      setLogs(prev => [...prev.slice(-200), log]); // Keep last 200 logs
      
      // Auto-scroll to bottom
      setTimeout(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('🔌 Log stream disconnected - attempting reconnect...');
      // Attempt reconnect after 3s
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    };
    
    wsRef.current = ws;
    
    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    // Fetch jobs and stats periodically
    const interval = setInterval(() => {
      fetchJobs();
      fetchStats();
    }, 2000);
    
    fetchJobs();
    fetchStats();
    
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const res = await axios.get('/api/jobs/');
      setJobs(res.data);
    } catch (e) {
      console.error('Error fetching jobs:', e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/admin/system-stats');
      setStats(res.data);
    } catch (e) {
      console.error('Error fetching stats:', e);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-400 bg-red-900/20 border-l-4 border-red-500';
      case 'WARNING': return 'text-yellow-400 bg-yellow-900/20 border-l-4 border-yellow-500';
      case 'SUCCESS': return 'text-green-400 bg-green-900/20 border-l-4 border-green-500';
      case 'INFO': return 'text-blue-400 bg-blue-900/20 border-l-4 border-blue-500';
      case 'DEBUG': return 'text-gray-400 bg-gray-900/20 border-l-4 border-gray-600';
      default: return 'text-gray-400';
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'drive-sync': return 'text-purple-400';
      case 'worker': return 'text-cyan-400';
      case 'backend': return 'text-green-400';
      case 'system': return 'text-orange-400';
      default: return 'text-gray-400';
    }
  };

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.source === filter);

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  };

  const allJobs = jobs ? [
    ...(jobs.running || []),
    ...(jobs.queued || []),
    ...(jobs.completed || []).slice(0, 5),
    ...(jobs.failed || []).slice(0, 5)
  ] : [];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
              Mission Control
            </h1>
            <p className="text-gray-500 text-sm mt-1">Real-time system monitoring</p>
          </div>
          
          {/* System Stats */}
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-xs text-gray-500 uppercase">Next Drive Poll</div>
              <div className="text-3xl font-mono font-bold text-cyan-400">
                {Math.floor(nextPollSeconds / 60)}:{(nextPollSeconds % 60).toString().padStart(2, '0')}
              </div>
            </div>
            
            {stats && stats.cpu_percent !== undefined && (
              <>
                <div className="text-center">
                  <div className="text-xs text-gray-500 uppercase">CPU</div>
                  <div className="text-2xl font-mono font-bold text-green-400">
                    {(stats.cpu_percent || 0).toFixed(1)}%
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-gray-500 uppercase">Memory</div>
                  <div className="text-2xl font-mono font-bold text-yellow-400">
                    {(stats.memory?.percent || 0).toFixed(1)}%
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-gray-500 uppercase">Disk</div>
                  <div className="text-2xl font-mono font-bold text-red-400">
                    {(stats.disk?.percent || 0).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {stats.disk?.free ? formatBytes(stats.disk.free) : 'N/A'} free
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-100px)]">
        {/* Sidebar - Job Queue */}
        <div className="w-80 bg-gray-900 border-r border-gray-800 p-4 overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4 text-gray-300 flex items-center justify-between">
            <span>Active Jobs</span>
            <span className="text-sm font-mono text-gray-500">{allJobs.length}</span>
          </h2>
          
          <div className="space-y-2">
            {allJobs.length === 0 && (
              <div className="text-center text-gray-600 py-8">
                <div className="text-4xl mb-2">💤</div>
                <div className="text-sm">No active jobs</div>
              </div>
            )}
            
            {allJobs.map((job: Job) => (
              <div 
                key={job.id}
                className={`p-3 rounded border ${
                  job.status === 'completed' ? 'bg-green-900/20 border-green-800' :
                  job.status === 'failed' ? 'bg-red-900/20 border-red-800' :
                  job.status === 'started' ? 'bg-blue-900/20 border-blue-800 animate-pulse' :
                  'bg-gray-800 border-gray-700'
                }`}
              >
                <div className="text-sm font-semibold truncate">{job.job_type.replace(/_/g, ' ')}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(job.created_at).toLocaleTimeString()}
                </div>
                {job.progress_percent > 0 && job.status === 'started' && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <div 
                        className="bg-blue-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${job.progress_percent}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1 text-right">
                      {job.progress_percent}%
                    </div>
                  </div>
                )}
                {job.file_id && (
                  <div className="text-xs text-gray-600 mt-1 font-mono">
                    {job.file_id.substring(0, 8)}...
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Main Content - Live Logs */}
        <div className="flex-1 flex flex-col">
          {/* Filter Bar */}
          <div className="bg-gray-900 border-b border-gray-800 px-6 py-3">
            <div className="flex gap-2">
              {['all', 'drive-sync', 'worker', 'backend', 'system'].map(source => (
                <button
                  key={source}
                  onClick={() => setFilter(source)}
                  className={`px-4 py-2 rounded font-mono text-sm transition ${
                    filter === source
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {source.toUpperCase()}
                </button>
              ))}
              
              <button
                onClick={() => setLogs([])}
                className="ml-auto px-4 py-2 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm transition"
              >
                🗑️ Clear Logs
              </button>
            </div>
          </div>

          {/* Log Stream */}
          <div className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-black">
            {filteredLogs.length === 0 && (
              <div className="text-center text-gray-600 mt-8">
                <div className="text-4xl mb-4 animate-pulse">📡</div>
                <div>Waiting for logs...</div>
                <div className="text-xs text-gray-700 mt-2">
                  WebSocket connection established
                </div>
              </div>
            )}
            
            {filteredLogs.map((log, idx) => (
              <div 
                key={idx}
                className={`py-2 px-4 mb-1 rounded ${getLevelColor(log.level)}`}
              >
                <span className="text-gray-600">
                  [{new Date(log.timestamp).toLocaleTimeString()}]
                </span>
                <span className={`ml-2 font-bold ${getSourceColor(log.source)}`}>
                  [{log.source.toUpperCase()}]
                </span>
                <span className="ml-2">{log.message}</span>
                
                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <div className="ml-12 mt-1 text-xs text-gray-500 bg-gray-950 p-2 rounded">
                    {JSON.stringify(log.metadata, null, 2)}
                  </div>
                )}
              </div>
            ))}
            
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
