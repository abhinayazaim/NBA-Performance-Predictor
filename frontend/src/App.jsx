import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { PlayerProvider } from './context/PlayerContext';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import PlayerCareerPage from './pages/PlayerCareerPage';
import ErrorBoundary from './components/ErrorBoundary';

// ProgressBar must live INSIDE BrowserRouter to use useLocation
const ProgressBar = () => {
  const [progress, setProgress] = useState(0);
  const location = useLocation();

  useEffect(() => {
    setProgress(30);
    const t1 = setTimeout(() => setProgress(85), 100);
    const t2 = setTimeout(() => setProgress(100), 800);
    const t3 = setTimeout(() => setProgress(0), 1200);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [location]);

  return (
    <div className="fixed top-0 left-0 w-full h-0.5 z-[100]">
      <div
        className="h-full bg-court-orange transition-all duration-500 ease-out"
        style={{ width: `${progress}%`, opacity: progress > 0 ? 1 : 0 }}
      />
    </div>
  );
};

// Inner layout lives inside BrowserRouter so all router hooks work
const AppLayout = () => {
  return (
    <div className="min-h-screen bg-court-bg text-court-text font-body pb-20 selection:bg-court-orange/30">
      <ProgressBar />
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 pt-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/player/:playerId" element={<PlayerCareerPage />} />
        </Routes>
      </main>
    </div>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <PlayerProvider>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </PlayerProvider>
    </ErrorBoundary>
  );
}

export default App;