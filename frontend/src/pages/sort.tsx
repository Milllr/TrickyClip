import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

interface Segment {
  segment_id: string;
  start_ms: number;
  end_ms: number;
  original_file: {
    id: string;
    path: string;
    fps: number;
    duration_ms: number;
  };
  video_context?: {
    current_index: number;
    total_segments: number;
    unreviewed_segments: number;
    videos_remaining: number;
    segment_ids: string[];
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
  const [range, setRange] = useState<[number, number]>([0, 0]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState<'start' | 'end' | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [showMenu, setShowMenu] = useState(false);

  const [people, setPeople] = useState<Person[]>([]);
  const [tricks, setTricks] = useState<Trick[]>([]);
  const [filteredPeople, setFilteredPeople] = useState<Person[]>([]);
  const [filteredTricks, setFilteredTricks] = useState<Trick[]>([]);

  const [category, setCategory] = useState('TRICK');
  const [personSearch, setPersonSearch] = useState('');
  const [trickSearch, setTrickSearch] = useState('');
  const [selectedPerson, setSelectedPerson] = useState<string>('');
  const [selectedTrick, setSelectedTrick] = useState<string>('');
  const [sessionName, setSessionName] = useState('Session1');
  const [showPersonDropdown, setShowPersonDropdown] = useState(false);
  const [showTrickDropdown, setShowTrickDropdown] = useState(false);

  // update video playback speed
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed;
    }
  }, [playbackSpeed]);

  // filter autocomplete
  useEffect(() => {
    if (personSearch.length > 0) {
      const filtered = people.filter(p => 
        p.display_name.toLowerCase().includes(personSearch.toLowerCase())
      );
      setFilteredPeople(filtered);
      if (filtered.length > 0 && personSearch.length > 0) {
        setShowPersonDropdown(true);
      }
    } else {
      setFilteredPeople(people);
    }
  }, [personSearch, people]);

  useEffect(() => {
    if (trickSearch.length > 0) {
      const filtered = tricks.filter(t => 
        t.name.toLowerCase().includes(trickSearch.toLowerCase())
      );
      setFilteredTricks(filtered);
      if (filtered.length > 0 && trickSearch.length > 0) {
        setShowTrickDropdown(true);
      }
    } else {
      setFilteredTricks(tricks);
    }
  }, [trickSearch, tricks]);

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
        // add 2s buffer
        const bufferMs = 2000;
        const start = Math.max(0, res.data.start_ms - bufferMs);
        const end = Math.min(res.data.original_file.duration_ms, res.data.end_ms + bufferMs);
        setRange([start, end]);
        setCurrentTime(start);
        
        // reset form
        setCategory('TRICK');
        setPersonSearch('');
        setTrickSearch('');
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
      alert('error saving');
      console.error(e);
    }
  };

  const handleTrash = async () => {
    if (!segment) return;
    try {
      await axios.post('/api/sort/trash', { segment_id: segment.segment_id });
      fetchNext();
    } catch (e) {
      alert('error trashing');
      console.error(e);
    }
  };

  const handleSkipVideo = async () => {
    if (!segment) return;
    if (!confirm(`skip all ${segment.video_context?.unreviewed_segments || 0} remaining clips from this video?`)) return;
    try {
      await axios.post(`/api/sort/skip-video?segment_id=${segment.segment_id}`);
      fetchNext();
    } catch (e) {
      alert('error skipping video');
      console.error(e);
    }
  };

  // timeline drag handlers
  const handleTimelineMouseDown = (handle: 'start' | 'end') => (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(handle);
  };

  const handleTimelineMouseMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDragging || !segment || !timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const percent = x / rect.width;
    const newTime = Math.round(percent * segment.original_file.duration_ms);
    
    if (isDragging === 'start') {
      setRange([Math.min(newTime, range[1] - 500), range[1]]);
    } else {
      setRange([range[0], Math.max(newTime, range[0] + 500)]);
    }
  };

  const handleTimelineMouseUp = () => {
    setIsDragging(null);
  };

  const handleTimelineTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    handleTimelineMouseMove(e);
  };

  const togglePlayPause = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.currentTime = range[0] / 1000;
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleVideoTimeUpdate = () => {
    if (!videoRef.current) return;
    const currentMs = videoRef.current.currentTime * 1000;
    setCurrentTime(currentMs);
    
    if (currentMs >= range[1]) {
      videoRef.current.currentTime = range[0] / 1000;
      if (videoRef.current.paused) {
        setIsPlaying(false);
      }
    }
  };

  // keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // ignore if typing in input
      if (e.target instanceof HTMLInputElement) return;
      
      if (e.key === ' ') {
        e.preventDefault();
        togglePlayPause();
      } else if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'd' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleTrash();
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [range, segment, selectedPerson, selectedTrick, category, sessionName]);

  const formatTime = (ms: number) => {
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = (totalSeconds % 60).toFixed(2);
    return `${minutes}:${seconds.padStart(5, '0')}`;
  };

  const speedOptions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-xl text-white">loading clips...</div>
      </div>
    );
  }

  if (!segment) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center text-white">
          <div className="text-2xl mb-4">🎉 all clips sorted!</div>
          <div className="text-gray-400">
            <Link to="/upload" className="text-blue-400 hover:underline">upload more videos</Link> to continue
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="fixed inset-0 bg-gray-900 text-white overflow-hidden select-none"
      onMouseMove={handleTimelineMouseMove}
      onMouseUp={handleTimelineMouseUp}
      onTouchMove={handleTimelineTouchMove}
      onTouchEnd={handleTimelineMouseUp}
    >
      {/* burger menu */}
      <div className="absolute top-4 left-4 z-50">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded shadow-lg"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        
        {showMenu && (
          <div className="absolute top-12 left-0 bg-gray-800 rounded shadow-lg py-2 min-w-[200px]">
            <Link to="/" className="block px-4 py-2 hover:bg-gray-700">home</Link>
            <Link to="/upload" className="block px-4 py-2 hover:bg-gray-700">upload</Link>
            <Link to="/sort" className="block px-4 py-2 hover:bg-gray-700 bg-gray-700">sort</Link>
            <Link to="/jobs" className="block px-4 py-2 hover:bg-gray-700">jobs</Link>
            <Link to="/clips" className="block px-4 py-2 hover:bg-gray-700">clips</Link>
          </div>
        )}
      </div>

      <div className="h-full flex flex-col md:flex-row pt-16 md:pt-0">
        {/* video player */}
        <div className="flex-1 flex items-center justify-center bg-black p-4">
          <video
            ref={videoRef}
            src={`/api/upload/media/${segment.original_file.id}`}
            className="max-w-full max-h-full rounded shadow-2xl"
            onTimeUpdate={handleVideoTimeUpdate}
            onEnded={() => setIsPlaying(false)}
          />
        </div>

        {/* sidebar controls */}
        <div className="w-full md:w-96 flex flex-col bg-gray-800 border-t md:border-t-0 md:border-l border-gray-700">
          {/* timeline scrubber */}
          <div className="p-4 border-b border-gray-700">
            <div className="mb-2 flex justify-between text-xs text-gray-400">
              <span>{formatTime(range[0])}</span>
              <span className="font-bold text-white">{formatTime(range[1] - range[0])}</span>
              <span>{formatTime(range[1])}</span>
            </div>
            
            <div 
              ref={timelineRef}
              className="relative h-20 bg-gray-700 rounded cursor-crosshair touch-none"
              onClick={(e) => {
                if (isDragging || !videoRef.current || !timelineRef.current) return;
                const rect = timelineRef.current.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const percent = x / rect.width;
                const newTime = percent * (segment?.original_file.duration_ms || 0);
                videoRef.current.currentTime = newTime / 1000;
              }}
            >
              {/* selected range */}
              <div 
                className="absolute top-0 bottom-0 bg-blue-500 bg-opacity-30 border-l-2 border-r-2 border-blue-400"
                style={{
                  left: `${(range[0] / segment.original_file.duration_ms) * 100}%`,
                  right: `${100 - (range[1] / segment.original_file.duration_ms) * 100}%`
                }}
              />
              
              {/* playhead */}
              <div 
                className="absolute top-0 bottom-0 w-1 bg-white z-10 shadow"
                style={{
                  left: `${(currentTime / segment.original_file.duration_ms) * 100}%`
                }}
              />
              
              {/* start handle */}
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-5 h-12 bg-blue-600 hover:bg-blue-500 cursor-ew-resize z-20 flex items-center justify-center rounded shadow-lg active:scale-110 transition-transform"
                style={{
                  left: `${(range[0] / segment.original_file.duration_ms) * 100}%`,
                  transform: 'translate(-50%, -50%)'
                }}
                onMouseDown={handleTimelineMouseDown('start')}
                onTouchStart={(e) => {
                  e.preventDefault();
                  setIsDragging('start');
                }}
              >
                <div className="w-1 h-8 bg-white rounded"></div>
              </div>
              
              {/* end handle */}
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-5 h-12 bg-blue-600 hover:bg-blue-500 cursor-ew-resize z-20 flex items-center justify-center rounded shadow-lg active:scale-110 transition-transform"
                style={{
                  left: `${(range[1] / segment.original_file.duration_ms) * 100}%`,
                  transform: 'translate(-50%, -50%)'
                }}
                onMouseDown={handleTimelineMouseDown('end')}
                onTouchStart={(e) => {
                  e.preventDefault();
                  setIsDragging('end');
                }}
              >
                <div className="w-1 h-8 bg-white rounded"></div>
              </div>
            </div>

            {/* playback controls */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={togglePlayPause}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold flex-1 transition"
              >
                {isPlaying ? '⏸' : '▶'}
              </button>
              <button
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = range[0] / 1000;
                    setCurrentTime(range[0]);
                  }
                }}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded transition"
                title="jump to start"
              >
                ⏮
              </button>
              <button
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = range[1] / 1000;
                    setCurrentTime(range[1]);
                  }
                }}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded transition"
                title="jump to end"
              >
                ⏭
              </button>
            </div>

            {/* speed controls */}
            <div className="mt-3">
              <label className="block mb-2 text-xs font-semibold text-gray-400">playback speed: {playbackSpeed}x</label>
              <div className="flex gap-1 flex-wrap">
                {speedOptions.map(speed => (
                  <button
                    key={speed}
                    onClick={() => setPlaybackSpeed(speed)}
                    className={`px-2 py-1 text-xs rounded font-medium transition ${
                      playbackSpeed === speed
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* clip navigator */}
          {segment.video_context && (
            <div className="p-4 bg-gray-900 border-b border-gray-700">
              <div className="flex justify-between items-center mb-2">
                <div className="text-xs font-semibold text-gray-400">video progress</div>
                <div className="text-xs text-gray-400">
                  {segment.video_context.total_segments - segment.video_context.unreviewed_segments}/{segment.video_context.total_segments} sorted
                </div>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ 
                    width: `${((segment.video_context.total_segments - segment.video_context.unreviewed_segments) / segment.video_context.total_segments) * 100}%` 
                  }}
                />
              </div>
              <div className="text-xs text-gray-500 mb-2">
                clip {segment.video_context.current_index + 1} of {segment.video_context.total_segments} • {segment.video_context.videos_remaining} videos remaining
              </div>
              <button
                onClick={handleSkipVideo}
                className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium transition"
              >
                skip rest of video ({segment.video_context.unreviewed_segments} clips)
              </button>
            </div>
          )}

          {/* form fields */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div>
              <label className="block mb-2 text-sm font-semibold text-gray-300">session name</label>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-white"
              />
            </div>

            <div>
              <label className="block mb-2 text-sm font-semibold text-gray-300">category</label>
              <div className="grid grid-cols-3 gap-2">
                {['TRICK', 'BROLL', 'OTHER'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setCategory(cat)}
                    className={`px-3 py-2 rounded font-semibold text-sm transition ${
                      category === cat 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="relative">
              <label className="block mb-2 text-sm font-semibold text-gray-300">person</label>
              <input
                type="text"
                value={personSearch}
                onChange={(e) => {
                  setPersonSearch(e.target.value);
                }}
                onFocus={() => {
                  if (filteredPeople.length > 0) {
                    setShowPersonDropdown(true);
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setShowPersonDropdown(false), 200);
                }}
                placeholder="type to search..."
                autoComplete="off"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-white placeholder-gray-500"
              />
              {showPersonDropdown && filteredPeople.length > 0 && (
                <div className="absolute z-30 w-full mt-1 bg-gray-700 border border-gray-600 rounded max-h-48 overflow-y-auto shadow-xl">
                  {filteredPeople.map(person => (
                    <div
                      key={person.id}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setSelectedPerson(person.id);
                        setPersonSearch(person.display_name);
                        setShowPersonDropdown(false);
                      }}
                      className="px-3 py-2 hover:bg-gray-600 cursor-pointer text-white border-b border-gray-600 last:border-0"
                    >
                      {person.display_name}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="relative">
              <label className="block mb-2 text-sm font-semibold text-gray-300">trick</label>
              <input
                type="text"
                value={trickSearch}
                onChange={(e) => {
                  setTrickSearch(e.target.value);
                }}
                onFocus={() => {
                  if (filteredTricks.length > 0) {
                    setShowTrickDropdown(true);
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setShowTrickDropdown(false), 200);
                }}
                placeholder="type to search..."
                autoComplete="off"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-white placeholder-gray-500"
              />
              {showTrickDropdown && filteredTricks.length > 0 && (
                <div className="absolute z-30 w-full mt-1 bg-gray-700 border border-gray-600 rounded max-h-48 overflow-y-auto shadow-xl">
                  {filteredTricks.map(trick => (
                    <div
                      key={trick.id}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setSelectedTrick(trick.id);
                        setTrickSearch(trick.name);
                        setShowTrickDropdown(false);
                      }}
                      className="px-3 py-2 hover:bg-gray-600 cursor-pointer text-white border-b border-gray-600 last:border-0"
                    >
                      {trick.name}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* keyboard shortcuts */}
            <div className="text-xs text-gray-500 pt-4 border-t border-gray-700">
              <div className="font-semibold mb-1">shortcuts:</div>
              <div>space: play/pause</div>
              <div>cmd+s: save & next</div>
              <div>cmd+d: trash</div>
            </div>
          </div>

          {/* action buttons */}
          <div className="p-4 border-t border-gray-700 grid grid-cols-2 gap-3">
            <button
              onClick={handleTrash}
              className="px-4 py-3 bg-red-600 hover:bg-red-700 rounded font-semibold transition active:scale-95"
            >
              trash
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-3 bg-green-600 hover:bg-green-700 rounded font-semibold transition active:scale-95"
            >
              save & next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
