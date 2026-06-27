import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, ChevronDown, Sparkles, Clock, Download, FileText, Table, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import KnowledgeGraph from './KnowledgeGraph';
import PaperList from './PaperList';
import Timeline from './Timeline';
import PdfUpload from './PdfUpload';
import DataMatrix from './DataMatrix';

const CitationTooltip = ({ sourceName, report }: { sourceName: string, report: any }) => {
  const allPapers = [...(report?.seminal || []), ...(report?.citations || [])];
  const paper = allPapers.find(p => 
    p.title && sourceName && (
      p.title.toLowerCase().includes(sourceName.toLowerCase().substring(0, 15)) || 
      sourceName.toLowerCase().includes(p.title.toLowerCase().substring(0, 15))
    )
  );
  
  if (!paper) {
    return <span className="citation-source-text">{sourceName}</span>;
  }

  return (
    <div className="citation-tooltip-wrapper">
      <span className="citation-source-text interactive">{sourceName}</span>
      <div className="citation-tooltip-content">
        <h4>{paper.title}</h4>
        <div className="tooltip-meta">
          {paper.authors && <span>{Array.isArray(paper.authors) ? paper.authors.slice(0,2).join(', ') : paper.authors}</span>}
          {paper.year && <span> · {paper.year}</span>}
        </div>
        {paper.abstract && (
          <p>{paper.abstract.substring(0, 150)}...</p>
        )}
        {paper.url && (
          <a href={paper.url} target="_blank" rel="noopener noreferrer">View Paper</a>
        )}
      </div>
    </div>
  );
};

const SUGGESTIONS = [
  { icon: '🔬', text: 'Transformer attention mechanisms in NLP' },
  { icon: '🧬', text: 'CRISPR gene editing recent advances' },
  { icon: '⚛️', text: 'Quantum computing error correction' },
  { icon: '🌍', text: 'Climate change mitigation strategies' },
];

const REJECTION_SUGGESTIONS = [
  'Large language model architectures',
  'Neural network optimization techniques',
  'Reinforcement learning in robotics',
];

const SYNTHESIS_TABS = [
  { key: 'overview', label: 'Overview', icon: '📋' },
  { key: 'methodology_comparison', label: 'Methods', icon: '⚙️' },
  { key: 'contradictions', label: 'Contradictions', icon: '⚡' },
  { key: 'research_gaps', label: 'Research Gaps', icon: '🔍' },
  { key: 'key_findings', label: 'Key Findings', icon: '💡' },
];

