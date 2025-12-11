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
  started_at?: string;
  finished_at?: string;
  file_id?: string;
  error_message?: string;
}

export default function MissionControlPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [jobs, setJobs] = useState<any>(null);
  const [nextPollSeconds, setNextPollSeconds] = useState<number>(120);
  const [filter, setFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsReconnectAttempts, setWsReconnectAttempts] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // websocket connection with auto-reconnect
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
        
        ws.onopen = () => {
          console.log('🔌 log stream connected');
          setWsConnected(true);
          setWsReconnectAttempts(0);
          
          // add connection success log
          setLogs(prev => [...prev, {
            timestamp: new Date().toISOString(),
            source: 'system',
            level: 'SUCCESS',
            message: '🔌 websocket connected to log stream',
            metadata: {}
          }]);
        };
        
        ws.onmessage = (event) => {
          try {
            const log = JSON.parse(event.data);
            
            // update countdown if available
            if (log.metadata?.next_poll_seconds !== undefined) {
              setNextPollSeconds(log.metadata.next_poll_seconds);
            }
            
            setLogs(prev => {
              const newLogs = [...prev, log];
              // keep last 500 logs
              return newLogs.slice(-500);
            });
          } catch (e) {
            console.error('error parsing log:', e);
          }
        };
        
        ws.onerror = (error) => {
          console.error('websocket error:', error);
          setWsConnected(false);
        };
        
        ws.onclose = () => {
          console.log('🔌 log stream disconnected');
          setWsConnected(false);
          
          // add disconnection log
          setLogs(prev => [...prev, {
            timestamp: new Date().toISOString(),
            source: 'system',
            level: 'WARNING',
            message: '⚠️  websocket disconnected - attempting reconnect...',
            metadata: {}
          }]);
          
          // attempt reconnect with exponential backoff
          const attempts = wsReconnectAttempts;
          const delay = Math.min(1000 * Math.pow(2, attempts), 30000); // max 30s
          setWsReconnectAttempts(attempts + 1);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`reconnecting... (attempt ${attempts + 1})`);
            connectWebSocket();
          }, delay);
        };
        
        wsRef.current = ws;
      } catch (e) {
        console.error('failed to create websocket:', e);
        setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // auto-scroll when logs update
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // detect manual scroll to disable auto-scroll
  useEffect(() => {
    const container = logsContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setAutoScroll(isAtBottom);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // fetch jobs and stats periodically
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
      console.error('error fetching jobs:', e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/admin/system-stats');
      setStats(res.data);
    } catch (e) {
      console.error('error fetching stats:', e);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-400 bg-red-950/50 border-l-4 border-red-500';
      case 'WARNING': return 'text-yellow-400 bg-yellow-950/50 border-l-4 border-yellow-500';
      case 'SUCCESS': return 'text-green-400 bg-green-950/50 border-l-4 border-green-500';
      case 'INFO': return 'text-blue-400 bg-blue-950/50 border-l-4 border-blue-500';
      case 'DEBUG': return 'text-gray-500 bg-gray-950/50 border-l-4 border-gray-700';
      default: return 'text-gray-400 bg-gray-950/50';
    }
  };

  const getSourceBadge = (source: string) => {
    const badges = {
      'drive-sync': 'bg-purple-900/50 text-purple-300 border-purple-700',
      'worker': 'bg-cyan-900/50 text-cyan-300 border-cyan-700',
      'backend': 'bg-green-900/50 text-green-300 border-green-700',
      'system': 'bg-orange-900/50 text-orange-300 border-orange-700',
    };
    return badges[source as keyof typeof badges] || 'bg-gray-900/50 text-gray-400 border-gray-700';
  };

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.source === filter);

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  };

  const formatDuration = (startTime: string | null, endTime?: string | null) => {
    if (!startTime) return 'not started';
    const start = new Date(startTime).getTime();
    const end = endTime ? new Date(endTime).getTime() : Date.now();
    const seconds = Math.floor((end - start) / 1000);
    
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  const allJobs = jobs ? [
    ...(jobs.running || []),
    ...(jobs.queued || []),
    ...(jobs.completed || []).slice(0, 10),
    ...(jobs.failed || []).slice(0, 10)
  ] : [];

  const getStatusBadge = (status: string) => {
    const badges = {
      'running': 'bg-blue-500/20 text-blue-400 border-blue-500',
      'queued': 'bg-yellow-500/20 text-yellow-400 border-yellow-500',
      'completed': 'bg-green-500/20 text-green-400 border-green-500',
      'failed': 'bg-red-500/20 text-red-400 border-red-500',
    };
    return badges[status as keyof typeof badges] || 'bg-gray-500/20 text-gray-400 border-gray-500';
  };

  return (
    <div className="min-h-screen bg-black text-gray-100">
      {/* header with stats */}
      <div className="bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 border-b border-gray-700 px-6 py-4 shadow-2xl">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 animate-pulse">
              ⚡ MISSION CONTROL
            </h1>
            <p className="text-gray-500 text-sm mt-1 font-mono">real-time system monitoring & job orchestration</p>
          </div>
          
          {/* connection status */}
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900/50 border border-gray-700">
            <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm font-mono">
              {wsConnected ? 'STREAM ACTIVE' : `RECONNECTING... (${wsReconnectAttempts})`}
            </span>
          </div>
        </div>

        {/* system stats bar */}
        <div className="mt-4 grid grid-cols-5 gap-4">
          {/* next poll countdown */}
          <div className="bg-gradient-to-br from-cyan-900/20 to-blue-900/20 border border-cyan-800/50 rounded-lg p-4 text-center">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">next drive poll</div>
            <div className="text-4xl font-mono font-bold text-cyan-400 tabular-nums">
              {Math.floor(nextPollSeconds / 60)}:{(nextPollSeconds % 60).toString().padStart(2, '0')}
            </div>
            <div className="text-xs text-gray-600 mt-1">minutes:seconds</div>
          </div>

          {stats && (
            <>
              <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-800/50 rounded-lg p-4 text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">cpu usage</div>
                <div className="text-4xl font-mono font-bold text-green-400 tabular-nums">
                  {(stats.cpu_percent || 0).toFixed(1)}%
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 mt-2">
                  <div 
                    className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(stats.cpu_percent || 0, 100)}%` }}
                  />
                </div>
              </div>

              <div className="bg-gradient-to-br from-yellow-900/20 to-amber-900/20 border border-yellow-800/50 rounded-lg p-4 text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">memory</div>
                <div className="text-4xl font-mono font-bold text-yellow-400 tabular-nums">
                  {(stats.memory?.percent || 0).toFixed(1)}%
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 mt-2">
                  <div 
                    className="bg-gradient-to-r from-yellow-500 to-amber-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(stats.memory?.percent || 0, 100)}%` }}
                  />
                </div>
              </div>

              <div className="bg-gradient-to-br from-red-900/20 to-rose-900/20 border border-red-800/50 rounded-lg p-4 text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">disk usage</div>
                <div className="text-4xl font-mono font-bold text-red-400 tabular-nums">
                  {(stats.disk?.percent || 0).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500 mt-2">
                  {stats.disk?.free ? formatBytes(stats.disk.free) : 'N/A'} free
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-800/50 rounded-lg p-4 text-center">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">active jobs</div>
                <div className="text-4xl font-mono font-bold text-purple-400 tabular-nums">
                  {(jobs?.running?.length || 0) + (jobs?.queued?.length || 0)}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  {jobs?.running?.length || 0} running · {jobs?.queued?.length || 0} queued
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex h-[calc(100vh-220px)]">
        {/* job queue sidebar */}
        <div className="w-96 bg-gradient-to-b from-gray-900 to-black border-r border-gray-800 overflow-y-auto">
          <div className="p-4 border-b border-gray-800 bg-gray-900/50 sticky top-0 z-10">
            <h2 className="text-lg font-semibold text-gray-300 flex items-center justify-between font-mono uppercase tracking-wider">
              <span>📋 job queue</span>
              <span className="text-sm text-gray-500">{allJobs.length} total</span>
            </h2>
          </div>
          
          <div className="p-4 space-y-3">
            {allJobs.length === 0 && (
              <div className="text-center text-gray-600 py-12">
                <div className="text-6xl mb-4 opacity-20">💤</div>
                <div className="text-sm font-mono">system idle - no active jobs</div>
              </div>
            )}
            
            {allJobs.map((job: Job) => (
              <div 
                key={job.id}
                className={`p-4 rounded-lg border-2 transition-all ${
                  job.status === 'running' ? 'bg-blue-950/30 border-blue-800 shadow-lg shadow-blue-900/50 animate-pulse' :
                  job.status === 'queued' ? 'bg-yellow-950/30 border-yellow-800' :
                  job.status === 'completed' ? 'bg-green-950/30 border-green-900' :
                  job.status === 'failed' ? 'bg-red-950/30 border-red-900' :
                  'bg-gray-900 border-gray-800'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-mono text-sm font-bold text-gray-200 truncate">
                      {job.job_type.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-500 font-mono mt-1">
                      {new Date(job.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-mono uppercase border ${getStatusBadge(job.status)}`}>
                    {job.status}
                  </div>
                </div>

                {job.status === 'running' && job.progress_percent > 0 && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-gray-500 mb-1 font-mono">
                      <span>progress</span>
                      <span>{job.progress_percent}%</span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 h-2 rounded-full transition-all duration-500 animate-gradient-x"
                        style={{ width: `${job.progress_percent}%` }}
                      />
                    </div>
                  </div>
                )}

                {job.started_at && (
                  <div className="text-xs text-gray-600 mt-2 font-mono">
                    ⏱️ {formatDuration(job.started_at, job.finished_at)}
                  </div>
                )}

                {job.error_message && (
                  <div className="text-xs text-red-400 mt-2 font-mono bg-red-950/30 p-2 rounded border border-red-900">
                    ❌ {job.error_message}
                  </div>
                )}

                {job.file_id && (
                  <div className="text-xs text-gray-600 mt-2 font-mono truncate">
                    📁 {job.file_id.substring(0, 12)}...
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* main log stream */}
        <div className="flex-1 flex flex-col bg-black">
          {/* filter bar */}
          <div className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
            <div className="flex gap-2">
              {['all', 'drive-sync', 'worker', 'backend', 'system'].map(source => (
                <button
                  key={source}
                  onClick={() => setFilter(source)}
                  className={`px-4 py-2 rounded-lg font-mono text-xs uppercase tracking-wider transition-all border ${
                    filter === source
                      ? 'bg-cyan-600 text-white border-cyan-500 shadow-lg shadow-cyan-900/50'
                      : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700 hover:border-gray-600'
                  }`}
                >
                  {source === 'all' ? '🌐 ' : ''}
                  {source}
                </button>
              ))}
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`px-4 py-2 rounded-lg font-mono text-xs uppercase transition-all border ${
                  autoScroll 
                    ? 'bg-green-600 text-white border-green-500' 
                    : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                }`}
              >
                {autoScroll ? '📌 auto-scroll on' : '📌 auto-scroll off'}
              </button>
              <button
                onClick={() => setLogs([])}
                className="px-4 py-2 rounded-lg bg-gray-800 text-gray-400 border border-gray-700 hover:bg-gray-700 hover:border-gray-600 font-mono text-xs uppercase transition-all"
              >
                🗑️ clear logs
              </button>
            </div>
          </div>

          {/* log stream */}
          <div 
            ref={logsContainerRef}
            className="flex-1 overflow-y-auto p-4 font-mono text-sm"
            style={{ 
              backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.02) 1px, transparent 0)',
              backgroundSize: '40px 40px'
            }}
          >
            {filteredLogs.length === 0 && (
              <div className="text-center text-gray-700 mt-16">
                <div className="text-7xl mb-6 animate-pulse opacity-20">📡</div>
                <div className="text-lg font-bold mb-2">awaiting log stream...</div>
                <div className="text-xs text-gray-800">
                  {wsConnected ? 'connected - waiting for data' : 'connecting to websocket...'}
                </div>
              </div>
            )}
            
            {filteredLogs.map((log, idx) => (
              <div 
                key={idx}
                className={`py-3 px-4 mb-2 rounded-lg ${getLevelColor(log.level)} backdrop-blur-sm transition-all hover:scale-[1.01] hover:shadow-lg`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-gray-600 text-xs whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}.{new Date(log.timestamp).getMilliseconds().toString().padStart(3, '0')}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase border ${getSourceBadge(log.source)}`}>
                    {log.source}
                  </span>
                  <span className="flex-1 text-gray-200">{log.message}</span>
                </div>
                
                {log.metadata && Object.keys(log.metadata).length > 0 && log.level !== 'DEBUG' && (
                  <div className="ml-32 mt-2 text-xs text-gray-500 bg-black/50 p-3 rounded border border-gray-800 font-mono">
                    {Object.entries(log.metadata).map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <span className="text-gray-600">{key}:</span>
                        <span className="text-cyan-400">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      <style>{`
        @keyframes gradient-x {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }
        .animate-gradient-x {
          background-size: 200% auto;
          animation: gradient-x 2s ease infinite;
        }
      `}</style>
    </div>
  );
}
