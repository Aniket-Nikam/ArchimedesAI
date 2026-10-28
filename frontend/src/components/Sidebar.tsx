import { LogOut, Plus, MessageSquare, Trash2, Star, PenTool, PanelLeftClose } from 'lucide-react';

export default function Sidebar({
  user,
  history,
  onLogout,
  onLoadSession,
  onDeleteSession,
  onNewChat,
  collapsed,
  onToggle,
  onToggleBookmarks,
  onToggleStudio,
  showBookmarks,
  showStudio,
}: any) {
  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`} inert={collapsed} aria-hidden={collapsed}>
      <div className="sidebar-inner">
        <div className="workspace-brand"><span><b>A.</b> Archimedes<span className="workspace-edition">RESEARCH WORKSPACE</span></span><button onClick={onToggle} aria-label="Close sidebar"><PanelLeftClose size={18} /></button></div>
        {/* New Research Button */}
        <button className="new-research-btn" onClick={onNewChat}>
          <Plus size={18} />
          New Research
        </button>

        <div className="sidebar-tools">
          <div className="history-group-label">Tools</div>
          <div className="sidebar-tools-list">
            <button className={`sidebar-action-btn ${showBookmarks ? 'active' : ''}`} onClick={onToggleBookmarks}>
              <Star size={16} />
              Reading List
            </button>
            <button className={`sidebar-action-btn ${showStudio ? 'active' : ''}`} onClick={onToggleStudio}>
              <PenTool size={16} />
              Manuscript Studio
            </button>
          </div>
        </div>

        {/* History */}
        <div className="history-section">
          <div className="history-group-label">Research History</div>
          {history.length === 0 ? (
            <div className="history-empty">
              No research sessions yet. Start by asking a question!
            </div>
          ) : (
            <div className="history-list">
              {history.map((session: any) => (
                <div key={session.id} className="history-item">
                  <button className="history-load" onClick={() => onLoadSession(session.id)}>
                    <MessageSquare size={14} className="history-icon" />
                    <span className="truncate">{session.query}</span>
                  </button>
                  <button
                    className="history-del"
                    onClick={() => onDeleteSession(session.id)}
                    title="Delete session"
                    aria-label={`Delete research: ${session.query}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profile at Bottom */}
        <div className="sidebar-profile">
          <div className="profile-card">
            <div className="profile-avatar">
              {user.username?.charAt(0).toUpperCase()}
            </div>
            <div className="profile-info">
              <div className="profile-name">{user.username}</div>
              <div className="profile-email">{user.email}</div>
            </div>
            <button className="logout-btn" onClick={onLogout} title="Sign out" aria-label="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