export default function Chat({ user, chatHistory, setChatHistory, onNewSession }: any) {
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentLogs, setAgentLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [activeSynthTab, setActiveSynthTab] = useState<Record<number, string>>({});
  const [showExportMenu, setShowExportMenu] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const prevChatLen = useRef(chatHistory.length);
  const prevLogsLen = useRef(agentLogs.length);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    const savedScroll = sessionStorage.getItem('archimedes_chat_scroll');
    if (savedScroll && listRef.current) {
      listRef.current.scrollTop = parseInt(savedScroll, 10);
    }
  }, []);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    sessionStorage.setItem('archimedes_chat_scroll', e.currentTarget.scrollTop.toString());
  };

  useEffect(() => {
    if (chatHistory.length > prevChatLen.current || agentLogs.length > prevLogsLen.current) {
      scrollToBottom();
    }
    prevChatLen.current = chatHistory.length;
    prevLogsLen.current = agentLogs.length;
  }, [chatHistory, agentLogs]);

  // Auto-resize textarea
  const adjustTextarea = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }
  }, []);

  useEffect(() => {
    adjustTextarea();
  }, [input, adjustTextarea]);

  // Close export menu on outside click
  useEffect(() => {
    const handler = () => setShowExportMenu(null);
    if (showExportMenu !== null) {
      document.addEventListener('click', handler);
      return () => document.removeEventListener('click', handler);
    }
  }, [showExportMenu]);

  // ── Get the active synthesis tab for a given message index ──
  const getSynthTab = (idx: number) => activeSynthTab[idx] || 'overview';

  // ── Determine if synthesis is structured (JSON object) or legacy (string) ──
  const isStructuredSynthesis = (synthesis: any): synthesis is Record<string, any> => {
    return synthesis && typeof synthesis === 'object' && !Array.isArray(synthesis);
  };

  // ── Export handler ──
  const handleExport = async (format: string) => {
    // For now, generate client-side from report data
    // In a full implementation, this would call /api/export/
    setShowExportMenu(null);
    
    // Find the relevant report from chat history
    const reportMsg = chatHistory.find((m: any) => m.report);
    if (!reportMsg) return;

    const report = reportMsg.report;
    const allPapers = [
      ...(report.seminal || []),
      ...(report.citations || []),
      ...(report.citations_depth2 || []),
    ];

    // Deduplicate
    const seen = new Set<string>();
    const papers = allPapers.filter((p: any) => {
      if (seen.has(p.title)) return false;
      seen.add(p.title);
      return true;
    });

    let content = '';
    let filename = '';
    let mimeType = 'text/plain';

    if (format === 'bibtex') {
      content = papers.map((p: any, i: number) => {
        const authors = Array.isArray(p.authors) ? p.authors.join(' and ') : 'Unknown';
        const key = p.authors?.[0]?.split(' ').pop()?.toLowerCase() || `paper${i}`;
        return `@article{${key}${p.year || ''},\n  title={${p.title}},\n  author={${authors}},\n  year={${p.year || 'n.d.'}}\n}`;
      }).join('\n\n');
      filename = 'archimedes_export.bib';
    } else if (format === 'csv') {
      content = 'Title,Authors,Year,Source,Citations,Abstract\n';
      content += papers.map((p: any) => {
        const authors = Array.isArray(p.authors) ? p.authors.join('; ') : '';
        const abstract = (p.abstract || '').replace(/"/g, '""');
        return `"${p.title}","${authors}","${p.year || ''}","${p.source || ''}","${p.citations || 0}","${abstract}"`;
      }).join('\n');
      filename = 'archimedes_export.csv';
      mimeType = 'text/csv';
    } else if (format === 'apa') {
      content = papers.map((p: any) => {
        const authors = p.authors || [];
        let authorStr = 'Unknown Author';
        if (Array.isArray(authors) && authors.length > 0) {
          authorStr = authors.length > 2 ? `${authors[0]} et al.` : authors.join(' & ');
        }
        return `${authorStr} (${p.year || 'n.d.'}). ${p.title}. ${p.source || ''}.`;
      }).join('\n\n');
      filename = 'archimedes_export_apa.txt';
    } else if (format === 'ris') {
      content = papers.map((p: any) => {
        let ris = 'TY  - JOUR\n';
        ris += `TI  - ${p.title || 'Unknown Title'}\n`;
        if (Array.isArray(p.authors)) {
          p.authors.forEach((a: string) => {
            ris += `AU  - ${a}\n`;
          });
        }
        if (p.year) ris += `PY  - ${p.year}\n`;
        if (p.source) ris += `JO  - ${p.source}\n`;
        if (p.url) ris += `UR  - ${p.url}\n`;
        if (p.abstract) ris += `AB  - ${p.abstract}\n`;
        ris += 'ER  - \n';
        return ris;
      }).join('\n');
      filename = 'archimedes_export.ris';
      mimeType = 'application/x-research-info-systems';
    } else if (format === 'litreview') {
      try {
        const res = await fetch('http://localhost:8000/api/litreview/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: reportMsg.session_id || Date.now(), user_id: user.id }) // Fallback session id if not set
        });
        if (res.ok) {
          const blobLit = await res.blob();
          const urlLit = URL.createObjectURL(blobLit);
          const aLit = document.createElement('a');
          aLit.href = urlLit;
          aLit.download = 'literature_review.md';
          aLit.click();
          URL.revokeObjectURL(urlLit);
        }
      } catch (err) {
        console.error('Failed to generate lit review:', err);
      }
      return;
    }

    // Download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const submitQuery = async (query: string) => {
    if (!query.trim() || isProcessing) return;

    const userMsg = query.trim();
    setInput('');
    setChatHistory((prev: any[]) => [...prev, { role: 'user', content: userMsg }]);
    setIsProcessing(true);
    setAgentLogs([]);
    setShowLogs(false);

    // Find the last report in history to send as context for follow-ups
    const lastReportMsg = [...chatHistory].reverse().find(m => m.report);
    const existingReport = lastReportMsg ? lastReportMsg.report : null;

    try {
      const response = await fetch('http://localhost:8000/api/research/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMsg, 
          user_id: user.id,
          chat_history: chatHistory,
          existing_report: existingReport
        }),
      });

      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let aiContent = '';
      let reportData = null;
      let isOffTopic = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.type === 'log') {
                setAgentLogs(prev => [...prev, parsed.data]);
              } else if (parsed.type === 'error') {
                aiContent = parsed.data;
                // Check if this is an off-topic rejection
                if (parsed.data.includes('specialized') || parsed.data.includes('research-related')) {
                  isOffTopic = true;
                }
              } else if (parsed.type === 'followup_complete') {
                aiContent = parsed.data.answer;
              } else if (parsed.type === 'complete') {
                reportData = parsed.data;
                const elapsed = parsed.data.elapsed_seconds
                  ? ` in **${parsed.data.elapsed_seconds}s**`
                  : '';
                aiContent = `Research complete. I found **${parsed.data.total_crawled} papers** across 4 databases with 2 levels of citation tracing for *"${userMsg}"*${elapsed}.`;
              }
            } catch (err) {
              console.error('Error parsing SSE:', err, dataStr);
            }
          }
        }
      }

      setChatHistory((prev: any[]) => [
        ...prev,
        { role: 'assistant', content: aiContent, report: reportData, offTopic: isOffTopic },
      ]);
      onNewSession();
    } catch (err) {
      console.error(err);
      setChatHistory((prev: any[]) => [
        ...prev,
        { role: 'assistant', content: `An error occurred while connecting to the server: ${(err as any).message || String(err)}` },
      ]);
    } finally {
      setIsProcessing(false);
      setAgentLogs([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    submitQuery(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitQuery(input);
    }
  };

  // ── Render the synthesis section (structured or legacy) ──
  const renderSynthesis = (synthesis: any, msgIdx: number) => {
    if (!synthesis) return null;

    // Legacy string synthesis
    if (typeof synthesis === 'string') {
      if (synthesis.includes('Failed')) return null;
      return (
        <div className="synthesis-box">
          <div className="synthesis-header">
            <Sparkles size={14} />
            AI Synthesis
          </div>
          <ReactMarkdown>{synthesis}</ReactMarkdown>
        </div>
      );
    }

    // Structured synthesis
    if (isStructuredSynthesis(synthesis)) {
      const currentTab = getSynthTab(msgIdx);
      return (
        <div className="synth-structured">
          <div className="synth-tabs">
            {SYNTHESIS_TABS.map(tab => (
              <button
                key={tab.key}
                className={`synth-tab ${currentTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveSynthTab(prev => ({ ...prev, [msgIdx]: tab.key }))}
              >
                <span className="synth-tab-icon">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
          <div className="synth-tab-content">
            {currentTab === 'key_findings' ? (
              <div className="synth-findings">
                {Array.isArray(synthesis.key_findings) ? (
                  synthesis.key_findings.map((finding: any, i: number) => {
                    const text = typeof finding === 'string' ? finding : finding.text;
                    const conf = typeof finding === 'string' ? 'MEDIUM' : finding.confidence;
                    const confColor = conf === 'HIGH' ? '#a6e3a1' : conf === 'LOW' ? '#f38ba8' : '#f9e2af';
                    
                    return (
                      <div key={i} className="synth-finding-item">
                        <span className="synth-finding-number">{i + 1}</span>
                        <div style={{ flex: 1 }}>
                          <ReactMarkdown>{text}</ReactMarkdown>
                            {typeof finding === 'object' && finding.sources?.length > 0 && (
                              <div className="synth-finding-sources">
                                <strong>Sources:</strong>{' '}
                                {finding.sources.map((src: string, srcIdx: number) => (
                                  <span key={srcIdx}>
                                    <CitationTooltip sourceName={src} report={chatHistory[msgIdx].report} />
                                    {srcIdx < finding.sources.length - 1 ? ', ' : ''}
                                  </span>
                                ))}
                              </div>
                            )}
                        </div>
                        <div className="synth-confidence" style={{ color: confColor, borderColor: confColor + '40', background: confColor + '15' }}>
                          {conf} Confidence
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <ReactMarkdown>{String(synthesis.key_findings || 'No findings available.')}</ReactMarkdown>
                )}
              </div>
            ) : (
              <ReactMarkdown>{String(synthesis[currentTab] || 'Not available for this query.')}</ReactMarkdown>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="chat-container">
      {chatHistory.length === 0 ? (
        /* ── Empty State ── */
        <div className="chat-empty">
          <div className="empty-logo">🧬</div>
          <h2 className="empty-greeting">
            Hello, {user.username} <span className="wave-emoji">👋</span>
          </h2>
          <p className="empty-subtitle">What would you like to research today?</p>

          <div className="suggestion-grid">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => submitQuery(s.text)}
              >
                <span className="chip-icon">{s.icon}</span>
                <span className="chip-text">{s.text}</span>
              </button>
            ))}
          </div>
          <div style={{ marginTop: '32px', width: '100%', maxWidth: '520px' }}>
            <PdfUpload user={user} onComplete={() => setAgentLogs([])} />
          </div>
        </div>
      ) : (
        /* ── Messages ── */
        <div className="messages-list" ref={listRef} onScroll={handleScroll}>
          {chatHistory.map((msg: any, msgIdx: number) => (
            <div key={msgIdx} className={`message-wrapper ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user'
                  ? user.username?.charAt(0).toUpperCase()
                  : '🧬'}
              </div>
              <div className="message-content">
                {/* Off-topic rejection card */}
                {msg.offTopic ? (
                  <div className="rejection-card">
                    <div className="rejection-header">
                      <div className="rejection-icon">🎯</div>
                      <div className="rejection-title">Research Queries Only</div>
                    </div>
                    <div className="rejection-body">
                      I'm specialized for academic research — searching papers, tracing citations, and synthesizing findings. Try asking about a research topic instead!
                    </div>
                    <div className="rejection-suggestions">
                      {REJECTION_SUGGESTIONS.map((rs, i) => (
                        <button
                          key={i}
                          className="rejection-chip"
                          onClick={() => submitQuery(rs)}
                        >
                          {rs}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>

                    {msg.report && (
                      <div className="report-card animate-fade-in">
                        {/* Stats Row + Elapsed Time + Export */}
                        <div className="report-top-bar">
                          <div className="report-stats">
                            <div className="stat">
                              <span className="stat-value">{msg.report.seminal?.length || 0}</span>
                              <span className="stat-label">Seminal</span>
                            </div>
                            <div className="stat">
                              <span className="stat-value">{msg.report.citations?.length || 0}</span>
                              <span className="stat-label">Depth-1</span>
                            </div>
                            <div className="stat">
                              <span className="stat-value">{msg.report.citations_depth2?.length || 0}</span>
                              <span className="stat-label">Depth-2</span>
                            </div>
                            <div className="stat highlight">
                              <span className="stat-value">{msg.report.total_crawled}</span>
                              <span className="stat-label">Total</span>
                            </div>
                          </div>
                          <div className="report-actions">
                            {msg.report.elapsed_seconds && (
                              <div className="elapsed-badge">
                                <Clock size={13} />
                                {msg.report.elapsed_seconds}s
                              </div>
                            )}
                            <div className="export-dropdown-wrapper" onClick={e => e.stopPropagation()}>
                              <button
                                className="export-btn"
                                onClick={() => setShowExportMenu(showExportMenu === msgIdx ? null : msgIdx)}
                              >
                                <Download size={14} />
                                Export
                              </button>
                              {showExportMenu === msgIdx && (
                                <div className="export-menu">
                                  <button onClick={() => handleExport('bibtex')}>
                                    <FileText size={14} />
                                    BibTeX (.bib)
                                  </button>
                                  <button onClick={() => handleExport('csv')}>
                                    <Table size={14} />
                                    CSV (.csv)
                                  </button>
                                  <button onClick={() => handleExport('apa')}>
                                    <BookOpen size={14} />
                                    APA (.txt)
                                  </button>
                                  <button onClick={() => handleExport('ris')}>
                                    <FileText size={14} />
                                    Zotero/EndNote (.ris)
                                  </button>
                                  <div className="export-menu-divider" style={{ borderTop: '1px solid var(--border)', margin: '4px 0' }} />
                                  <button onClick={() => handleExport('litreview')}>
                                    <Sparkles size={14} />
                                    Lit Review (.md)
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* AI Synthesis */}
                        {msg.report.ai_synthesis && renderSynthesis(msg.report.ai_synthesis, msgIdx)}

                        {/* Knowledge Graph */}
                        <KnowledgeGraph report={msg.report} />

                        {/* Data Extraction Matrix */}
                        <DataMatrix report={msg.report} />

                        {/* Timeline */}
                        <Timeline report={msg.report} />

                        {/* Paper List */}
                        <PaperList report={msg.report} user={user} />
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}

          {/* Processing / Thinking */}
          {isProcessing && (
            <div className="thinking-wrapper">
              <div className="thinking-avatar">🧬</div>
              <div className="thinking-content">
                <div className="thinking-shimmer">
                  <div className="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="thinking-label">
                    {agentLogs.length > 0
                      ? agentLogs[agentLogs.length - 1]
                      : 'Thinking...'}
                  </span>
                </div>

                {agentLogs.length > 0 && (
                  <>
                    <button
                      className="agent-logs-toggle"
                      onClick={() => setShowLogs(!showLogs)}
                    >
                      <ChevronDown
                        size={14}
                        className={`chevron ${showLogs ? 'open' : ''}`}
                      />
                      {showLogs ? 'Hide details' : 'Show details'}
                    </button>

                    {showLogs && (
                      <div className="agent-logs-container">
                        {agentLogs.map((log, i) => (
                          <div key={i} className="log-line">
                            <span className="log-caret">›</span>
                            {log}
                          </div>
                        ))}
                        <span className="log-cursor" />
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* ── Input ── */}
      <div className="input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a research question..."
            disabled={isProcessing}
            rows={1}
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="send-btn"
          >
            <Send size={18} />
          </button>
        </form>
        <div className="input-footer">
          Archimedes searches academic databases. Ask research questions only.
        </div>
      </div>
    </div>
  );
}
