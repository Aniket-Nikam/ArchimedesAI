import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
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
  1: 'Seminal',
  2: 'Depth-1',
  3: 'Depth-2',
};

export default function KnowledgeGraph({ report }: { report: any }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 500 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [visibleGroups, setVisibleGroups] = useState({ 1: true, 2: true, 3: true });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [copiedCitation, setCopiedCitation] = useState(false);
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

  // ── Auto-size via ResizeObserver ──
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // ── Spread out nodes to prevent overlap ──
  useEffect(() => {
    if (graphRef.current) {
      const chargeForce = graphRef.current.d3Force('charge');
      if (chargeForce) chargeForce.strength(-400); // Stronger repulsion

      const linkForce = graphRef.current.d3Force('link');
      if (linkForce) linkForce.distance(100); // Longer links
    }
  }, [report]);

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
    const visibleLinks = links.filter(l => visibleIds.has(l.source) && visibleIds.has(l.target));
    return { nodes: visibleNodes, links: visibleLinks };
  }, [nodes, links, visibleGroups, searchTerm]);

  // ── Zoom controls ──
  const handleZoomIn = useCallback(() => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom * 1.4, 300);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom / 1.4, 300);
    }
  }, []);

  const handleFitView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 60);
    }
  }, []);

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

  // ── Node paint function ──
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const color = groupColors[node.group] || '#888';
    const isHighlighted = searchTerm && node.name?.toLowerCase().includes(searchTerm.toLowerCase());
    const isHovered = hoveredNode === node.id;
    const isSelected = selectedNode?.id === node.id;
    const isExplored = exploredNodes.has(node.id);
    const radius = node.val * 1.2;

    // Glow effect for hovered/selected/highlighted
    if (isHovered || isSelected || isHighlighted) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
      ctx.fillStyle = color.replace(')', ', 0.25)').replace('rgb', 'rgba');
      ctx.fill();
    }

    // Main node
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
    // Dim the node if it has been explored, unless it's actively hovered or selected
    const opacity = (isHovered || isSelected) ? '' : (isExplored ? '40' : 'cc');
    ctx.fillStyle = color + opacity;
    ctx.fill();

    // Border for seminal papers
    if (node.group === 1) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }

    // Label for seminal papers or when zoomed in
    if (node.group === 1 || globalScale > 1.8) {
      const label = node.name?.length > 30 ? node.name.substring(0, 30) + '…' : node.name;
      const fontSize = Math.max(10 / globalScale, 2.5);
      ctx.font = `${fontSize}px 'Outfit', sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(232, 230, 240, 0.9)';
      ctx.fillText(label || '', node.x, node.y + radius + 3);
    }
  }, [searchTerm, hoveredNode, selectedNode, exploredNodes]);

  if (!nodes.length) return null;

  return (
    <div className="kg-wrapper">
      <div className="kg-header">
        <div className="kg-title">
          <span className="kg-title-icon">🕸️</span>
          Citation Network
          <span className="kg-node-count">{filteredData.nodes.length} nodes · {filteredData.links.length} edges</span>
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

      <div className="kg-graph-area" ref={containerRef}>
        <ForceGraph2D
          ref={graphRef}
          graphData={filteredData}
          nodeLabel=""
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const r = node.val * 1.2 + 4;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeClick={handleNodeClick}
          onNodeHover={(node: any) => setHoveredNode(node?.id || null)}
          linkColor={() => 'rgba(255,255,255,0.1)'}
          linkWidth={1}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={0.004}
          linkDirectionalParticleColor={() => 'rgba(108, 99, 255, 0.6)'}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="transparent"
          cooldownTicks={80}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.25}
          enableZoomInteraction={true}
          enablePanInteraction={true}
        />
      </div>

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
