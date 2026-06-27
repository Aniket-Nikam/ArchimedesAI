import { useState, useMemo, useCallback, useEffect } from 'react';
import { ArrowUpDown, Copy, Check, ExternalLink, Star, AlertTriangle } from 'lucide-react';

type SortKey = 'year' | 'citations' | 'title';

const SOURCE_COLORS: Record<string, string> = {
  'Semantic Scholar': '#89b4fa',
  'arXiv': '#f9e2af',
  'arXiv (Reference)': '#f9e2af',
  'arXiv (D2)': '#f9e2af',
  'PubMed': '#a6e3a1',
  'Google Scholar': '#f38ba8',
  'Semantic Scholar (D2)': '#89b4fa',
};

export default function PaperList({ report, user }: { report: any, user: any }) {
  const [sortKey, setSortKey] = useState<SortKey>('citations');
  const [sortAsc, setSortAsc] = useState(false);
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [bookmarkedTitles, setBookmarkedTitles] = useState<Set<string>>(new Set());

  // Combine + deduplicate
  const allPapers = useMemo(() => {
    if (!report) return [];
    const combined = [
      ...(report.seminal || []),
      ...(report.citations || []),
      ...(report.citations_depth2 || []),
    ];
    return Array.from(new Map(combined.map((p: any) => [p.title, p])).values());
  }, [report]);

  // Fetch bookmarks
  useEffect(() => {
    if (!user) return;
    fetch(`http://localhost:8000/api/bookmarks/?user_id=${user.id}`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setBookmarkedTitles(new Set(data.map((b: any) => b.paper_title)));
        }
      })
      .catch(console.error);
  }, [user]);

  // Toggle Bookmark
  const toggleBookmark = async (paper: any) => {
    if (!user) return;
    const isBookmarked = bookmarkedTitles.has(paper.title);
    
    try {
      if (isBookmarked) {
        await fetch('http://localhost:8000/api/bookmarks/', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: user.id, paper_title: paper.title })
        });
        setBookmarkedTitles(prev => {
          const next = new Set(prev);
          next.delete(paper.title);
          return next;
        });
      } else {
        await fetch('http://localhost:8000/api/bookmarks/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: user.id, paper: paper })
        });
        setBookmarkedTitles(prev => {
          const next = new Set(prev);
          next.add(paper.title);
          return next;
        });
      }
    } catch (e) {
      console.error('Bookmark failed', e);
    }
  };

  // Get unique sources for filter chips
  const sources = useMemo(() => {
    const s = new Set<string>();
    allPapers.forEach((p: any) => {
      // Normalize source names for filtering
      const src = p.source || 'Unknown';
      if (src.includes('arXiv')) s.add('arXiv');
      else if (src.includes('Semantic Scholar')) s.add('Semantic Scholar');
      else s.add(src);
    });
    return Array.from(s);
  }, [allPapers]);

  // Toggle filter
  const toggleFilter = useCallback((source: string) => {
    setActiveFilters(prev => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
    });
  }, []);

  // Filter + sort
  const displayedPapers = useMemo(() => {
    let filtered = allPapers;

    if (activeFilters.size > 0) {
      filtered = allPapers.filter((p: any) => {
        const src = p.source || 'Unknown';
        for (const f of activeFilters) {
          if (src.includes(f)) return true;
        }
        return false;
      });
    }

    return [...filtered].sort((a: any, b: any) => {
      let aVal: any, bVal: any;
      if (sortKey === 'year') {
        aVal = parseInt(a.year) || 0;
        bVal = parseInt(b.year) || 0;
      } else if (sortKey === 'citations') {
        aVal = a.citations || a.citationCount || 0;
        bVal = b.citations || b.citationCount || 0;
      } else {
        aVal = (a.title || '').toLowerCase();
        bVal = (b.title || '').toLowerCase();
      }
      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [allPapers, activeFilters, sortKey, sortAsc]);

  // Copy APA citation
  const copyAPA = useCallback((paper: any, idx: number) => {
    const authors = paper.authors || [];
    let authorStr = 'Unknown Author';
    if (Array.isArray(authors) && authors.length > 0) {
      authorStr = authors.length > 2
        ? `${authors[0]} et al.`
        : authors.join(' & ');
    }
    const citation = `${authorStr} (${paper.year || 'n.d.'}). ${paper.title}. ${paper.source || ''}.`;
    navigator.clipboard.writeText(citation);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  }, []);

  // Toggle sort
  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(prev => !prev);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  }, [sortKey]);

  if (!allPapers.length) return null;

  return (
    <div className="pl-container">
      <div className="pl-header">
        <h3 className="pl-title">
          <span>📄</span> Discovered Papers
          <span className="pl-count">{displayedPapers.length} of {allPapers.length}</span>
        </h3>
      </div>

      {/* Toolbar: filters + sort */}
      <div className="pl-toolbar">
        <div className="pl-filters">
          {sources.map(src => (
            <button
              key={src}
              className={`pl-filter-chip ${activeFilters.has(src) ? 'active' : ''}`}
              onClick={() => toggleFilter(src)}
              style={{
                '--chip-color': SOURCE_COLORS[src] || '#888',
              } as React.CSSProperties}
            >
              <span className="pl-filter-dot" style={{ backgroundColor: SOURCE_COLORS[src] || '#888' }} />
              {src}
            </button>
          ))}
        </div>
        <div className="pl-sort-buttons">
          <button
            className={`pl-sort-btn ${sortKey === 'citations' ? 'active' : ''}`}
            onClick={() => handleSort('citations')}
          >
            <ArrowUpDown size={12} />
            Citations
          </button>
          <button
            className={`pl-sort-btn ${sortKey === 'year' ? 'active' : ''}`}
            onClick={() => handleSort('year')}
          >
            <ArrowUpDown size={12} />
            Year
          </button>
          <button
            className={`pl-sort-btn ${sortKey === 'title' ? 'active' : ''}`}
            onClick={() => handleSort('title')}
          >
            <ArrowUpDown size={12} />
            Title
          </button>
        </div>
      </div>

      {/* Paper Grid */}
      <div className="pl-grid">
        {displayedPapers.map((paper: any, idx: number) => {
          const srcColor = SOURCE_COLORS[paper.source] || '#888';
          return (
            <div key={idx} className={`pl-card ${paper.retraction_status?.is_retracted ? 'retracted' : ''}`} style={{ '--card-accent': srcColor } as React.CSSProperties}>
              <div className="pl-card-accent" style={{ backgroundColor: paper.retraction_status?.is_retracted ? '#ff6b6b' : srcColor }} />
              <div className="pl-card-body">
                <div className="pl-card-header">
                  <h4 className="pl-card-title" title={paper.retraction_status?.is_retracted ? paper.retraction_status.retraction_reason : undefined}>
                    {paper.retraction_status?.is_retracted && <AlertTriangle size={14} className="retracted-icon" />}
                    {paper.title}
                  </h4>
                  <button 
                    className={`pl-bookmark-btn ${bookmarkedTitles.has(paper.title) ? 'active' : ''}`}
                    onClick={() => toggleBookmark(paper)}
                    title="Bookmark paper"
                  >
                    <Star size={16} fill={bookmarkedTitles.has(paper.title) ? 'currentColor' : 'none'} />
                  </button>
                </div>
                <div className="pl-card-meta">
                  {paper.authors && Array.isArray(paper.authors)
                    ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '')
                    : paper.authors}
                  {paper.year && <span> · {paper.year}</span>}
                </div>
                <p className="pl-card-abstract">
                  {paper.abstract || 'No abstract available.'}
                </p>
                <div className="pl-card-footer">
                  <div className="pl-card-badges">
                    <span className="pl-source-badge" style={{ color: srcColor, borderColor: srcColor + '40' }}>
                      {paper.source}
                    </span>
                    {(paper.citations || paper.citationCount) ? (
                      <span className="pl-citation-badge">
                        {paper.citations || paper.citationCount} cited
                      </span>
                    ) : null}
                  </div>
                  <div className="pl-card-actions">
                    <button
                      className="pl-action-btn"
                      onClick={() => copyAPA(paper, idx)}
                      title="Copy APA citation"
                    >
                      {copiedIdx === idx ? <Check size={13} /> : <Copy size={13} />}
                    </button>
                    {paper.url && (
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="pl-action-btn"
                        title="Open paper"
                      >
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
