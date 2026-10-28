import { apiFetch, setCsrfToken } from './api';
import { useState, useEffect, lazy, Suspense } from 'react';
import { PanelLeft } from 'lucide-react';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
const Bookmarks = lazy(() => import('./components/Bookmarks'));
const ManuscriptStudio = lazy(() => import('./components/ManuscriptStudio'));
import './App.css';
import './workspace.css';

export default function App() {
  const [user, setUser] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [activeView, setActiveView] = useState<'chat' | 'bookmarks' | 'studio'>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth < 800);
  const [restoring, setRestoring] = useState(true);
  const [notice, setNotice] = useState('');
  const [chatEpoch, setChatEpoch] = useState(0);

  // Load user from local storage
  useEffect(() => {
    localStorage.removeItem('archimedes_user');
    let alive = true;
    apiFetch('/api/auth/session').then(res => res.json()).then(data => {
      if (alive) { setCsrfToken(data.csrf_token); setUser(data.user); }
    }).catch(() => {}).finally(() => { if (alive) setRestoring(false); });
    const expire = () => { setUser(null); setHistory([]); setChatHistory([]); setCsrfToken(''); };
    window.addEventListener('archimedes:session-expired', expire);
    return () => { alive = false; window.removeEventListener('archimedes:session-expired', expire); };
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    setNotice('');
  };

  const handleLogout = async () => {
    try { await apiFetch('/api/auth/logout', { method: 'POST' }); }
    catch (error) { setNotice((error as Error).message); return; }
    setCsrfToken('');
    setUser(null);
    setHistory([]);
    setChatHistory([]);
    localStorage.removeItem('archimedes_user');
  };

  const fetchHistory = async (userId: number) => {
    try {
      const res = await apiFetch(`/api/history/?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (user) fetchHistory(user.id);
  }, [user]);

  const handleLoadSession = async (sessionId: number) => {
    try {
      const res = await apiFetch(`/api/history/${sessionId}?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setActiveView('chat');
        setChatEpoch(epoch => epoch + 1);
        setChatHistory([
          { role: 'assistant', content: 'What would you like to research today?' },
          { role: 'user', content: data.query },
          { role: 'assistant', content: `Here is your saved research on *"${data.query}"*.`, report: data.report }
        ]);
      }
    } catch (e) {
      setNotice((e as Error).message);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    try {
      const res = await apiFetch(`/api/history/${sessionId}?user_id=${user.id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchHistory(user.id);
        setChatHistory([]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewChat = () => {
    setChatEpoch(epoch => epoch + 1);
    setActiveView('chat');
    setChatHistory([]);
  };

  if (restoring) return <div className="startup-state" role="status">Opening your research workspace…</div>;
  if (!user) {
    return <Auth onLogin={handleLogin} />;
  }

  return (
    <div className="app-layout">
      {/* Sidebar toggle (visible when collapsed) */}
      {sidebarCollapsed && <button
        className={`sidebar-toggle ${!sidebarCollapsed ? 'hidden' : ''}`}
        onClick={() => setSidebarCollapsed(false)}
        title="Open sidebar"
        aria-label="Open sidebar"
      >
        <PanelLeft size={20} />
      </button>}

      <Sidebar
        user={user}
        history={history}
        onLogout={handleLogout}
        onLoadSession={handleLoadSession}
        onDeleteSession={handleDeleteSession}
        onNewChat={handleNewChat}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onToggleBookmarks={() => setActiveView(activeView === 'bookmarks' ? 'chat' : 'bookmarks')}
        onToggleStudio={() => setActiveView(activeView === 'studio' ? 'chat' : 'studio')}
        showBookmarks={activeView === 'bookmarks'}
        showStudio={activeView === 'studio'}
      />
      <div className="main-content">
        <header className="workspace-header"><div><span className="workspace-eyebrow">YOUR LIBRARY OF EVIDENCE</span><h1>{activeView === 'chat' ? 'Research desk' : activeView === 'bookmarks' ? 'Reading list' : 'Manuscript studio'}</h1></div><span className="workspace-mode">Discover · Connect · Synthesize</span></header>
        {notice && <div className="workspace-notice" role="alert">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss notice">×</button></div>}
        <Suspense fallback={<div className="startup-state" role="status">Loading workspace…</div>}>
        {activeView === 'bookmarks' ? (
          <Bookmarks user={user} onClose={() => setActiveView('chat')} />
        ) : activeView === 'studio' ? (
          <ManuscriptStudio user={user} onClose={() => setActiveView('chat')} />
        ) : (
          <Chat
            key={chatEpoch}
            user={user}
            chatHistory={chatHistory}
            setChatHistory={setChatHistory}
            onNewSession={() => fetchHistory(user.id)}
          />
        )}
        </Suspense>
      </div>
    </div>
  );
}
