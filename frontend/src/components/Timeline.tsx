import { useMemo, useRef, useState } from 'react';

interface TimelinePaper {
  title: string;
  year: string | number;
  source?: string;
  citations?: number;
  authors?: string[];
  url?: string;
}

const SOURCE_COLORS: Record<string, string> = {
  'Semantic Scholar': '#89b4fa',
  'arXiv': '#f9e2af',
  'arXiv (Reference)': '#f9e2af',
  'arXiv (D2)': '#f9e2af',
  'PubMed': '#a6e3a1',
  'Google Scholar': '#f38ba8',
  'Semantic Scholar (D2)': '#89b4fa',
};

export default function Timeline({ report }: { report: any }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [selectedPaper, setSelectedPaper] = useState<TimelinePaper | null>(null);

  const { papers, yearGroups, years } = useMemo(() => {
    if (!report) return { papers: [], yearGroups: {}, years: [] };

    const all: TimelinePaper[] = [
      ...(report.seminal || []),
      ...(report.citations || []),
      ...(report.citations_depth2 || []),
    ];

    // Deduplicate and filter papers with valid years
    const seen = new Set<string>();
    const valid = all.filter(p => {
      const year = parseInt(String(p.year));
      if (!year || year < 1950 || year > 2030 || seen.has(p.title)) return false;
      seen.add(p.title);
      return true;
    });

    // Group by year
    const groups: Record<number, TimelinePaper[]> = {};
    valid.forEach(p => {
      const y = parseInt(String(p.year));
      if (!groups[y]) groups[y] = [];
      groups[y].push(p);
    });

    const sortedYears = Object.keys(groups).map(Number).sort((a, b) => a - b);

    return { papers: valid, yearGroups: groups, years: sortedYears };
  }, [report]);

  if (papers.length < 3 || years.length < 2) return null;

  const maxCitations = Math.max(...papers.map(p => p.citations || 0), 1);

  return (
    <div className="tl-container">
      <div className="tl-header">
        <span className="tl-header-icon">📅</span>
        <span className="tl-header-title">Research Timeline</span>
        <span className="tl-header-range">{years[0]} — {years[years.length - 1]}</span>
      </div>

      <div className="tl-scroll" ref={scrollRef}>
        <div className="tl-track">
          <div className="tl-line" />
          {years.map((year) => {
            const group = yearGroups[year] || [];
            const isCluster = group.length >= 3;
            return (
              <div key={year} className="tl-year-group">
                <div className="tl-year-marker">
                  <div className={`tl-year-dot ${isCluster ? 'cluster' : ''}`} />
                  <span className="tl-year-label">{year}</span>
                </div>
                <div className="tl-papers">
                  {group.map((paper, pi) => {
                    const size = 8 + ((paper.citations || 0) / maxCitations) * 20;
                    const color = SOURCE_COLORS[paper.source || ''] || '#888';
                    return (
                      <button
                        key={pi}
                        className={`tl-paper-dot ${selectedPaper?.title === paper.title ? 'selected' : ''}`}
                        style={{
                          width: `${size}px`,
                          height: `${size}px`,
                          backgroundColor: color,
                        }}
                        title={paper.title}
                        onClick={() => setSelectedPaper(selectedPaper?.title === paper.title ? null : paper)}
                      />
                    );
                  })}
                </div>
                {isCluster && (
                  <div className="tl-cluster-label">
                    {group.length} papers
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {selectedPaper && (
        <div className="tl-detail">
          <h4 className="tl-detail-title">{selectedPaper.title}</h4>
          <div className="tl-detail-meta">
            {selectedPaper.authors && Array.isArray(selectedPaper.authors) && (
              <span>{selectedPaper.authors.slice(0, 3).join(', ')}{selectedPaper.authors.length > 3 ? ' et al.' : ''}</span>
            )}
            <span>· {selectedPaper.year}</span>
            {selectedPaper.citations ? <span>· {selectedPaper.citations} citations</span> : null}
          </div>
          {selectedPaper.url && (
            <a href={selectedPaper.url} target="_blank" rel="noopener noreferrer" className="tl-detail-link">
              Open Paper →
            </a>
          )}
        </div>
      )}
    </div>
  );
}
