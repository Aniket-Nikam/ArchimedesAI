import { apiFetch } from '../api';
import { useState, useRef, useEffect, useCallback, lazy, Suspense } from 'react';
import { Send, ChevronDown, Sparkles, Clock, Download, FileText, Table, BookOpen } from 'lucide-react';
import ReactMarkdown from './ResearchMarkdown';
import { readEvents } from '../sse';
const KnowledgeGraph = lazy(() => import('./KnowledgeGraph'));
import PaperList from './PaperList';
import Timeline from './Timeline';
import PdfUpload from './PdfUpload';
import DataMatrix from './DataMatrix';

const CitationTooltip = ({ sourceName, report }: { sourceName: string, report: any }) => {
  const allPapers = [...(report?.seminal || []), ...(report?.citations || [])];
  const paper = allPapers.find(p => 
    p.title && sourceName && (
      p.title.trim().toLowerCase() === sourceName.trim().toLowerCase()
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
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => { abortRef.current?.abort(); }, []);
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

  const [exportError, setExportError] = useState('');
  const handleExport = async (format: string, messageIndex: number) => {
    setShowExportMenu(null);
    setExportError('');
    const sessionId = chatHistory[messageIndex]?.report?.session_id;
    if (!sessionId) { setExportError('Reload this saved report from history before exporting.'); return; }
    try {
      const response = await apiFetch(format === 'litreview' ? '/api/litreview/' : '/api/export/', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, format }),
      });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const extensions: Record<string,string> = { bibtex: 'bib', csv: 'csv', apa: 'txt', ris: 'ris', litreview: 'md' };
      link.download = `archimedes_${sessionId}.${extensions[format]}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) { setExportError((error as Error).message); }
  };


  const jobRef = useRef<string | null>(null);
  const streamRef = useRef<(job: string, query: string, controller: AbortController) => Promise<void>>(async () => {});
  const aliveRef = useRef(true);
  useEffect(() => { aliveRef.current = true; return () => { aliveRef.current = false; }; }, []);
  const historyState = useRef({length:chatHistory.length,set:setChatHistory});
  historyState.current = {length:chatHistory.length,set:setChatHistory};
  const storageKey = `archimedes_job_${user.id}`;
  const [searchOnly, setSearchOnly] = useState(false);

  const consumeJob = async (job: string, query: string, controller: AbortController) => {
    jobRef.current = job;
    abortRef.current = controller;
    sessionStorage.setItem(storageKey, job);
    setIsProcessing(true);
    try {
      const response = await apiFetch(`/api/research/jobs/${job}/events`, { signal: controller.signal });
      if (!response.body) throw new Error('Streaming is unavailable.');
      let answer = '';
      let report = null;
      let terminal = false;
      for await (const event of readEvents(response.body)) {
        if (!aliveRef.current || controller.signal.aborted) return;
        if (event.type === 'log') setAgentLogs(previous => [...previous.slice(-99), String(event.data)]);
        if (event.type === 'error') { terminal = true; answer = String(event.data); }
        if (event.type === 'followup_complete') { terminal = true; answer = event.data.answer; }
        if (event.type === 'complete') {
          terminal = true; report = event.data;
          answer = `Research saved: **${report.total_crawled} unique papers** for *"${query}"* in **${report.elapsed_seconds}s**. Inspect the evidence and source coverage below.`;
        }
      }
      if (!terminal) throw new Error('Connection interrupted. Reload to reconnect to the saved research job.');
      sessionStorage.removeItem(storageKey);
      if (aliveRef.current) {
        setChatHistory((previous: any[]) => [...previous, { role: 'assistant', content: answer, report }]);
        onNewSession();
      }
    } catch (error) {
      if (aliveRef.current && !controller.signal.aborted) setChatHistory((previous: any[]) => [...previous, { role: 'assistant', content: (error as Error).message + ' Your job is retained; reload to reconnect.' }]);
    } finally {
      if (aliveRef.current) { setIsProcessing(false); setAgentLogs([]); }
      abortRef.current = null;
      jobRef.current = null;
    }
  };
  streamRef.current = consumeJob;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const restore = async () => {
      try {
        const remembered = sessionStorage.getItem(`archimedes_job_${user.id}`);
        const response = await apiFetch(remembered ? `/api/research/jobs/${remembered}` : '/api/research/jobs/active', {signal: controller.signal});
        const job = await response.json();
        if (!active || !job) return;
        if (historyState.current.length === 0) historyState.current.set([{role:'user',content:job.query}]);
        await streamRef.current(job.id, job.query, controller);
      } catch { /* a missing remembered job must not break the workspace */ }
    };
    void restore();
    return () => { active = false; controller.abort(); };
  }, [user.id]);

  const submitQuery = async (query: string) => {
    if (!query.trim() || isProcessing || jobRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setIsProcessing(true); setInput(''); setAgentLogs([]); setShowLogs(false);
    setChatHistory((previous: any[]) => [...previous, {role:'user',content:query.trim()}]);
    try {
      const lastReport = [...chatHistory].reverse().find(message => message.report)?.report;
      const response = await apiFetch('/api/research/jobs', {
        method:'POST', signal:controller.signal, headers:{'Content-Type':'application/json'},
        body:JSON.stringify({query:query.trim(),mode:searchOnly ? 'search':'synthesis',chat_history:chatHistory.slice(-10).map((message: any) => ({role:message.role,content:message.content})),existing_report:lastReport}),
      });
      const {job_id} = await response.json();
      if (!aliveRef.current) return;
      await consumeJob(job_id,query.trim(),controller);
    } catch (error) {
      if (aliveRef.current && !controller.signal.aborted) setChatHistory((previous: any[]) => [...previous,{role:'assistant',content:(error as Error).message}]);
      if (aliveRef.current) setIsProcessing(false);
    }
  };

  const stopResearch = async () => {
    if (!jobRef.current) return;
    try {
      await apiFetch(`/api/research/jobs/${jobRef.current}`,{method:'DELETE'});
      abortRef.current?.abort();
      sessionStorage.removeItem(storageKey);
      setChatHistory((previous: any[]) => [...previous,{role:'assistant',content:'Research cancelled.'}]);
      setIsProcessing(false);
    } catch (error) { setExportError((error as Error).message); }
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
      {exportError && <div className="workspace-notice" role="alert">{exportError}<button onClick={() => setExportError('')} aria-label="Dismiss export error">×</button></div>}
      {chatHistory.length === 0 ? (
        /* ── Empty State ── */
        <div className="chat-empty">
          <div className="empty-logo" aria-hidden="true">A.</div>
          <h2 className="empty-greeting">
            Follow a better question.
          </h2>
          <p className="empty-subtitle">Discover papers, connect the evidence, and make room for your next idea.</p>

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
          <div className="research-upload">
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
                                  <button onClick={() => handleExport('bibtex', msgIdx)}>
                                    <FileText size={14} />
                                    BibTeX (.bib)
                                  </button>
                                  <button onClick={() => handleExport('csv', msgIdx)}>
                                    <Table size={14} />
                                    CSV (.csv)
                                  </button>
                                  <button onClick={() => handleExport('apa', msgIdx)}>
                                    <BookOpen size={14} />
                                    APA (.txt)
                                  </button>
                                  <button onClick={() => handleExport('ris', msgIdx)}>
                                    <FileText size={14} />
                                    Zotero/EndNote (.ris)
                                  </button>
                                  <div className="export-menu-divider" style={{ borderTop: '1px solid var(--border)', margin: '4px 0' }} />
                                  <button onClick={() => handleExport('litreview', msgIdx)}>
                                    <Sparkles size={14} />
                                    Lit Review (.md)
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="source-coverage" aria-label="Source coverage">
                          {(msg.report.source_status || []).map((source: any) => (
                            <span key={source.source} className={source.status === 'results' ? 'source-ok' : 'source-warning'}>
                              {source.source}: {source.status === 'results' ? `${source.count} results` : source.status.replaceAll('_', ' ')}
                            </span>
                          ))}
                          <p>Retraction metadata is limited. An unknown status does not establish that a paper is safe.</p>
                        </div>
                        {/* AI Synthesis */}
                        {msg.report.ai_synthesis?.evidence_review && <p className="workspace-caption">Citation identity checks: {msg.report.ai_synthesis.evidence_review.unmatched_citations} unmatched references. A matched paper does not by itself verify a claim; inspect the linked evidence.</p>}
                        {msg.report.ai_synthesis && renderSynthesis(msg.report.ai_synthesis, msgIdx)}

                        {/* Knowledge Graph */}
                        <Suspense fallback={<p className="workspace-caption">Loading citation graph…</p>}><KnowledgeGraph report={msg.report} /></Suspense>

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
        <label className="research-mode"><input type="checkbox" checked={searchOnly} onChange={event => setSearchOnly(event.target.checked)} disabled={isProcessing} /> Paper search only (no AI synthesis)</label>
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Research question"
            maxLength={1000}
            placeholder="Ask a research question..."
            disabled={isProcessing}
            rows={1}
          />
          <button
            type="submit"
            aria-label="Start research"
            disabled={!input.trim() || isProcessing}
            className="send-btn"
          >
            <Send size={18} />
          </button>
        </form>
        {isProcessing && <button type="button" className="stop-research" onClick={stopResearch}>Stop research</button>}
        <div className="input-footer">
          AI can make mistakes. Verify findings against the original papers.
        </div>
      </div>
    </div>
  );
}
