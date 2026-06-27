import { useState, useEffect, useCallback } from 'react';
import { Star, Trash2, StickyNote, ExternalLink, BookOpen } from 'lucide-react';

export default function Bookmarks({ user, onClose }: { user: any; onClose: () => void }) {
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [sortBy, setSortBy] = useState<'recent' | 'citations'>('recent');

  const fetchBookmarks = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/bookmarks/?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setBookmarks(data);
      }
    } catch (e) {
      console.error('Failed to fetch bookmarks:', e);
    }
  }, [user.id]);

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  const removeBookmark = async (paperTitle: string) => {
    try {
      await fetch('http://localhost:8000/api/bookmarks/', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, paper_title: paperTitle }),
      });
      fetchBookmarks();
    } catch (e) {
      console.error('Failed to remove bookmark:', e);
    }
  };

  const saveNotes = async (paperTitle: string) => {
    try {
      await fetch('http://localhost:8000/api/bookmarks/notes', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, paper_title: paperTitle, notes: noteText }),
      });
      setEditingNotes(null);
      fetchBookmarks();
    } catch (e) {
      console.error('Failed to save notes:', e);
    }
  };

  const sorted = [...bookmarks].sort((a, b) => {
    if (sortBy === 'citations') {
      return (b.paper?.citations || 0) - (a.paper?.citations || 0);
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="bm-panel">
      <div className="bm-header">
        <div className="bm-header-left">
          <BookOpen size={16} />
          <h3>Reading List</h3>
          <span className="bm-count">{bookmarks.length}</span>
        </div>
        <button className="bm-close" onClick={onClose}>×</button>
      </div>

      <div className="bm-sort">
        <button className={sortBy === 'recent' ? 'active' : ''} onClick={() => setSortBy('recent')}>
          Recent
        </button>
        <button className={sortBy === 'citations' ? 'active' : ''} onClick={() => setSortBy('citations')}>
          Most Cited
        </button>
      </div>

      {sorted.length === 0 ? (
        <div className="bm-empty">
          <Star size={24} />
          <p>No bookmarks yet</p>
          <span>Star papers from search results to build your reading list.</span>
        </div>
      ) : (
        <div className="bm-list">
          {sorted.map((bm, i) => (
            <div key={i} className="bm-item">
              <div className="bm-item-main">
                <h4 className="bm-item-title">{bm.paper?.title || bm.paper_title}</h4>
                <div className="bm-item-meta">
                  {bm.paper?.authors && Array.isArray(bm.paper.authors) && (
                    <span>{bm.paper.authors.slice(0, 2).join(', ')}</span>
                  )}
                  {bm.paper?.year && <span> · {bm.paper.year}</span>}
                  {bm.paper?.citations ? <span> · {bm.paper.citations} cited</span> : null}
                </div>
                {bm.notes && editingNotes !== bm.paper_title && (
                  <div className="bm-item-notes">📝 {bm.notes}</div>
                )}
                {editingNotes === bm.paper_title && (
                  <div className="bm-notes-editor">
                    <textarea
                      value={noteText}
                      onChange={e => setNoteText(e.target.value)}
                      placeholder="Add your notes..."
                      rows={2}
                    />
                    <div className="bm-notes-actions">
                      <button onClick={() => saveNotes(bm.paper_title)}>Save</button>
                      <button onClick={() => setEditingNotes(null)}>Cancel</button>
                    </div>
                  </div>
                )}
              </div>
              <div className="bm-item-actions">
                <button
                  title="Add notes"
                  onClick={() => {
                    setEditingNotes(bm.paper_title);
                    setNoteText(bm.notes || '');
                  }}
                >
                  <StickyNote size={14} />
                </button>
                {bm.paper?.url && (
                  <a href={bm.paper.url} target="_blank" rel="noopener noreferrer" title="Open paper">
                    <ExternalLink size={14} />
                  </a>
                )}
                <button title="Remove" onClick={() => removeBookmark(bm.paper_title)}>
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
