"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  Database,
  ExternalLink,
  Filter,
  Layers,
  Maximize2,
  Minimize2,
  Network,
  RefreshCw,
  Search,
  Share2,
  Shield,
  Sparkles,
  Zap,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { api } from "../../lib/api";
import { GraphEdge, GraphNode, GraphVisualizationResponse } from "../../types";

const NODE_TYPE_COLORS: Record<string, { bg: string; text: string; fill: string; stroke: string }> = {
  Company: { bg: "bg-blue-500/10", text: "text-blue-400", fill: "#3b82f6", stroke: "#60a5fa" },
  Person: { bg: "bg-purple-500/10", text: "text-purple-400", fill: "#a855f7", stroke: "#c084fc" },
  Startup: { bg: "bg-emerald-500/10", text: "text-emerald-400", fill: "#10b981", stroke: "#34d399" },
  Product: { bg: "bg-amber-500/10", text: "text-amber-400", fill: "#f59e0b", stroke: "#fbbf24" },
  Technology: { bg: "bg-cyan-500/10", text: "text-cyan-400", fill: "#06b6d4", stroke: "#22d3ee" },
  Investor: { bg: "bg-rose-500/10", text: "text-rose-400", fill: "#f43f5e", stroke: "#fb7185" },
  Industry: { bg: "bg-indigo-500/10", text: "text-indigo-400", fill: "#6366f1", stroke: "#818cf8" },
  Acquisition: { bg: "bg-orange-500/10", text: "text-orange-400", fill: "#f97316", stroke: "#fb923c" },
  Default: { bg: "bg-slate-500/10", text: "text-slate-400", fill: "#64748b", stroke: "#94a3b8" },
};

