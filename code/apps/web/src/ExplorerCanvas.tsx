import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Background, Controls, Handle, MarkerType, MiniMap, Position, ReactFlow,
  useNodesInitialized, useNodesState, useReactFlow, type Edge, type Node, type NodeProps, type ReactFlowInstance } from "@xyflow/react";
import { Fullscreen, Maximize, Minimize, Network, RotateCcw } from "lucide-react";
import type { ExplorerGraph, ExplorerNode } from "./api";
import { connectedIds, radialPositions, type Position as GraphPosition } from "./graphExplorer";
import { Button, Feedback } from "./ui";
import "@xyflow/react/dist/style.css";

export type BrainNode = Node<{ entity: ExplorerNode; degree: number; expanded: boolean; loading: boolean; center: boolean }, "knowledge">;
const nodeTypes = { knowledge: KnowledgeNode };
const iconKind: Record<string, string> = { project: "P", person: "A", team: "T", technology: "D", system: "S", task: "✓", decision: "◇", event: "E", document: "F" };

function KnowledgeNode({ data, selected }: NodeProps<BrainNode>) {
  const entity = data.entity;
  const hidden = Math.max(0, entity.connection_count - data.degree);
  return <div className={"graph-node kind-" + entity.kind + (selected ? " selected" : "") + (data.center ? " center" : "")}>
    <Handle type="target" position={Position.Left} />
    <div className="graph-node-orb" aria-hidden="true"><span>{iconKind[entity.kind] ?? "N"}</span>
      {!!entity.conflict_count && <i title={entity.conflict_count + " unresolved conflicts"}>!</i>}
      {data.loading ? <b className="graph-node-loading" /> : hidden > 0 && <span className="graph-node-expand"
        title={hidden + " connections outside the loaded canvas"}>{data.expanded ? "+" : "+" + Math.min(hidden, 99)}</span>}
    </div>
    <span className="graph-node-label"><strong>{entity.name}</strong><small>{entity.kind}</small></span>
    <Handle type="source" position={Position.Right} />
  </div>;
}

function FitNewScope({ scopeKey }: { scopeKey: string }) {
  const initialized = useNodesInitialized();
  const { fitView } = useReactFlow();
  const previous = useRef("");
  useEffect(() => {
    if (!initialized || !scopeKey || previous.current === scopeKey) return;
    previous.current = scopeKey;
    const mobile = window.matchMedia("(max-width:639px)").matches;
    void fitView({ padding: mobile ? .05 : .18, maxZoom: mobile ? .85 : 1.05, minZoom: mobile ? .38 : .16, duration: 180 });
  }, [scopeKey, initialized, fitView]);
  return null;
}

