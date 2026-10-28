import { apiFetch } from '../api';
import { useState, useEffect } from 'react';
import { PenTool, CheckSquare, Square, Loader, ChevronLeft, Save } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ManuscriptStudio({ user, onClose }: { user: any, onClose: () => void }) {
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [section, setSection] = useState('Introduction');
  const [notes, setNotes] = useState('');
  const [draft, setDraft] = useState('');
  const [isDrafting, setIsDrafting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch(`/api/bookmarks/?user_id=${user.id}`)
      .then(res => res.json())
      .then(data => {
        const papers = data.map((bookmark: any) => bookmark.paper);
        setBookmarks(papers);
        // Select all by default
        setSelectedPapers(new Set(papers.map((p: any) => p.title)));
      })
      .catch(err => console.error("Failed to load bookmarks", err));
  }, [user.id]);

  const togglePaper = (title: string) => {
    const newSet = new Set(selectedPapers);
    if (newSet.has(title)) newSet.delete(title);
    else newSet.add(title);
    setSelectedPapers(newSet);
  };

  const handleGenerate = async () => {
    if (!notes.trim()) {
      setError("Please provide some notes or bullet points to generate the draft from.");
      return;
    }
    
    setIsDrafting(true);
    setError('');
    
    const papersToInclude = bookmarks.filter(p => selectedPapers.has(p.title));

    try {
      const res = await apiFetch('/api/draft/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section,
          notes,
          papers: papersToInclude
        })
      });

      if (!res.ok) throw new Error("Failed to generate draft");
      const data = await res.json();
      setDraft(data.draft);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setIsDrafting(false);
    }
  };

  const handleExport = () => {
    const blob = new Blob([draft], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `archimedes_${section.toLowerCase()}_draft.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="studio-container">
      <div className="studio-header">
        <button className="studio-back-btn" onClick={onClose}>
          <ChevronLeft size={16} />
          Back to Research
        </button>
        <div className="studio-title">
          <PenTool size={18} className="text-accent" />
          Manuscript Studio
        </div>
      </div>

      <div className="studio-layout">
        <div className="studio-sidebar">
          <h3>Select References</h3>
          <p className="studio-help">These bookmarked papers will be used for in-text citations.</p>
          
          <div className="studio-paper-list">
            {bookmarks.length === 0 ? (
              <div className="studio-empty">No bookmarked papers found. Please bookmark papers in your research chat first!</div>
            ) : (
              bookmarks.map((p, i) => (
                <button type="button"
                  key={i} 
                  className={`studio-paper-item ${selectedPapers.has(p.title) ? 'selected' : ''}`}
                  onClick={() => togglePaper(p.title)}
                  aria-pressed={selectedPapers.has(p.title)}
                >
                  {selectedPapers.has(p.title) ? <CheckSquare size={16} className="text-accent" /> : <Square size={16} />}
                  <div className="studio-paper-title">{p.title}</div>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="studio-main">
          <div className="studio-controls">
            <select aria-label="Manuscript section" className="studio-select" value={section} onChange={e => setSection(e.target.value)}>
              <option value="Introduction">Introduction</option>
              <option value="Literature Review">Literature Review</option>
              <option value="Discussion">Discussion</option>
              <option value="Conclusion">Conclusion</option>
            </select>
          </div>

          <textarea 
            aria-label="Manuscript notes"
            maxLength={20000}
            className="studio-notes-input"
            placeholder="Paste your rough notes, bullet points, or experimental results here... Archimedes will expand these into a full academic draft with citations."
            value={notes}
            onChange={e => setNotes(e.target.value)}
          />
          
          {error && <div className="studio-error">{error}</div>}

          <button 
            className="studio-generate-btn" 
            onClick={handleGenerate}
            disabled={isDrafting || bookmarks.length === 0 || !notes.trim()}
          >
            {isDrafting ? <><Loader size={16} className="spin" /> Drafting {section}...</> : <><PenTool size={16} /> Generate Draft</>}
          </button>

          {draft && (
            <div className="studio-result">
              <p className="workspace-notice">Provisional draft based on supplied excerpts. Verify each claim and citation against the original papers before using it.</p>
              <div className="studio-result-header">
                <h3>Draft: {section}</h3>
                <button className="studio-export-btn" onClick={handleExport}>
                  <Save size={14} /> Export .md
                </button>
              </div>
              <div className="studio-markdown">
                <ReactMarkdown>{draft}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
