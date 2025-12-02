import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

interface Segment {
  segment_id: string;
  start_ms: number;
  end_ms: number;
  original_file: {
    path: string;
    fps: number;
    duration_ms: number;
  };
}

interface Person {
  id: string;
  display_name: string;
  slug: string;
}

interface Trick {
  id: string;
  name: string;
  category: string;
}

export default function SortPage() {
  const [segment, setSegment] = useState<Segment | null>(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<[number, number]>([0, 0]); // ms
  const videoRef = useRef<HTMLVideoElement>(null);

  const [people, setPeople] = useState<Person[]>([]);
  const [tricks, setTricks] = useState<Trick[]>([]);

  const [category, setCategory] = useState('TRICK');
  const [selectedPerson, setSelectedPerson] = useState<string>('');
  const [selectedTrick, setSelectedTrick] = useState<string>('');
  const [sessionName, setSessionName] = useState('Session1');

  useEffect(() => {
    fetchNext();
    fetchMetadata();
  }, []);

  const fetchMetadata = async () => {
    try {
      const [pRes, tRes] = await Promise.all([
        axios.get('/api/people/'),
        axios.get('/api/tricks/')
      ]);
      setPeople(pRes.data);
      setTricks(tRes.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchNext = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/sort/next');
      if (res.data.message === 'No more segments') {
        setSegment(null);
      } else {
        setSegment(res.data);
        setRange([res.data.start_ms, res.data.end_ms]);
        // Reset form
        setCategory('TRICK');
        setSelectedPerson('');
        setSelectedTrick('');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!segment) return;
    try {
      await axios.post('/api/sort/save', {
        segment_id: segment.segment_id,
        start_ms: range[0],
        end_ms: range[1],
        category,
        person_id: selectedPerson || null,
        trick_id: selectedTrick || null,
        session_name: sessionName
      });
      fetchNext();
    } catch (e) {
      alert('Error saving');
    }
  };

  const handleTrash = async () => {
    if (!segment) return;
    try {
      await axios.post(`/api/sort/trash?segment_id=${segment.segment_id}`);
      fetchNext();
    } catch (e) {
      alert('Error trashing');
    }
  };

  // Loop preview
  useEffect(() => {
    if (!videoRef.current || !segment) return;
    const vid = videoRef.current;

    const checkTime = () => {
      const endSec = range[1] / 1000;
      const startSec = range[0] / 1000;
      if (vid.currentTime > endSec || vid.currentTime < startSec) {
        vid.currentTime = startSec;
        vid.play();
      }
    };

    const interval = setInterval(checkTime, 100);
    return () => clearInterval(interval);
  }, [range, segment]);

  if (loading) return <div className="p-10">Loading...</div>;
  if (!segment) return <div className="p-10">No unreviewed segments found. Go upload more!</div>;

  // video path: needs a route to serve files or we assume /data is mounted to nginx or public?
  // In MVP with vite proxy, we might need a backend endpoint to serve video bytes if not in public.
  // Let's assume /api/media/{path} or direct file access if we set up static mount.
  // For now, let's assume we need to add a static file server to backend or serve it.
  // The spec mentions "Example route: GET /api/media/originals/{file_id}".
  // I'll implement that in backend later. For now assume it exists.
  
  // UPDATE: I need to add the media endpoint to backend for this to work.
  const videoSrc = `/api/upload/media/${segment.original_file.id}`; // changed to use ID

  return (
    <div className="flex h-[calc(100vh-100px)]">
      <div className="flex-1 bg-black flex items-center justify-center relative">
        <video
          ref={videoRef}
          src={videoSrc}
          className="max-h-full max-w-full"
          controls
          autoPlay
          loop
          muted
        />
        {/* Simple overlay for trim visualization could go here */}
      </div>
      
      <div className="w-96 bg-white p-6 border-l overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Sort Clip</h2>
        
        <div className="mb-6 space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase">Timing (ms)</label>
            <div className="flex gap-2 mt-1">
               <input 
                 type="number" 
                 value={range[0]} 
                 onChange={e => setRange([Number(e.target.value), range[1]])}
                 className="w-full border p-1 rounded"
               />
               <span className="self-center">-</span>
               <input 
                 type="number" 
                 value={range[1]} 
                 onChange={e => setRange([range[0], Number(e.target.value)])}
                 className="w-full border p-1 rounded"
               />
            </div>
             {/* Add simple range sliders if time permits, for now number inputs are MVP */}
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase">Session</label>
            <input 
              type="text" 
              value={sessionName}
              onChange={e => setSessionName(e.target.value)}
              className="w-full border p-2 rounded mt-1"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase">Category</label>
            <select 
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full border p-2 rounded mt-1"
            >
              <option value="TRICK">Trick</option>
              <option value="BROLL">B-Roll</option>
              <option value="CRASH">Crash</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase">Person</label>
            <select 
              value={selectedPerson}
              onChange={e => setSelectedPerson(e.target.value)}
              className="w-full border p-2 rounded mt-1"
            >
              <option value="">Select Person...</option>
              {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase">Trick</label>
            <select 
              value={selectedTrick}
              onChange={e => setSelectedTrick(e.target.value)}
              className="w-full border p-2 rounded mt-1"
            >
              <option value="">Select Trick...</option>
              {tricks.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <button 
            onClick={handleTrash}
            className="bg-red-100 text-red-700 py-3 rounded font-bold hover:bg-red-200"
          >
            Trash
          </button>
          <button 
            onClick={handleSave}
            className="bg-green-600 text-white py-3 rounded font-bold hover:bg-green-700"
          >
            Save & Next
          </button>
        </div>
      </div>
    </div>
  );
}