export default function GraphExplorerPage() {
  const [graphData, setGraphData] = useState<GraphVisualizationResponse>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [hopDepth, setHopDepth] = useState<number>(2);
  const [temporalYear, setTemporalYear] = useState<string>("ALL");
  const [activeTab, setActiveTab] = useState<"network" | "paths">("network");

  // Path finder states
  const [sourceEntity, setSourceEntity] = useState("");
  const [targetEntity, setTargetEntity] = useState("");
  const [discoveredPaths, setDiscoveredPaths] = useState<any[]>([]);
  const [pathLoading, setPathLoading] = useState(false);

  // Canvas zoom and pan
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const data = await api.graph.visualization(150);
      setGraphData(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[0]);
      }
    } catch (e) {
      console.error("Failed to load knowledge graph", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const handleFindPaths = async () => {
    if (!sourceEntity.trim()) return;
    setPathLoading(true);
    try {
      const paths = await api.graph.paths(sourceEntity.trim(), targetEntity.trim() || undefined, hopDepth);
      setDiscoveredPaths(paths || []);
    } catch (e) {
      console.error(e);
    } finally {
      setPathLoading(false);
    }
  };

  const expandNeighbors = async (nodeId: string) => {
    try {
      const yearFilter = temporalYear !== "ALL" ? parseInt(temporalYear) : undefined;
      const neighbors = await api.graph.neighbors(nodeId, hopDepth, yearFilter);
      // Merge unique nodes and edges
      setGraphData((prev) => {
        const existingNodeIds = new Set(prev.nodes.map((n) => n.id));
        const newNodes = neighbors.nodes.filter((n) => !existingNodeIds.has(n.id));
        const existingEdgeIds = new Set(prev.edges.map((e) => e.id));
        const newEdges = neighbors.edges.filter((e) => !existingEdgeIds.has(e.id));
        return {
          nodes: [...prev.nodes, ...newNodes],
          edges: [...prev.edges, ...newEdges],
        };
      });
    } catch (e) {
      console.error("Neighbor expansion error:", e);
    }
  };

  const filteredNodes = graphData.nodes.filter((node) => {
    const matchesSearch =
      node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.type.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === "ALL" || node.type === selectedType;
    return matchesSearch && matchesType;
  });

  const incidentEdges = selectedNode
    ? graphData.edges.filter(
        (e) => e.source === selectedNode.id || e.target === selectedNode.id
      )
    : [];

  const typesList = Array.from(new Set(graphData.nodes.map((n) => n.type)));

  // Layout node positions circularly for clean canvas rendering
  const nodePositions = new Map<string, { x: number; y: number }>();
  const total = filteredNodes.length;
  const radius = Math.min(320, Math.max(160, total * 22));
  const centerX = 380;
  const centerY = 300;

  filteredNodes.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / (total || 1);
    nodePositions.set(node.id, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  });

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 flex flex-col h-[calc(100vh-4rem)] max-w-7xl mx-auto overflow-hidden">
        {/* Top Control Bar */}
        <div className="p-4 px-6 border-b border-border glass-panel flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
              <Share2 className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white">Enterprise Knowledge Graph Explorer</h1>
              <p className="text-xs text-slate-400">
                Neo4j market topology with multi-hop reasoning paths and temporal filtering.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Tab Selector */}
            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-border text-xs">
              <button
                onClick={() => setActiveTab("network")}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  activeTab === "network" ? "bg-emerald-500 text-slate-950 font-semibold" : "text-slate-400 hover:text-white"
                }`}
              >
                Network Topology
              </button>
              <button
                onClick={() => setActiveTab("paths")}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  activeTab === "paths" ? "bg-emerald-500 text-slate-950 font-semibold" : "text-slate-400 hover:text-white"
                }`}
              >
                Multi-Hop Reasoning Paths
              </button>
            </div>

            <button
              onClick={fetchGraph}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-900 border border-border text-slate-300 hover:text-white hover:bg-slate-800 transition"
              title="Refresh Graph"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {activeTab === "network" ? (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Interactive Canvas */}
            <div className="flex-1 flex flex-col border-r border-border relative overflow-hidden bg-[#070b14]">
              {/* Canvas Filters */}
              <div className="p-3 border-b border-border/60 bg-slate-950/60 flex flex-wrap items-center justify-between gap-3 text-xs z-10">
                <div className="flex items-center space-x-3">
                  <div className="relative w-48">
                    <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2 pointer-events-none" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search nodes..."
                      className="w-full pl-8 pr-2 py-1 bg-slate-900 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <select
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value)}
                    className="px-2.5 py-1 bg-slate-900 border border-border rounded-lg text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ALL">All Types ({graphData.nodes.length})</option>
                    {typesList.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>

                  <select
                    value={temporalYear}
                    onChange={(e) => setTemporalYear(e.target.value)}
                    className="px-2.5 py-1 bg-slate-900 border border-border rounded-lg text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ALL">All Years</option>
                    <option value="2025">2025</option>
                    <option value="2024">2024</option>
                    <option value="2023">2023</option>
                    <option value="2022">2022</option>
                  </select>
                </div>

                {/* Zoom Controls */}
                <div className="flex items-center space-x-1 bg-slate-900 p-0.5 rounded-lg border border-border">
                  <button
                    onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
                    className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
                    className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      setZoom(1);
                      setPan({ x: 0, y: 0 });
                    }}
                    className="px-2 py-1 text-[10px] text-slate-400 hover:text-white font-mono"
                    title="Reset Zoom & Pan"
                  >
                    100%
                  </button>
                </div>
              </div>

              {/* Interactive SVG Network Graph */}
              <div
                className="flex-1 relative cursor-grab active:cursor-grabbing overflow-hidden"
                onMouseDown={(e) => {
                  setIsPanning(true);
                  setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
                }}
                onMouseMove={(e) => {
                  if (isPanning) {
                    setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
                  }
                }}
                onMouseUp={() => setIsPanning(false)}
                onMouseLeave={() => setIsPanning(false)}
              >
                {loading ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500">
                    Querying Neo4j knowledge graph topology...
                  </div>
                ) : filteredNodes.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-xs text-slate-500 space-y-2">
                    <Share2 className="w-8 h-8 opacity-40" />
                    <span>No graph nodes found matching filter criteria.</span>
                  </div>
                ) : (
                  <svg
                    className="w-full h-full select-none"
                    style={{
                      transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                      transformOrigin: "center center",
                      transition: isPanning ? "none" : "transform 0.1s ease-out",
                    }}
                  >
                    <defs>
                      <marker
                        id="arrow"
                        viewBox="0 0 10 10"
                        refX="22"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
                      </marker>
                    </defs>

                    {/* Edges */}
                    {graphData.edges.map((edge) => {
                      const srcPos = nodePositions.get(edge.source);
                      const tgtPos = nodePositions.get(edge.target);
                      if (!srcPos || !tgtPos) return null;

                      const isHighlighted =
                        selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id);

                      return (
                        <g key={edge.id}>
                          <line
                            x1={srcPos.x}
                            y1={srcPos.y}
                            x2={tgtPos.x}
                            y2={tgtPos.y}
                            stroke={isHighlighted ? "#10b981" : "#334155"}
                            strokeWidth={isHighlighted ? 2.5 : 1.2}
                            strokeDasharray={isHighlighted ? undefined : "3 3"}
                            markerEnd="url(#arrow)"
                          />
                          <text
                            x={(srcPos.x + tgtPos.x) / 2}
                            y={(srcPos.y + tgtPos.y) / 2 - 4}
                            fill={isHighlighted ? "#34d399" : "#64748b"}
                            fontSize="9"
                            fontFamily="monospace"
                            textAnchor="middle"
                          >
                            {edge.relationship}
                          </text>
                        </g>
                      );
                    })}

                    {/* Nodes */}
                    {filteredNodes.map((node) => {
                      const pos = nodePositions.get(node.id);
                      if (!pos) return null;

                      const isSelected = selectedNode?.id === node.id;
                      const colors = NODE_TYPE_COLORS[node.type] || NODE_TYPE_COLORS.Default;

                      return (
                        <g
                          key={node.id}
                          transform={`translate(${pos.x}, ${pos.y})`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedNode(node);
                          }}
                          className="cursor-pointer group"
                        >
                          <circle
                            r={isSelected ? 22 : 16}
                            fill={colors.fill}
                            stroke={isSelected ? "#ffffff" : colors.stroke}
                            strokeWidth={isSelected ? 3 : 1.5}
                            fillOpacity={isSelected ? 0.9 : 0.6}
                            className="transition-all duration-200 group-hover:scale-110"
                          />
                          <text
                            y={isSelected ? 34 : 28}
                            fill={isSelected ? "#ffffff" : "#94a3b8"}
                            fontSize="10"
                            fontWeight={isSelected ? "bold" : "normal"}
                            textAnchor="middle"
                            className="pointer-events-none drop-shadow"
                          >
                            {node.label}
                          </text>
                          <text
                            y={isSelected ? 45 : 39}
                            fill="#64748b"
                            fontSize="8"
                            textAnchor="middle"
                            fontFamily="monospace"
                            className="pointer-events-none"
                          >
                            {node.type}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
            </div>

            {/* Right Node & Relationship Details Sidebar */}
            <div className="w-80 border-l border-border glass-panel p-5 overflow-y-auto space-y-5">
              {selectedNode ? (
                <>
                  <div className="space-y-2 border-b border-border/60 pb-4">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                        (NODE_TYPE_COLORS[selectedNode.type] || NODE_TYPE_COLORS.Default).bg
                      } ${(NODE_TYPE_COLORS[selectedNode.type] || NODE_TYPE_COLORS.Default).text}`}
                    >
                      {selectedNode.type}
                    </span>
                    <h2 className="text-xl font-bold text-white tracking-tight">{selectedNode.label}</h2>
                    <p className="text-xs text-slate-400 font-mono">ID: {selectedNode.id}</p>
                    <button
                      onClick={() => expandNeighbors(selectedNode.id)}
                      className="mt-2 w-full py-1.5 px-3 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
                    >
                      <Share2 className="w-3.5 h-3.5" />
                      <span>Expand 1-Hop Neighbors</span>
                    </button>
                  </div>

                  {/* Incident Relationships */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Connected Relationships ({incidentEdges.length})
                    </h3>
                    {incidentEdges.length === 0 ? (
                      <p className="text-xs text-slate-500">No active relationships connected.</p>
                    ) : (
                      <div className="space-y-2">
                        {incidentEdges.map((edge) => {
                          const isSource = edge.source === selectedNode.id;
                          const otherNodeId = isSource ? edge.target : edge.source;
                          const otherNode = graphData.nodes.find((n) => n.id === otherNodeId);
                          return (
                            <div
                              key={edge.id}
                              onClick={() => {
                                if (otherNode) setSelectedNode(otherNode);
                              }}
                              className="p-2.5 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-border cursor-pointer transition text-xs space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-emerald-400 text-[11px]">
                                  {isSource ? "→" : "←"} {edge.relationship}
                                </span>
                                {edge.valid_from && (
                                  <span className="text-[10px] text-slate-500 font-mono">
                                    {edge.valid_from}
                                  </span>
                                )}
                              </div>
                              <p className="font-medium text-white">{otherNode?.label || otherNodeId}</p>
                              {edge.confidence && (
                                <p className="text-[10px] text-slate-400">
                                  Confidence: {Math.round(edge.confidence * 100)}%
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-500 text-center">
                  Select a node from the network graph to inspect relationships and temporal facts.
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Multi-Hop Path Visualizer Tab */
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-border space-y-4">
              <h2 className="text-lg font-bold text-white">Multi-Hop Path Discovery</h2>
              <p className="text-xs text-slate-400">
                Trace indirect relationship chains across companies, executives, startups, and acquisitions.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                    Source Entity Name
                  </label>
                  <input
                    type="text"
                    value={sourceEntity}
                    onChange={(e) => setSourceEntity(e.target.value)}
                    placeholder="e.g. Satya Nadella or Google"
                    className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                    Target Entity (Optional)
                  </label>
                  <input
                    type="text"
                    value={targetEntity}
                    onChange={(e) => setTargetEntity(e.target.value)}
                    placeholder="e.g. OpenAI or Activision"
                    className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 uppercase mb-1">
                    Max Hop Depth (1 - 5)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={hopDepth}
                    onChange={(e) => setHopDepth(parseInt(e.target.value) || 3)}
                    className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <button
                onClick={handleFindPaths}
                disabled={pathLoading || !sourceEntity.trim()}
                className="py-2.5 px-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-lg text-xs flex items-center space-x-2 transition disabled:opacity-50"
              >
                {pathLoading ? (
                  <span>Traversing Graph Paths...</span>
                ) : (
                  <>
                    <Network className="w-4 h-4" />
                    <span>Find Multi-Hop Reasoning Paths</span>
                  </>
                )}
              </button>
            </div>

            {/* Path Results */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-white">Discovered Reasoning Chains ({discoveredPaths.length})</h3>
              {discoveredPaths.length === 0 ? (
                <div className="glass-panel p-8 rounded-xl border border-border text-center text-xs text-slate-500">
                  Enter source entity to discover connecting multi-hop relationship paths.
                </div>
              ) : (
                <div className="space-y-3">
                  {discoveredPaths.map((path, idx) => (
                    <div key={idx} className="glass-panel p-4 rounded-xl border border-border space-y-2">
                      <div className="flex items-center space-x-2 text-xs text-emerald-400 font-mono">
                        <span>Path #{idx + 1}</span>
                        {path.length && <span>• {path.length} hops</span>}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                        {path.nodes ? (
                          path.nodes.map((node: string, nIdx: number) => (
                            <div key={nIdx} className="flex items-center space-x-2">
                              <span className="px-2.5 py-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-semibold">
                                {node}
                              </span>
                              {path.relationships && path.relationships[nIdx] && (
                                <span className="text-emerald-400 text-xs">
                                  ──[ {path.relationships[nIdx]} ]──▶
                                </span>
                              )}
                            </div>
                          ))
                        ) : (
                          <pre className="text-slate-300 text-xs">{JSON.stringify(path, null, 2)}</pre>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
