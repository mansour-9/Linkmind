import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { List, Network, PanelLeftClose, PanelLeftOpen, Search, X } from "lucide-react";
import { GraphDemoButton } from "./GraphDemo";
import { ExplorerCanvas } from "./ExplorerCanvas";
import { Discovery, Inspector } from "./GraphPanels";
import { mergeGraphs } from "./graphExplorer";
import { rememberEntity } from "./recent";
import { useSession } from "./session";
import { Button, Feedback, SearchField, Sheet } from "./ui";
import type { ExplorerGraph, ExplorerNode, ExplorerSearch } from "./api";

const uuid = (value: string | null) => value && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value) ? value : null;
export function GraphWorkspace() {
  const { token, service } = useSession();
  const [params, setParams] = useSearchParams();
  const selected = uuid(params.get("node"));
  const [fallbackScope, setFallbackScope] = useState<string | null>(null);
  const explicitScope = uuid(params.get("scope"));
  const root = explicitScope ?? fallbackScope ?? selected;
  const evidenceId = uuid(params.get("evidence"));
  const q = params.get("q") ?? "";
  const kind = params.get("kind") ?? "";
  const relationship = params.get("relationship") ?? "";
  const depth = Math.min(3, Math.max(1, Number(params.get("depth")) || 1));

  const [primaryGraph, setPrimaryGraph] = useState<ExplorerGraph | null>(null);
  const [expandedGraphs, setExpandedGraphs] = useState<Record<string, ExplorerGraph>>({});
  const [expandedOffsets, setExpandedOffsets] = useState<Record<string, number>>({});
  const [batchLoading, setBatchLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [resultOffset, setResultOffset] = useState(0);
  const [extraResults, setExtraResults] = useState<ExplorerNode[]>([]);
  const [inspectorTab, setInspectorTab] = useState("overview");
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [showDiscover, setShowDiscover] = useState(true);
  const [showMap, setShowMap] = useState(false);
  const [showList, setShowList] = useState(false);
  const expandedRoots = useRef("");

  function update(changes: Record<string, string | null>, replace = false) {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => value ? next.set(key, value) : next.delete(key));
    setParams(next, { replace });
  }
  function center(id: string) {
    if (id !== root) {
      setPrimaryGraph(null); setExpandedGraphs({}); setExpandedOffsets({}); setHistory([]);
    }
    update({ scope: id, node: id, evidence: null, q: null });
  }
  useEffect(() => { setPrimaryGraph(null); setExpandedGraphs({}); setExpandedOffsets({}); setHistory([]); expandedRoots.current = ""; }, [root, kind, relationship, depth, token]);
  useEffect(() => { setResultOffset(0); setExtraResults([]); }, [q, kind, token]);

  const discovery = useQuery({ queryKey: ["explorer-search", q, kind, resultOffset],
    queryFn: () => service.json<ExplorerSearch>(`/graph/search?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}&offset=${resultOffset}&limit=10`),
    refetchInterval: 5000 });
  const neighborhood = useQuery({ queryKey: ["explorer", root, depth, kind, relationship],
    queryFn: () => service.json<ExplorerGraph>(`/graph/explore?root=${root}&depth=${depth}&kind=${encodeURIComponent(kind)}&relationship=${encodeURIComponent(relationship)}&offset=0&limit=24`),
    enabled: !!root, refetchInterval: 5000 });
  const expanded = useQuery({
    queryKey: ["explorer-expansions", root, kind, relationship, expandedRoots.current],
    enabled: !!root && !!expandedRoots.current,
    queryFn: async () => {
      const requests = expandedRoots.current.split(",").filter(Boolean).map(async id => {
        const offset = expandedOffsets[id] ?? 0;
        const result = await service.json<ExplorerGraph>(`/graph/explore?root=${id}&depth=1&kind=${encodeURIComponent(kind)}&relationship=${encodeURIComponent(relationship)}&offset=${offset}&limit=24`);
        return [id, result] as const;
      });
      return Object.fromEntries(await Promise.all(requests));
    },
    refetchInterval: 5000,
  });
  const predicates = useQuery({ queryKey: ["graph-relationships"], queryFn: () => service.json<string[]>("/graph/relationships"), refetchInterval: 10000 });
  const entity = useQuery({ queryKey: ["entity", selected], queryFn: () => service.entity(selected!), enabled: !!selected, refetchInterval: 5000 });
  const evidence = useQuery({ queryKey: ["evidence", evidenceId], queryFn: () => service.evidence(evidenceId!), enabled: !!evidenceId, refetchInterval: 5000 });

  useEffect(() => {
    if (neighborhood.isSuccess && root && neighborhood.data.root === root) {
      setPrimaryGraph(neighborhood.data);
      const rootEntity = neighborhood.data.nodes.find(node => node.id === root);
      if (rootEntity) rememberEntity(token, rootEntity);
    }
  }, [neighborhood.data, neighborhood.isSuccess, root, token]);
  useEffect(() => {
    if (expanded.isSuccess) setExpandedGraphs(expanded.data);
    if (expanded.isError) setExpandedGraphs({});
  }, [expanded.data, expanded.isSuccess, expanded.isError]);
  useEffect(() => {
    if (root || !discovery.isSuccess || resultOffset) return;
    const first = discovery.data.nodes.find(node => node.kind === "project") ?? discovery.data.nodes[0];
    if (first) { setFallbackScope(first.id); update({ scope: first.id, node: first.id }, true); }
  }, [discovery.data, discovery.isSuccess, root, resultOffset]);

  const graph = useMemo(() => mergeGraphs(primaryGraph, expandedGraphs), [primaryGraph, expandedGraphs]);
  const selectedNode = graph.nodes.find(node => node.id === selected);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [expansionError, setExpansionError] = useState("");
  const loading = loadingId ?? (neighborhood.isFetching && root ? root : null);
  const searchData = discovery.isSuccess ? { ...discovery.data, nodes: [...extraResults, ...discovery.data.nodes] } : undefined;
  const recent = graph.nodes.filter(node => history.includes(node.id) || node.id === root);
  function open(id: string) {
    if (!graph.nodes.some(node => node.id === id)) { center(id); return; }
    setInspectorTab("overview");
    setHistory(old => [id, ...old.filter(item => item !== id)].slice(0, 10));
    update({ node: id, evidence: null });
  }
  async function expand(id: string) {
    setExpansionError("");
    if (id === root && !expandedGraphs[id]) {
      if (primaryGraph?.truncated && !batchLoading) {
        setBatchLoading(true);
        try {
          const batches = await Promise.all([1, 2, 3].map(batch => service.json<ExplorerGraph>(`/graph/explore?root=${id}&depth=${depth}&kind=${encodeURIComponent(kind)}&relationship=${encodeURIComponent(relationship)}&offset=${batch * 24}&limit=24`)));
          setExpandedGraphs(old => Object.fromEntries(batches.map((result, index) => [`${id}:${index + 1}`, result])));
          expandedRoots.current = [...new Set([...expandedRoots.current.split(","), id])].filter(Boolean).join(",");
        } catch (cause) { setExpansionError(cause instanceof Error ? cause.message : "Could not load more connections."); }
        finally { setBatchLoading(false); }
      }
      return;
    }
    if (expandedGraphs[id]) {
      const current = expandedOffsets[id] ?? 0;
      if (current + 24 < (expandedGraphs[id].root_connection_count ?? 0)) {
        setLoadingId(id);
        try {
          const next = current + 24;
          const result = await service.json<ExplorerGraph>(`/graph/explore?root=${id}&depth=1&kind=${encodeURIComponent(kind)}&relationship=${encodeURIComponent(relationship)}&offset=${next}&limit=24`);
          setExpandedGraphs(old => ({ ...old, [`${id}:${next}`]: result })); setExpandedOffsets(old => ({ ...old, [id]: next }));
          expandedRoots.current = [...new Set([...expandedRoots.current.split(","), `${id}:${next}`])].filter(Boolean).join(",");
        } catch (cause) { setExpansionError(cause instanceof Error ? cause.message : "Could not load more connections."); }
        finally { setLoadingId(null); }
      }
      return;
    }
    setLoadingId(id);
    try {
      const result = await service.json<ExplorerGraph>(`/graph/explore?root=${id}&depth=1&kind=${encodeURIComponent(kind)}&relationship=${encodeURIComponent(relationship)}&limit=24`);
      setExpandedGraphs(old => ({ ...old, [id]: result })); setExpandedOffsets(old => ({ ...old, [id]: 0 }));
      expandedRoots.current = [...new Set([...expandedRoots.current.split(","), id])].filter(Boolean).join(",");
      setHistory(old => [...old, id]); update({ node: id, evidence: null });
    } catch (cause) { setExpansionError(cause instanceof Error ? cause.message : "Could not expand this entity."); }
    finally { setLoadingId(null); }
  }
  function resetFilters() { update({ kind: null, relationship: null, depth: null }, true); }

  const hasInspector = !!selectedNode && (entity.isSuccess || evidenceId !== null);
  const inspector = <Inspector node={selectedNode} entity={entity.isSuccess && entity.data.id === selected ? entity.data : undefined} graph={graph}
    evidence={evidence.isSuccess && evidence.data.id === evidenceId ? evidence.data : undefined} tab={inspectorTab} setTab={setInspectorTab}
    onEvidence={id => update({ evidence: id })} onNode={open} onExpand={() => selected && void expand(selected)}
    onCenter={() => selected && center(selected)} onBack={() => update({ evidence: null })} />;
  const discoveryPanel = <Discovery search={q || kind ? searchData : undefined} recent={recent} onOpen={open} onCenter={center}
    onMore={() => { if (discovery.isSuccess) { setExtraResults(old => [...old, ...discovery.data.nodes]); setResultOffset(value => value + 10); } }} />;

  return <div className="graph-workspace">
    <header className="explorer-header"><div className="explorer-title"><Network size={19} /><h1>Knowledge graph</h1><span>Explore the connections behind your workspace.</span></div>
      <Button variant="ghost" className="explorer-discover-toggle" aria-label="Toggle discovery panel" onClick={() => setShowDiscover(value => !value)}>{showDiscover ? <PanelLeftClose size={17} /> : <PanelLeftOpen size={17} />}</Button>
      <Button variant="outline" className="explorer-mobile-discover" onClick={() => setDiscoverOpen(true)}><Search size={16} />Discover</Button>
      <GraphDemoButton /></header>
    <div className="explorer-filterbar"><SearchField className="explorer-search" aria-label="Find an entity" placeholder="Find a project, person, decision…" value={q} onChange={event => update({ q: event.target.value }, true)} />
      <select aria-label="Graph entity type" value={kind} onChange={event => update({ kind: event.target.value }, true)}><option value="">All types</option>{["project", "person", "team", "task", "decision", "technology", "system", "event"].map(value => <option key={value}>{value}</option>)}</select>
      <select aria-label="Relationship filter" value={relationship} onChange={event => update({ relationship: event.target.value }, true)}><option value="">All relationships</option>{predicates.data?.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
      <label className="depth-select"><span>Depth</span><select aria-label="Exploration depth" value={depth} onChange={event => update({ depth: event.target.value }, true)}><option value="1">1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option></select></label>
      {(kind || relationship || depth > 1) && <Button variant="ghost" onClick={resetFilters}>Clear<X size={14} /></Button>}
      <Button variant="ghost" className="explorer-list-toggle" aria-pressed={showList} onClick={() => setShowList(value => !value)}><List size={16} />List</Button></div>
    <div className={"explorer-layout" + (showDiscover ? "" : " discovery-hidden") + (hasInspector ? " has-inspector" : "")}>
      {showDiscover && <aside className="explorer-discovery" aria-label="Graph discovery">{discoveryPanel}</aside>}
      <section className="explorer-main" aria-label="Graph exploration">
        <div className="explorer-context"><div><span className="live-dot" /><strong>{graph.nodes.find(node => node.id === root)?.name ?? "Your knowledge"}</strong><span>{depth}-hop exploration</span></div>
          <span>{graph.nodes.length} nodes · {graph.edges.length} relationships</span></div>
        {(neighborhood.isPending && root || discovery.isPending && !root) && <div className="explorer-loading"><Feedback>Loading your connected knowledge…</Feedback></div>}
        {neighborhood.isError && <Feedback error>{neighborhood.error.message}<Button variant="outline" onClick={() => void neighborhood.refetch()}>Retry</Button></Feedback>}
        {discovery.isError && <Feedback error>{discovery.error.message}<Button variant="outline" onClick={() => void discovery.refetch()}>Retry</Button></Feedback>}
        {entity.isError && <Feedback error>{entity.error.message}</Feedback>}
        {evidence.isError && <Feedback error>{evidence.error.message}</Feedback>}
        {expansionError && <Feedback error>{expansionError}</Feedback>}
        {!neighborhood.isPending && <ExplorerCanvas graph={graph} roots={root ? [root] : []}
          expanded={new Set(Object.keys(expandedGraphs).map(key => key.split(":")[0]))} loading={loading} selected={selected} onNode={open} onExpand={id => void expand(id)}
          onEvidence={id => update({ evidence: id })} showMap={showMap} onToggleMap={() => setShowMap(value => !value)} />}
        {showList && <div className="graph-list-view"><div className="graph-list-heading"><strong>Visible entities</strong><button onClick={() => setShowList(false)} aria-label="Close entity list"><X size={16} /></button></div>
          {graph.nodes.map(node => <button key={node.id} onClick={() => open(node.id)}><span>{node.name}<small>{node.kind}</small></span><span>{node.connection_count} connections</span></button>)}</div>}
        <footer className="explorer-status"><span><i />Only sources you can access</span><span>{graph.truncated ? "Partial view · expand or filter to see more" : `${graph.nodes.length} entities in this view`}</span></footer>
      </section>
      {hasInspector && <aside className="explorer-inspector" aria-label="Entity inspector"><div className="inspector-top"><span>Inspector</span><Button variant="ghost" className="icon-button" aria-label="Close inspector" onClick={() => update({ node: null, evidence: null }, true)}><X size={16} /></Button></div>
        <div className="inspector-scroll">{entity.isPending || (evidenceId !== null && evidence.isPending) ? <Feedback>Loading details…</Feedback> : inspector}</div></aside>}
    </div>
    <Sheet title="Discover knowledge" description="Find and center a connected entity." side="left" open={discoverOpen} onOpenChange={setDiscoverOpen}>{discoveryPanel}</Sheet>
  </div>;
}
