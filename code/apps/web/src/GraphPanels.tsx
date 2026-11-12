import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, ArrowUpRight, ChevronRight, FileText, Network, Search } from "lucide-react";
import { SourcePreview } from "./Evidence";
import { Button, SourceCitation } from "./ui";
import type { EntityDetails, Evidence, ExplorerGraph, ExplorerNode, ExplorerSearch } from "./api";

export const pretty = (value: string) => value.replaceAll("_", " ");
export function EntityMark({ entity, large = false }: { entity: { kind: string; name: string }; large?: boolean }) {
  return <span className={"entity-mark kind-" + entity.kind + (large ? " large" : "")} aria-hidden="true">{entity.name.slice(0, 1)}</span>;
}

export function Discovery({ search, recent, onOpen, onCenter, onMore }: {
  search?: ExplorerSearch; recent: ExplorerNode[]; onOpen: (id: string) => void; onCenter: (id: string) => void; onMore: () => void;
}) {
  return <>
    <div className="explorer-panel-heading"><span>Discover</span><Network size={16} /></div>
    <div className="discovery-body">
      {search && <p className="discovery-summary">{search.total ? `${search.total} matching ${search.total === 1 ? "entity" : "entities"}` : "No matching entities"}</p>}
      {!search && <p className="discovery-intro">Start with something you know. Follow only the connections you need.</p>}
      <div className="entity-results">{(search?.nodes ?? recent).map(entity => <div className="entity-result" key={entity.id}>
        <button className="entity-result-main" onClick={() => onOpen(entity.id)}><EntityMark entity={entity} />
          <span><strong>{entity.name}</strong><small>{entity.kind} · {entity.connection_count} connections</small></span></button>
        <button className="entity-center" aria-label={"Center graph on " + entity.name} title="Make this the center" onClick={() => onCenter(entity.id)}><ArrowUpRight size={15} /></button>
      </div>)}</div>
      {search?.has_more && <Button variant="outline" className="discovery-more" onClick={onMore}>Show more results<ChevronRight size={14} /></Button>}
      {!search && !recent.length && <div className="discovery-empty"><Search size={24} /><p>Your recently explored entities will appear here.</p></div>}
    </div>
    <div className="discovery-note"><span className="discovery-note-dot" /><p><strong>A window into your knowledge</strong>Not the whole workspace. Expand a node to reveal more.</p></div>
  </>;
}

export function Inspector({ node, entity, graph, evidence, tab, setTab, onEvidence, onNode, onExpand, onCenter, onBack }: {
  node?: ExplorerNode; entity?: EntityDetails; graph: ExplorerGraph; evidence?: Evidence;
  tab: string; setTab: (tab: string) => void; onEvidence: (id: string) => void; onNode: (id: string) => void;
  onExpand: () => void; onCenter: () => void; onBack: () => void;
}) {
  if (evidence) return <div className="inspector-evidence">{node && <Button variant="ghost" onClick={onBack}><ArrowLeft size={15} />Back to node</Button>}<SourcePreview evidence={evidence} /></div>;
  if (!node || !entity) return null;
  const connections = graph.edges.flatMap(edge => {
    const outgoing = edge.source === node.id;
    const otherId = outgoing ? edge.target : edge.target === node.id ? edge.source : null;
    const other = graph.nodes.find(item => item.id === otherId);
    return other ? { edge, other, outgoing } : [];
  });
  return <>
    <div className="inspector-identity"><EntityMark entity={node} large /><div><span>{node.kind}</span><h2>{node.name}</h2></div></div>
    {!!node.conflict_count && <div className="review-banner">This entity has unresolved conflicting evidence. <Link to="/admin/conflicts">Review conflicts</Link></div>}
    <div className="inspector-entity-actions"><Button variant="outline" onClick={onExpand}><Network size={15} />Expand connections</Button><Button variant="ghost" onClick={onCenter}>Center<ArrowUpRight size={14} /></Button></div>
    <div className="inspector-tabs" role="tablist" aria-label="Entity details">{["overview", "connections"].map(value => <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{value === "overview" ? "Overview" : `Connections (${node.connection_count})`}</button>)}</div>

    {tab === "overview" ? <div className="inspector-tab-body">
      <Link className="inspector-knowledge-link" to={"/content/" + node.id}>Open knowledge page<ArrowUpRight size={14} /></Link>
      {entity.claims.length ? entity.claims.map(claim => <article className="inspector-claim" key={claim.id}><h3>{pretty(claim.predicate)}</h3><p>{claim.value}</p>
        <SourceCitation filename={claim.filename ?? node.filename} line={claim.line_number} locator={claim.locator} onOpen={() => onEvidence(claim.chunk_id)} /></article>) :
        <p className="muted">No verified claims are available for this entity. Explore its connections or source.</p>}
      <div className="inspector-source"><FileText size={16} /><div><strong>Knowledge from your sources</strong><span>{node.filename}</span></div></div>
    </div> : <div className="inspector-tab-body">
      <p className="connection-explanation">{connections.length} of {node.connection_count} authorized connections are on this canvas.</p>
      {connections.map(({ edge, other, outgoing }) => <article className="inspector-connection" key={edge.id}>
        <button onClick={() => onNode(other.id)}><EntityMark entity={other} /><span><strong>{other.name}</strong><small>{outgoing ? "Outgoing" : "Incoming"} · {pretty(edge.label)}</small></span><ArrowRight size={14} /></button>
        <button className="connection-evidence" onClick={() => onEvidence(edge.chunk_id)}><FileText size={12} />{pretty(edge.label)} evidence</button>
      </article>)}
      {!connections.length && <p className="muted">No matching loaded connections. Expand this node or clear graph filters.</p>}
    </div>}
  </>;
}

export function EntityOverviewCard({ entity, graph, claims }: { entity: ExplorerNode; graph: ExplorerGraph; claims: EntityDetails["claims"] }) {
  const connections = graph.nodes.filter(node => node.id !== entity.id).slice(0, 6);
  return <section className="search-entity-overview" aria-label="Connected knowledge">
    <div className="search-overview-heading"><EntityMark entity={entity} large /><div><span>{entity.kind} · Connected knowledge</span><h2>{entity.name}</h2></div>
      <Button variant="outline" asChild><Link to={"/graph?scope=" + entity.id + "&node=" + entity.id}><Network size={15} />View graph</Link></Button></div>
    {!!claims.length && <dl className="search-overview-claims">{claims.slice(0, 4).map(claim => <div key={claim.id}><dt>{pretty(claim.predicate)}</dt><dd>{claim.value}</dd></div>)}</dl>}
    {!!connections.length && <div className="search-overview-connections"><h3>Connected to</h3><div>{connections.map(node => <Link key={node.id} to={"/graph?scope=" + entity.id + "&node=" + node.id}><EntityMark entity={node} /><span>{node.name}<small>{node.kind}</small></span></Link>)}</div></div>}
    <Link className="text-action" to={"/content/" + entity.id}>Open full knowledge page<ArrowUpRight size={14} /></Link>
  </section>;
}
