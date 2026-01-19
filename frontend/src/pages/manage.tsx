import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Person {
  id: string;
  display_name: string;
  slug: string;
}

interface Trick {
  id: string;
  name: string;
  category: string;
  direction: string | null;
}

interface Location {
  id: string;
  name: string;
  slug: string;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
}

interface Camera {
  id: string;
  name: string;
  slug: string;
  device_type: string;
}

type Tab = 'people' | 'tricks' | 'locations' | 'cameras';

export default function ManagePage() {
  const [activeTab, setActiveTab] = useState<Tab>('people');
  const [loading, setLoading] = useState(true);
  
  // data
  const [people, setPeople] = useState<Person[]>([]);
  const [tricks, setTricks] = useState<Trick[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  
  // editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editExtra, setEditExtra] = useState(''); // for category, device_type, etc.
  
  // delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  
  // message
  const [message, setMessage] = useState<{text: string; type: 'success' | 'error'} | null>(null);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [peopleRes, tricksRes, locationsRes, camerasRes] = await Promise.all([
        axios.get('/api/people/'),
        axios.get('/api/tricks/'),
        axios.get('/api/locations/'),
        axios.get('/api/cameras/')
      ]);
      setPeople(peopleRes.data);
      setTricks(tricksRes.data);
      setLocations(locationsRes.data);
      setCameras(camerasRes.data);
    } catch (e) {
      console.error('error fetching data:', e);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const startEdit = (id: string, value: string, extra: string = '') => {
    setEditingId(id);
    setEditValue(value);
    setEditExtra(extra);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue('');
    setEditExtra('');
  };

  const saveEdit = async () => {
    if (!editingId || !editValue.trim()) return;
    
    try {
      switch (activeTab) {
        case 'people':
          await axios.patch(`/api/people/${editingId}`, { display_name: editValue });
          setPeople(prev => prev.map(p => p.id === editingId ? { ...p, display_name: editValue } : p));
          break;
        case 'tricks':
          await axios.patch(`/api/tricks/${editingId}`, { name: editValue, category: editExtra });
          setTricks(prev => prev.map(t => t.id === editingId ? { ...t, name: editValue, category: editExtra } : t));
          break;
        case 'locations':
          await axios.patch(`/api/locations/${editingId}`, { name: editValue });
          setLocations(prev => prev.map(l => l.id === editingId ? { ...l, name: editValue } : l));
          break;
        case 'cameras':
          await axios.patch(`/api/cameras/${editingId}`, { name: editValue, device_type: editExtra });
          setCameras(prev => prev.map(c => c.id === editingId ? { ...c, name: editValue, device_type: editExtra } : c));
          break;
      }
      showMessage('saved successfully', 'success');
      cancelEdit();
    } catch (e) {
      console.error('error saving:', e);
      showMessage('failed to save', 'error');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      switch (activeTab) {
        case 'people':
          await axios.delete(`/api/people/${id}`);
          setPeople(prev => prev.filter(p => p.id !== id));
          break;
        case 'tricks':
          await axios.delete(`/api/tricks/${id}`);
          setTricks(prev => prev.filter(t => t.id !== id));
          break;
        case 'locations':
          await axios.delete(`/api/locations/${id}`);
          setLocations(prev => prev.filter(l => l.id !== id));
          break;
        case 'cameras':
          await axios.delete(`/api/cameras/${id}`);
          setCameras(prev => prev.filter(c => c.id !== id));
          break;
      }
      showMessage('deleted successfully', 'success');
      setDeleteConfirm(null);
    } catch (e) {
      console.error('error deleting:', e);
      showMessage('failed to delete', 'error');
    }
  };

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'people', label: 'people', count: people.length },
    { id: 'tricks', label: 'tricks', count: tricks.length },
    { id: 'locations', label: 'locations', count: locations.length },
    { id: 'cameras', label: 'cameras', count: cameras.length },
  ];

  const renderPeopleList = () => (
    <div className="space-y-2">
      {people.map(person => (
        <div key={person.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
          {editingId === person.id ? (
            <div className="flex-1 flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="flex-1 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
              />
              <button onClick={saveEdit} className="px-3 py-1 bg-green-600 rounded text-sm hover:bg-green-700">save</button>
              <button onClick={cancelEdit} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
            </div>
          ) : (
            <>
              <div>
                <div className="font-medium">{person.display_name}</div>
                <div className="text-xs text-gray-500">{person.slug}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(person.id, person.display_name)}
                  className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-700"
                >
                  edit
                </button>
                {deleteConfirm === person.id ? (
                  <>
                    <button onClick={() => handleDelete(person.id)} className="px-3 py-1 bg-red-600 rounded text-sm hover:bg-red-700">confirm</button>
                    <button onClick={() => setDeleteConfirm(null)} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(person.id)}
                    className="px-3 py-1 bg-red-600/50 rounded text-sm hover:bg-red-600"
                  >
                    delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      ))}
      {people.length === 0 && <div className="text-gray-500 text-center py-8">no people found</div>}
    </div>
  );

  const renderTricksList = () => (
    <div className="space-y-2">
      {tricks.map(trick => (
        <div key={trick.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
          {editingId === trick.id ? (
            <div className="flex-1 flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="trick name"
                className="flex-1 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
              />
              <select
                value={editExtra}
                onChange={(e) => setEditExtra(e.target.value)}
                className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="RAIL">RAIL</option>
                <option value="JUMP">JUMP</option>
                <option value="FLAT">FLAT</option>
                <option value="GAP">GAP</option>
                <option value="MANUAL">MANUAL</option>
                <option value="OTHER">OTHER</option>
              </select>
              <button onClick={saveEdit} className="px-3 py-1 bg-green-600 rounded text-sm hover:bg-green-700">save</button>
              <button onClick={cancelEdit} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
            </div>
          ) : (
            <>
              <div>
                <div className="font-medium">{trick.name}</div>
                <div className="text-xs text-gray-500">{trick.category}{trick.direction && ` • ${trick.direction}`}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(trick.id, trick.name, trick.category)}
                  className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-700"
                >
                  edit
                </button>
                {deleteConfirm === trick.id ? (
                  <>
                    <button onClick={() => handleDelete(trick.id)} className="px-3 py-1 bg-red-600 rounded text-sm hover:bg-red-700">confirm</button>
                    <button onClick={() => setDeleteConfirm(null)} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(trick.id)}
                    className="px-3 py-1 bg-red-600/50 rounded text-sm hover:bg-red-600"
                  >
                    delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      ))}
      {tricks.length === 0 && <div className="text-gray-500 text-center py-8">no tricks found</div>}
    </div>
  );

  const renderLocationsList = () => (
    <div className="space-y-2">
      {locations.map(location => (
        <div key={location.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
          {editingId === location.id ? (
            <div className="flex-1 flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="flex-1 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
              />
              <button onClick={saveEdit} className="px-3 py-1 bg-green-600 rounded text-sm hover:bg-green-700">save</button>
              <button onClick={cancelEdit} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
            </div>
          ) : (
            <>
              <div>
                <div className="font-medium">{location.name}</div>
                <div className="text-xs text-gray-500">
                  {location.address || location.slug}
                  {location.latitude && location.longitude && (
                    <span className="ml-2">📍 {location.latitude.toFixed(3)}, {location.longitude.toFixed(3)}</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(location.id, location.name)}
                  className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-700"
                >
                  edit
                </button>
                {deleteConfirm === location.id ? (
                  <>
                    <button onClick={() => handleDelete(location.id)} className="px-3 py-1 bg-red-600 rounded text-sm hover:bg-red-700">confirm</button>
                    <button onClick={() => setDeleteConfirm(null)} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(location.id)}
                    className="px-3 py-1 bg-red-600/50 rounded text-sm hover:bg-red-600"
                  >
                    delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      ))}
      {locations.length === 0 && <div className="text-gray-500 text-center py-8">no locations found</div>}
    </div>
  );

  const renderCamerasList = () => (
    <div className="space-y-2">
      {cameras.map(camera => (
        <div key={camera.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
          {editingId === camera.id ? (
            <div className="flex-1 flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="camera name"
                className="flex-1 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
              />
              <select
                value={editExtra}
                onChange={(e) => setEditExtra(e.target.value)}
                className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="gopro">gopro</option>
                <option value="iphone">iphone</option>
                <option value="dji">dji</option>
                <option value="android">android</option>
                <option value="other">other</option>
              </select>
              <button onClick={saveEdit} className="px-3 py-1 bg-green-600 rounded text-sm hover:bg-green-700">save</button>
              <button onClick={cancelEdit} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
            </div>
          ) : (
            <>
              <div>
                <div className="font-medium">{camera.name}</div>
                <div className="text-xs text-gray-500">{camera.device_type} • {camera.slug}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(camera.id, camera.name, camera.device_type)}
                  className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-700"
                >
                  edit
                </button>
                {deleteConfirm === camera.id ? (
                  <>
                    <button onClick={() => handleDelete(camera.id)} className="px-3 py-1 bg-red-600 rounded text-sm hover:bg-red-700">confirm</button>
                    <button onClick={() => setDeleteConfirm(null)} className="px-3 py-1 bg-gray-600 rounded text-sm hover:bg-gray-700">cancel</button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(camera.id)}
                    className="px-3 py-1 bg-red-600/50 rounded text-sm hover:bg-red-600"
                  >
                    delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      ))}
      {cameras.length === 0 && <div className="text-gray-500 text-center py-8">no cameras found</div>}
    </div>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'people':
        return renderPeopleList();
      case 'tricks':
        return renderTricksList();
      case 'locations':
        return renderLocationsList();
      case 'cameras':
        return renderCamerasList();
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">manage metadata</h1>
        
        {/* message toast */}
        {message && (
          <div className={`fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 ${
            message.type === 'success' ? 'bg-green-600' : 'bg-red-600'
          }`}>
            {message.text}
          </div>
        )}
        
        {/* tabs */}
        <div className="flex gap-1 mb-6 bg-gray-800 p-1 rounded-lg">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-4 py-2 rounded-md transition ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {tab.label} <span className="text-xs opacity-70">({tab.count})</span>
            </button>
          ))}
        </div>
        
        {/* content */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">loading...</div>
        ) : (
          renderContent()
        )}
        
        {/* help text */}
        <div className="mt-8 p-4 bg-gray-800/50 rounded-lg text-sm text-gray-400">
          <p className="mb-2">editing names here will update them across all clips that reference them.</p>
          <p>deleting an entry will remove the association from clips (the clips themselves are preserved).</p>
        </div>
      </div>
    </div>
  );
}

