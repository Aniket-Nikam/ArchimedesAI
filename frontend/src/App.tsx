import { useState, useEffect } from 'react';
import { PanelLeft } from 'lucide-react';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import Bookmarks from './components/Bookmarks';
import ManuscriptStudio from './components/ManuscriptStudio';
import './App.css';

export default function App() {
  const [user, setUser] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [activeView, setActiveView] = useState<'chat' | 'bookmarks' | 'studio'>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Load user from local storage
  useEffect(() => {
    const stored = localStorage.getItem('archimedes_user');
    if (stored) setUser(JSON.parse(stored));
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    localStorage.setItem('archimedes_user', JSON.stringify(userData));
    fetchHistory(userData.id);
  };

  const handleLogout = () => {
    setUser(null);
    setHistory([]);
    setChatHistory([]);
    localStorage.removeItem('archimedes_user');
  };

  const fetchHistory = async (userId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/history/?user_id=${userId}`);
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
      const res = await fetch(`http://localhost:8000/api/history/${sessionId}?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setChatHistory([
          { role: 'assistant', content: 'What would you like to research today?' },
          { role: 'user', content: data.query },
          { role: 'assistant', content: `Here is your saved research on *"${data.query}"*.`, report: data.report }
        ]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/history/${sessionId}?user_id=${user.id}`, {
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
    setChatHistory([]);
  };

  if (!user) {
    return <Auth onLogin={handleLogin} />;
  }

  return (
    <div className="app-layout">
      {/* Sidebar toggle (visible when collapsed) */}
      <button
        className={`sidebar-toggle ${!sidebarCollapsed ? 'hidden' : ''}`}
        onClick={() => setSidebarCollapsed(false)}
        title="Open sidebar"
      >
        <PanelLeft size={20} />
      </button>

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
        {activeView === 'bookmarks' ? (
          <Bookmarks user={user} onClose={() => setActiveView('chat')} />
        ) : activeView === 'studio' ? (
          <ManuscriptStudio user={user} onClose={() => setActiveView('chat')} />
        ) : (
          <Chat
            user={user}
            chatHistory={chatHistory}
            setChatHistory={setChatHistory}
            onNewSession={() => fetchHistory(user.id)}
          />
        )}
      </div>
    </div>
  );
}
