import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Clip {
  id: string;
  filename: string;
  person: string | null;
  person_slug: string | null;
  trick: string | null;
  category: string;
  session_name: string;
  date: string;
  duration_ms: number;
  resolution: string;
  aspect_ratio: string;
  fps: string;
  camera: string;
  drive_url: string | null;
  is_uploaded: boolean;
  original_file_id: string;
  start_ms: number;
  end_ms: number;
  created_at: string;
}

interface Stats {
  total_clips: number;
  total_uploaded: number;
  by_year: { [key: string]: number };
  by_person: { [key: string]: number };
  by_trick: { [key: string]: number };
}

export default function ClipsPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'list' | 'tree'>('grid');
  
  // filters
  const [searchTerm, setSearchTerm] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [resolutionFilter, setResolutionFilter] = useState('');
  
  // pagination
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 24;
  
  useEffect(() => {
    fetchClips();
    fetchStats();
  }, [searchTerm, yearFilter, categoryFilter, resolutionFilter, page]);
  
  const fetchClips = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (yearFilter) params.append('year', yearFilter);
      if (categoryFilter) params.append('category', categoryFilter);
      if (resolutionFilter) params.append('resolution', resolutionFilter);
      params.append('skip', (page * pageSize).toString());
      params.append('limit', pageSize.toString());
      
      const res = await axios.get(`/api/clips/?${params}`);
      setClips(res.data.clips);
      setTotal(res.data.total);
    } catch (e) {
      console.error('error fetching clips:', e);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/clips/stats');
      setStats(res.data);
    } catch (e) {
      console.error('error fetching stats:', e);
    }
  };
  
  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    return `${seconds}s`;
  };
  
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };
  
  if (loading && clips.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">loading clips...</div>
      </div>
    );
  }
  
  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* header with stats */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">clips library</h1>
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-100 p-4 rounded">
              <div className="text-3xl font-bold">{stats.total_clips}</div>
              <div className="text-sm text-gray-600">total clips</div>
            </div>
            <div className="bg-green-100 p-4 rounded">
              <div className="text-3xl font-bold">{stats.total_uploaded}</div>
              <div className="text-sm text-gray-600">uploaded to drive</div>
            </div>
            <div className="bg-purple-100 p-4 rounded">
              <div className="text-3xl font-bold">{Object.keys(stats.by_person).length}</div>
              <div className="text-sm text-gray-600">people</div>
            </div>
            <div className="bg-orange-100 p-4 rounded">
              <div className="text-3xl font-bold">{Object.keys(stats.by_trick).length}</div>
              <div className="text-sm text-gray-600">unique tricks</div>
            </div>
          </div>
        )}
      </div>
      
      {/* filters and search */}
      <div className="bg-white p-6 rounded shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="search clips..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            className="px-4 py-2 border rounded focus:outline-none focus:border-blue-500"
          />
          
          <select
            value={yearFilter}
            onChange={(e) => {
              setYearFilter(e.target.value);
              setPage(0);
            }}
            className="px-4 py-2 border rounded focus:outline-none focus:border-blue-500"
          >
            <option value="">all years</option>
            {stats && Object.keys(stats.by_year).map(year => (
              <option key={year} value={year}>{year} ({stats.by_year[year]})</option>
            ))}
          </select>
          
          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setPage(0);
            }}
            className="px-4 py-2 border rounded focus:outline-none focus:border-blue-500"
          >
            <option value="">all categories</option>
            <option value="TRICK">tricks</option>
            <option value="BROLL">b-roll</option>
            <option value="OTHER">other</option>
          </select>
          
          <select
            value={resolutionFilter}
            onChange={(e) => {
              setResolutionFilter(e.target.value);
              setPage(0);
            }}
            className="px-4 py-2 border rounded focus:outline-none focus:border-blue-500"
          >
            <option value="">all resolutions</option>
            <option value="4K">4K</option>
            <option value="1080p">1080p</option>
            <option value="720p">720p</option>
          </select>
        </div>
        
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`px-4 py-2 rounded ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            grid
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            list
          </button>
          <button
            onClick={() => setViewMode('tree')}
            className={`px-4 py-2 rounded ${viewMode === 'tree' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            tree
          </button>
        </div>
      </div>
      
      {/* clips display */}
      {clips.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          no clips found. upload and sort videos to see them here!
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {clips.map(clip => (
            <div key={clip.id} className="bg-white rounded-lg shadow-lg hover:shadow-xl transition overflow-hidden">
              <div className="aspect-video bg-gray-900 relative group">
                {clip.drive_url ? (
                  <>
                    <iframe
                      src={`https://drive.google.com/file/d/${clip.drive_url.split('/d/')[1]?.split('/')[0]}/preview`}
                      className="w-full h-full"
                      allow="autoplay"
                    />
                    <a 
                      href={clip.drive_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="absolute top-2 right-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition"
                    >
                      open in drive →
                    </a>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-white text-sm">
                    processing...
                  </div>
                )}
              </div>
              <div className="p-4">
                <div className="font-bold text-lg mb-2 truncate" title={clip.trick || 'B-ROLL'}>
                  {clip.trick || 'B-ROLL'}
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  {clip.person && <div className="font-semibold">👤 {clip.person}</div>}
                  <div>📅 {formatDate(clip.date)}</div>
                  <div>⏱ {formatDuration(clip.duration_ms)}</div>
                  <div>📹 {clip.resolution} • {clip.aspect_ratio.replace('x', ':')}</div>
                  <div className="text-xs text-gray-400 mt-2 truncate" title={clip.filename}>
                    {clip.filename}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 text-left">filename</th>
                <th className="px-4 py-3 text-left">person</th>
                <th className="px-4 py-3 text-left">trick</th>
                <th className="px-4 py-3 text-left">date</th>
                <th className="px-4 py-3 text-left">duration</th>
                <th className="px-4 py-3 text-left">resolution</th>
                <th className="px-4 py-3 text-left">actions</th>
              </tr>
            </thead>
            <tbody>
              {clips.map(clip => (
                <tr key={clip.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono">{clip.filename}</td>
                  <td className="px-4 py-3 text-sm">{clip.person || '-'}</td>
                  <td className="px-4 py-3 text-sm">{clip.trick || '-'}</td>
                  <td className="px-4 py-3 text-sm">{formatDate(clip.date)}</td>
                  <td className="px-4 py-3 text-sm">{formatDuration(clip.duration_ms)}</td>
                  <td className="px-4 py-3 text-sm">{clip.resolution}</td>
                  <td className="px-4 py-3 text-sm">
                    {clip.drive_url && (
                      <a 
                        href={clip.drive_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        view
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* pagination */}
      {total > pageSize && (
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-2 bg-white border rounded disabled:opacity-50"
          >
            previous
          </button>
          <span className="px-4 py-2">
            page {page + 1} of {Math.ceil(total / pageSize)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={(page + 1) * pageSize >= total}
            className="px-4 py-2 bg-white border rounded disabled:opacity-50"
          >
            next
          </button>
        </div>
      )}
    </div>
  );
}

