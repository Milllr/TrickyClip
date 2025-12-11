import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

interface DetectionDebugData {
  file_id: string;
  filename: string;
  duration_sec: number;
  motion_timeseries: {
    times: number[];
    energy: number[];
  };
  audio_timeseries: {
    times: number[];
    energy: number[];
  };
  stage1_windows: Array<{
    start_sec: number;
    end_sec: number;
    motion_score: number;
    audio_score: number;
    combined_score: number;
  }>;
  final_segments: Array<{
    id: string;
    start_sec: number;
    end_sec: number;
    confidence: number;
    method: string;
    status: string;
  }>;
  config: {
    motion_threshold: number;
    audio_threshold: number;
    ml_threshold: number;
    use_stage1: boolean;
    use_ml_stage2: boolean;
  };
}

export default function DetectionDebugPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const [data, setData] = useState<DetectionDebugData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fileId) return;

    axios.get(`/api/admin/detection-debug/${fileId}`)
      .then(res => {
        setData(res.data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [fileId]);

  if (loading) {
    return <div className="text-center mt-10">loading debug data...</div>;
  }

  if (error || !data) {
    return (
      <div className="text-center mt-10 text-red-600">
        error loading debug data: {error}
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto mt-6 p-6">
      <h1 className="text-4xl font-bold mb-2">detection debug</h1>
      <p className="text-gray-600 mb-6">{data.filename} ({data.duration_sec.toFixed(1)}s)</p>

      {/* config info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <h2 className="font-bold mb-2">detection config</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600">stage 1:</span>{' '}
            <span className={data.config.use_stage1 ? "text-green-600 font-bold" : "text-gray-400"}>
              {data.config.use_stage1 ? "enabled" : "disabled"}
            </span>
          </div>
          <div>
            <span className="text-gray-600">stage 2 ml:</span>{' '}
            <span className={data.config.use_ml_stage2 ? "text-green-600 font-bold" : "text-gray-400"}>
              {data.config.use_ml_stage2 ? "enabled" : "disabled"}
            </span>
          </div>
          <div>
            <span className="text-gray-600">motion threshold:</span>{' '}
            <span className="font-mono">{data.config.motion_threshold}</span>
          </div>
          <div>
            <span className="text-gray-600">ml threshold:</span>{' '}
            <span className="font-mono">{data.config.ml_threshold}</span>
          </div>
        </div>
      </div>

      {/* summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-yellow-900">{data.stage1_windows.length}</div>
          <div className="text-sm text-yellow-700">stage 1 windows</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-900">{data.final_segments.length}</div>
          <div className="text-sm text-green-700">final segments</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-2xl font-bold text-blue-900">
            {data.final_segments.filter(s => s.status === 'ACCEPTED').length}
          </div>
          <div className="text-sm text-blue-700">user accepted</div>
        </div>
      </div>

      {/* timeseries visualization (simple text for now) */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">motion energy</h2>
        <div className="text-sm text-gray-600 mb-2">
          {data.motion_timeseries.times.length} samples
        </div>
        <div className="h-32 bg-gray-100 rounded flex items-end gap-px overflow-hidden">
          {data.motion_timeseries.energy.slice(0, 200).map((energy, i) => (
            <div
              key={i}
              className="flex-1 bg-blue-500"
              style={{ height: `${energy * 100}%` }}
              title={`t=${data.motion_timeseries.times[i]?.toFixed(1)}s, e=${energy.toFixed(2)}`}
            />
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">audio energy</h2>
        <div className="text-sm text-gray-600 mb-2">
          {data.audio_timeseries.times.length} samples
        </div>
        <div className="h-32 bg-gray-100 rounded flex items-end gap-px overflow-hidden">
          {data.audio_timeseries.energy.slice(0, 200).map((energy, i) => (
            <div
              key={i}
              className="flex-1 bg-green-500"
              style={{ height: `${energy * 100}%` }}
              title={`t=${data.audio_timeseries.times[i]?.toFixed(1)}s, e=${energy.toFixed(2)}`}
            />
          ))}
        </div>
      </div>

      {/* stage 1 windows */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">stage 1 candidate windows</h2>
        <div className="space-y-2">
          {data.stage1_windows.map((window, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-yellow-50 rounded">
              <div className="flex-1">
                <span className="font-mono text-sm">
                  {window.start_sec.toFixed(1)}s - {window.end_sec.toFixed(1)}s
                </span>
                <span className="text-gray-500 ml-2">
                  ({(window.end_sec - window.start_sec).toFixed(1)}s)
                </span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600">motion:</span>{' '}
                <span className="font-mono">{window.motion_score.toFixed(2)}</span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600">audio:</span>{' '}
                <span className="font-mono">{window.audio_score.toFixed(2)}</span>
              </div>
              <div className="text-sm font-bold">
                <span className="text-gray-600">combined:</span>{' '}
                <span className="font-mono">{window.combined_score.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* final segments */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">final segments (in db)</h2>
        <div className="space-y-2">
          {data.final_segments.map((seg) => (
            <div 
              key={seg.id} 
              className={`flex items-center gap-4 p-3 rounded ${
                seg.status === 'ACCEPTED' ? 'bg-green-50' :
                seg.status === 'TRASHED' ? 'bg-red-50' :
                'bg-gray-50'
              }`}
            >
              <div className="flex-1">
                <span className="font-mono text-sm">
                  {seg.start_sec.toFixed(1)}s - {seg.end_sec.toFixed(1)}s
                </span>
                <span className="text-gray-500 ml-2">
                  ({(seg.end_sec - seg.start_sec).toFixed(1)}s)
                </span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600">confidence:</span>{' '}
                <span className="font-mono">{seg.confidence.toFixed(2)}</span>
              </div>
              <div className="text-sm">
                <span className="text-gray-600">method:</span>{' '}
                <span className="font-mono text-xs">{seg.method}</span>
              </div>
              <div className={`text-sm font-bold px-2 py-1 rounded ${
                seg.status === 'ACCEPTED' ? 'bg-green-200 text-green-800' :
                seg.status === 'TRASHED' ? 'bg-red-200 text-red-800' :
                'bg-gray-200 text-gray-800'
              }`}>
                {seg.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


