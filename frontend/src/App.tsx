import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import UploadPage from './pages/upload';
import SortPage from './pages/sort';
import JobsPage from './pages/jobs';
import ClipsPage from './pages/clips';
import AdminAuthPage from './pages/admin-auth';
import VideoLibraryPage from './pages/video-library';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100 text-gray-900">
        <nav className="bg-white shadow p-4">
          <div className="max-w-6xl mx-auto flex gap-6">
            <Link to="/" className="font-bold text-xl">TrickyClip</Link>
            <Link to="/upload" className="hover:text-blue-600">Upload</Link>
            <Link to="/videos" className="hover:text-blue-600">Videos</Link>
            <Link to="/sort" className="hover:text-blue-600">Sort</Link>
            <Link to="/jobs" className="hover:text-blue-600">Jobs</Link>
            <Link to="/clips" className="hover:text-blue-600">Clips</Link>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto p-4">
          <Routes>
            <Route path="/" element={<div className="text-center mt-20">Welcome to TrickyClip. <Link to="/upload" className="text-blue-600 underline">Upload videos</Link> to start.</div>} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/videos" element={<VideoLibraryPage />} />
            <Route path="/sort" element={<SortPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/clips" element={<ClipsPage />} />
            <Route path="/admin/auth" element={<AdminAuthPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