export function ExplorerCanvas({ graph, roots, expanded, loading, selected, onNode, onExpand, onEvidence, showMap, onToggleMap }: {
  graph: ExplorerGraph; roots: string[]; expanded: Set<string>; loading: string | null; selected: string | null;
  onNode: (id: string) => void; onExpand: (id: string) => void; onEvidence: (id: string, edgeId: string) => void;
  showMap: boolean; onToggleMap: () => void;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<BrainNode>([]);
  const [flow, setFlow] = useState<ReactFlowInstance<BrainNode, Edge> | null>(null);
  const [zoom, setZoom] = useState(1);
  const canvasElement = useRef<HTMLDivElement>(null);
  const viewButton = useRef<HTMLButtonElement>(null);
  const [canvasOnly, setCanvasOnly] = useState(false);
  const [viewError, setViewError] = useState("");
  useEffect(() => {
    let wasCanvasOnly = false;
    function changed() {
      const active = document.fullscreenElement === canvasElement.current;
      setCanvasOnly(active);
      if (wasCanvasOnly && !active) viewButton.current?.focus({ preventScroll: true });
      wasCanvasOnly = active;
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape" && document.fullscreenElement === canvasElement.current) {
        event.preventDefault();
        void document.exitFullscreen();
      }
    }
    document.addEventListener("fullscreenchange", changed);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("fullscreenchange", changed);
      document.removeEventListener("keydown", escape);
    };
  }, []);
  async function toggleCanvasView() {
    setViewError("");
    try {
      if (document.fullscreenElement === canvasElement.current) await document.exitFullscreen();
      else await canvasElement.current?.requestFullscreen();
    } catch {
      setViewError("Canvas-only view could not open. Your browser may not support fullscreen here.");
    }
  }
  async function openEvidence(id: string, edgeId: string) {
    if (document.fullscreenElement === canvasElement.current) await document.exitFullscreen();
    onEvidence(id, edgeId);
  }
  const savedPositions = useRef(new Map<string, GraphPosition>());
  const [resetKey, setResetKey] = useState(0);
  const scopeKey = roots.join("|") + ":" + resetKey;
  const degrees = useMemo(() => {
    const result = new Map<string, number>();
    graph.edges.forEach(edge => {
      result.set(edge.source, (result.get(edge.source) ?? 0) + 1);
      result.set(edge.target, (result.get(edge.target) ?? 0) + 1);
    });
    return result;
  }, [graph.edges]);

  const layout = useMemo(() => {
    savedPositions.current = radialPositions(graph, roots, resetKey ? new Map() : savedPositions.current);
    return graph.nodes.map(entity => ({ id: entity.id, type: "knowledge" as const,
      data: { entity, degree: degrees.get(entity.id) ?? 0, expanded: expanded.has(entity.id), loading: loading === entity.id, center: roots.includes(entity.id) },
      position: savedPositions.current.get(entity.id) ?? { x: 0, y: 0 } }));
  }, [graph, roots, expanded, loading, degrees, resetKey]);
  useLayoutEffect(() => {
    setNodes(old => layout.map(node => ({ ...node, position: resetKey ? node.position : old.find(item => item.id === node.id)?.position ?? node.position })));
  }, [layout, setNodes, resetKey]);
  const related = useMemo(() => connectedIds(graph, selected), [graph, selected]);
  const visible = useMemo(() => nodes.map(node => ({ ...node, ariaLabel: node.data.entity.name + ", " + node.data.entity.kind,
    selected: node.id === selected, className: related && !related.has(node.id) ? "graph-receded" : "" })), [nodes, related, selected]);
  const edges = useMemo<Edge[]>(() => graph.edges.map(edge => {
    const active = selected === edge.source || selected === edge.target;
    return { id: edge.id, source: edge.source, target: edge.target, type: "default",
      ariaLabel: edge.label + " relationship. Open evidence.", label: zoom >= .95 && active ? edge.label.replaceAll("_", " ") : undefined,
      markerEnd: { type: MarkerType.ArrowClosed, width: 13, height: 13, color: active ? "var(--primary)" : "var(--graph-edge)" },
      className: active ? "graph-edge-active" : related ? "graph-edge-receded" : "",
      labelClassName: "graph-edge-label", data: { evidence: edge.chunk_id } };
  }), [graph.edges, selected, related, zoom]);
  function fit() { const mobile = window.matchMedia("(max-width:639px)").matches; void flow?.fitView({ padding: mobile ? .05 : .18, maxZoom: mobile ? .85 : 1.05, minZoom: mobile ? .38 : .16, duration: 180 }); }
  return <div ref={canvasElement} className="canvas explorer-canvas" aria-label="Knowledge graph canvas">
    <div className="canvas-view-control"><Button ref={viewButton} variant="outline" aria-pressed={canvasOnly}
      aria-label={canvasOnly ? "Exit canvas-only view" : "Enter canvas-only view"}
      title={canvasOnly ? "Exit canvas-only view (Esc)" : "Show only the graph canvas"}
      onClick={() => void toggleCanvasView()}>{canvasOnly ? <Minimize size={15} /> : <Fullscreen size={15} />}
      {canvasOnly ? "Exit canvas view" : "Canvas only"}</Button></div>
    {viewError && <div className="canvas-view-error"><Feedback error>{viewError}</Feedback></div>}
    {graph.nodes.length ? <>
      <ReactFlow nodes={visible} edges={edges} nodeTypes={nodeTypes} onInit={setFlow} onNodesChange={onNodesChange}
        onNodeClick={(_, node) => onNode(node.id)} onNodeDoubleClick={(_, node) => onExpand(node.id)}
        onEdgeClick={(_, edge) => void openEvidence(String(edge.data?.evidence), edge.id)}
        onMove={(_, viewport) => setZoom(viewport.zoom)} nodesConnectable={false} deleteKeyCode={null}
        fitView fitViewOptions={{ padding: .22, maxZoom: 1.05 }} minZoom={.16} maxZoom={2.2} proOptions={{ hideAttribution: true }}>
        <Background gap={22} size={1.1} color="var(--graph-grid)" />
        <Controls showInteractive={false} showFitView={false} position="bottom-left" />
        {showMap && <MiniMap pannable zoomable nodeColor="var(--entity-project)" className="explorer-minimap" />}
        <FitNewScope scopeKey={scopeKey} />
      </ReactFlow>
      <div className="canvas-actions graph-actions">
        <Button variant="outline" onClick={onToggleMap} aria-pressed={showMap}><Network size={15} />{showMap ? "Hide map" : "Minimap"}</Button>
        <Button variant="outline" onClick={fit}><Maximize size={15} />Fit</Button>
        <Button variant="outline" onClick={() => { savedPositions.current.clear(); setResetKey(key => key + 1); requestAnimationFrame(fit); }}><RotateCcw size={15} />Reset</Button>
      </div>
      <div className="canvas-hint">{canvasOnly ? "Select a node · Exit canvas view for details · Esc to exit" : "Select to inspect · Double-click to expand"}</div>
    </> : <div className="canvas-message"><Network size={34} /><h2>Explore your connected knowledge</h2>
      <p>Find a project, person, or decision to reveal its connections.</p></div>}
  </div>;
}
