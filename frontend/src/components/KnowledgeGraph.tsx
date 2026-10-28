import { useMemo, useState, useRef, useCallback } from 'react';
import {graphId,graphLayout} from '../graphLayout';
import { Search, ZoomIn, ZoomOut, Maximize2, X, ExternalLink, Copy } from 'lucide-react';

interface GraphNode {
  id: string;
  name: string;
  val: number;
  group: number;
  source?: string;
  year?: string | number;
  authors?: string[];
  abstract?: string;
  url?: string;
  citations?: number;
}

interface GraphLink {
  source: string;
  target: string;
}



const groupColors: Record<number, string> = {
  1: '#f38ba8',  // Seminal — rose
  2: '#89b4fa',  // Depth-1 — blue
  3: '#a6e3a1',  // Depth-2 — green
};

const groupLabels: Record<number, string> = {
  1: 'Search results',
  2: 'Depth-1',
  3: 'Depth-2',
};

export default function KnowledgeGraph({ report }: { report: any }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapPan,setMapPan] = useState({x:0,y:0});
  const dragRef = useRef<{x:number;y:number;panX:number;panY:number}|null>(null);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [visibleGroups, setVisibleGroups] = useState({ 1: true, 2: true, 3: true });

  const [copiedCitation, setCopiedCitation] = useState(false);
  const [mapZoom, setMapZoom] = useState(1);
  const [exploredNodes, setExploredNodes] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem('archimedes_explored_nodes');
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    if (node && node.id) {
      setExploredNodes(prev => {
        const next = new Set(prev);
        next.add(node.id);
        localStorage.setItem('archimedes_explored_nodes', JSON.stringify(Array.from(next)));
        return next;
      });
    }
  }, []);

  const { nodes, links } = useMemo(() => {
    if (!report) return { nodes: [], links: [] };

    const nodesMap = new Map<string, GraphNode>();
    const linksArray: GraphLink[] = [];

    const addNode = (paper: any, group: number): string => {
      const nodeId = paper.id || paper.url || paper.title;
      if (!nodesMap.has(nodeId)) {
        const citationCount = paper.citations || paper.citationCount || 0;
        nodesMap.set(nodeId, {
          id: nodeId,
          name: paper.title,
          val: group === 1 ? Math.max(5, Math.min(12, 3 + citationCount / 100)) :
               group === 2 ? Math.max(3, Math.min(8, 2 + citationCount / 200)) :
               Math.max(2, Math.min(5, 1 + citationCount / 300)),
          group,
          source: paper.source,
          year: paper.year,
          authors: paper.authors,
          abstract: paper.abstract,
          url: paper.url,
          citations: citationCount,
        });
      }
      return nodeId;
    };

    // Process seminal papers
    report.seminal?.forEach((p: any) => addNode(p, 1));

    // Process depth-1 citations
    report.citations?.forEach((p: any) => {
      const targetId = addNode(p, 2);
      if (p.cited_by && nodesMap.has(p.cited_by)) {
        linksArray.push({ source: p.cited_by, target: targetId });
      }
    });

    // Process depth-2 citations
    report.citations_depth2?.forEach((p: any) => {
      const targetId = addNode(p, 3);
      if (p.cited_by && nodesMap.has(p.cited_by)) {
        linksArray.push({ source: p.cited_by, target: targetId });
      }
    });

    // Remove orphan links
    const validLinks = linksArray.filter(l => nodesMap.has(l.source) && nodesMap.has(l.target));

    return {
      nodes: Array.from(nodesMap.values()),
      links: validLinks,
    };
  }, [report]);

  // ── Filter by visibility and search ──
  const filteredData = useMemo(() => {
    const visibleNodes = nodes.filter(n => {
      if (!visibleGroups[n.group as keyof typeof visibleGroups]) return false;
      if (searchTerm) {
        return n.name?.toLowerCase().includes(searchTerm.toLowerCase());
      }
      return true;
    });
    const visibleIds = new Set(visibleNodes.map(n => n.id));
    const visibleLinks = links.map(link => ({source:graphId(link.source),target:graphId(link.target)})).filter(link => visibleIds.has(link.source) && visibleIds.has(link.target));
    return { nodes: visibleNodes, links: visibleLinks };
  }, [nodes, links, visibleGroups, searchTerm]);

  const handleZoomIn = () => setMapZoom(value=>Math.min(3,value*1.2));
  const handleZoomOut = () => setMapZoom(value=>Math.max(.5,value/1.2));
  const handleFitView = () => {setMapZoom(1);setMapPan({x:0,y:0});};
  const positions = useMemo(()=>graphLayout(filteredData.nodes,filteredData.links.length>0),[filteredData]);

  // ── Copy citation ──
  const copyCitation = useCallback((node: GraphNode) => {
    const authors = node.authors;
    let authorStr = 'Unknown Author';
    if (authors && authors.length > 0) {
      authorStr = authors.length > 2
        ? `${authors[0]} et al.`
        : authors.join(' & ');
    }
    const citation = `${authorStr} (${node.year || 'n.d.'}). ${node.name}. ${node.source || ''}.`;
    navigator.clipboard.writeText(citation);
    setCopiedCitation(true);
    setTimeout(() => setCopiedCitation(false), 2000);
  }, []);

  if (!nodes.length) return null;

  return (
    <div className="kg-wrapper">
      <div className="kg-header">
        <div className="kg-title">
          <span className="kg-title-icon">🕸️</span>
          Citation Network
          <span className="kg-node-count">{filteredData.nodes.length} papers · {filteredData.links.length} citation links</span>
        </div>
        <div className="kg-controls">
          <div className="kg-search">
            <Search size={13} />
            <input
              type="text"
              placeholder="Search nodes..."
              aria-label="Search citation graph"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button className="kg-search-clear" onClick={() => setSearchTerm('')}>
                <X size={12} />
              </button>
            )}
          </div>
          <div className="kg-zoom-controls">
            <button onClick={handleZoomIn} title="Zoom in"><ZoomIn size={14} /></button>
            <button onClick={handleZoomOut} title="Zoom out"><ZoomOut size={14} /></button>
            <button onClick={handleFitView} title="Fit to view"><Maximize2 size={14} /></button>
          </div>
        </div>
      </div>

      {/* Legend with toggles */}
      <div className="kg-legend">
        {([1, 2, 3] as const).map(group => (
          <button
            key={group}
            className={`kg-legend-item ${!visibleGroups[group] ? 'dimmed' : ''}`}
            onClick={() => setVisibleGroups(prev => ({ ...prev, [group]: !prev[group] }))}
          >
            <span className="kg-legend-dot" style={{ backgroundColor: groupColors[group] }} />
            <span className="kg-legend-label">{groupLabels[group]}</span>
          </button>
        ))}
      </div>

      {links.length === 0 && <p className="kg-status" role="status">No citation links were retrieved{report.citation_status?.status==='rate_limited' ? ' because the citation service rate-limited this lookup' : ''}. These papers are shown as separate results; this does not establish that they are unrelated.</p>}
      {filteredData.nodes.length === 0 && <p className="kg-status" role="status">No papers match the current search and filters.</p>}
      <div className="kg-graph-area" ref={containerRef}>
        <svg className="kg-paper-map" viewBox="0 0 840 450" role="img" aria-label={filteredData.links.length ? 'Citation network showing retrieved relationships':'Paper map: results without retrieved citation links'}
          onPointerDown={event=>{if((event.target as Element).closest('[role="button"]'))return;dragRef.current={x:event.clientX,y:event.clientY,panX:mapPan.x,panY:mapPan.y};event.currentTarget.setPointerCapture(event.pointerId);}}
          onPointerMove={event=>{const drag=dragRef.current;if(drag)setMapPan({x:drag.panX+(event.clientX-drag.x),y:drag.panY+(event.clientY-drag.y)});}}
          onPointerUp={()=>{dragRef.current=null;}} onPointerCancel={()=>{dragRef.current=null;}}>
          <defs><marker id="citation-arrow" markerWidth="7" markerHeight="7" refX="12" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#8da5b0"/></marker></defs>
          <g transform={`translate(${420+mapPan.x} ${225+mapPan.y}) scale(${mapZoom}) translate(-420 -225)`}>
            {filteredData.links.map((link,index)=>{const source=positions.get(graphId(link.source));const target=positions.get(graphId(link.target));return source&&target ? <line key={index} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#8da5b0" strokeOpacity=".5" strokeWidth="1.2" markerEnd="url(#citation-arrow)"/>:null;})}
            {filteredData.nodes.map(node=>{const position=positions.get(node.id)!;return <g key={node.id} role="button" tabIndex={0} aria-label={`Inspect paper: ${node.name}`} onClick={()=>handleNodeClick(node)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();handleNodeClick(node);}}} className="kg-map-node">
              <title>{node.name}</title><circle cx={position.x} cy={position.y} r={selectedNode?.id===node.id?12:9} fill={groupColors[node.group]} stroke={exploredNodes.has(node.id)?'#80cbb8':'#eeeae1'} strokeWidth="1.5"/>
              <text x={position.x} y={position.y+24} textAnchor="middle" fill="#eeeae1" fontSize="10">{node.name?.length>27?node.name.slice(0,25)+'…':node.name}</text>
              <text x={position.x} y={position.y+37} textAnchor="middle" fill="#b8c6cc" fontSize="9">{node.year||'Year unavailable'}</text>
            </g>;})}
          </g>
        </svg>
      </div>
      {filteredData.links.length>0 && <p className="kg-status">Arrows run from a paper to retrieved works that cite it. Drag to pan, use the zoom controls, and select a paper for details.</p>}

      {/* Node Detail Panel */}
      {selectedNode && (
        <div className="kg-detail-panel">
          <div className="kg-detail-header">
            <span
              className="kg-detail-badge"
              style={{ backgroundColor: groupColors[selectedNode.group] + '30', color: groupColors[selectedNode.group] }}
            >
              {groupLabels[selectedNode.group]}
            </span>
            <button className="kg-detail-close" onClick={() => setSelectedNode(null)}>
              <X size={14} />
            </button>
          </div>
          <h4 className="kg-detail-title">{selectedNode.name}</h4>
          <div className="kg-detail-meta">
            {selectedNode.authors && selectedNode.authors.length > 0 && (
              <span>{Array.isArray(selectedNode.authors) ? selectedNode.authors.slice(0, 3).join(', ') : selectedNode.authors}{selectedNode.authors.length > 3 ? ' et al.' : ''}</span>
            )}
            {selectedNode.year && <span>· {selectedNode.year}</span>}
            {selectedNode.citations != null && selectedNode.citations > 0 && (
              <span>· {selectedNode.citations} citations</span>
            )}
          </div>
          {selectedNode.source && (
            <div className="kg-detail-source">{selectedNode.source}</div>
          )}
          {selectedNode.abstract && (
            <p className="kg-detail-abstract">
              {selectedNode.abstract.length > 300
                ? selectedNode.abstract.substring(0, 300) + '…'
                : selectedNode.abstract}
            </p>
          )}
          <div className="kg-detail-actions">
            {selectedNode.url && (
              <a href={selectedNode.url} target="_blank" rel="noopener noreferrer" className="kg-detail-link">
                <ExternalLink size={13} />
                Open Paper
              </a>
            )}
            <button className="kg-detail-copy" onClick={() => copyCitation(selectedNode)}>
              <Copy size={13} />
              {copiedCitation ? 'Copied!' : 'Copy Citation'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
