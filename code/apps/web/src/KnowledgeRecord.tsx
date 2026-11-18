import { createElement, useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, FileText, Network } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { EvidenceAction } from "./Evidence";
import { useSession } from "./session";
import { Button, Feedback } from "./ui";

export type RecordItem = {
  id: string; version_id: string; title: string; filename: string; kind: string; source_name: string;
};

type Relation = {
  source_id: string; source_name: string; source_kind: string;
  target_id: string; target_name: string; target_kind: string; predicate: string; chunk_id: string;
};

type RecordDetails = RecordItem & {
  issue_key?: string | null; entity_id: string | null; original_url: string; source_revision: string;
  source_updated_at: string | null; synced_at: string; synthetic?: boolean; current: boolean;
  metadata: Record<string, unknown>; body: string; body_format: "text" | "markdown" | "html";
  relationships: Relation[];
};

export const sourceLabel: Record<string, string> = { jira: "Jira", confluence: "Confluence", notion: "Notion" };

const htmlTags = new Set([
  "a", "b", "blockquote", "br", "caption", "code", "dd", "del", "div", "dl", "dt", "em",
  "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "li", "ol", "p", "pre", "s", "span",
  "strong", "sub", "sup", "table", "tbody", "td", "th", "thead", "tfoot", "tr", "u", "ul",
]);
const omitHtml = new Set(["audio", "embed", "form", "iframe", "object", "script", "style", "svg", "template", "video"]);

function safeLink(href: string | null | undefined, base: string) {
  if (!href) return undefined;
  try {
    const url = new URL(href, base);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

function htmlBody(body: string, base: string): ReactNode[] {
  // Parse in an inert template. Only pass approved elements and attributes to React.
  const template = document.createElement("template");
  template.innerHTML = body;
  function render(node: Node, key: number): ReactNode {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (!(node instanceof Element)) return null;
    const tag = node.localName;
    if (omitHtml.has(tag)) return null;
    if (tag === "img") return node.getAttribute("alt");
    const children = Array.from(node.childNodes, render);
    if (!htmlTags.has(tag)) return createElement("span", { key }, children);
    if (tag === "br" || tag === "hr") return createElement(tag, { key });
    if (tag === "a") {
      const href = safeLink(node.getAttribute("href"), base);
      return href ? <a key={key} href={href} target="_blank" rel="noopener noreferrer">{children}</a> :
        <span key={key}>{children}</span>;
    }
    if (tag === "td" || tag === "th") {
      const span = (attribute: string) => Math.max(1, Math.min(100, Number(node.getAttribute(attribute)) || 1));
      return createElement(tag, { key, colSpan: span("colspan"), rowSpan: span("rowspan") }, children);
    }
    return createElement(tag, { key }, children);
  }
  return Array.from(template.content.childNodes, render);
}

function SourceBody({ record }: { record: RecordDetails }) {
  const html = useMemo(() => record.body_format === "html" ? htmlBody(record.body, record.original_url) : null,
    [record.body, record.body_format, record.original_url]);
  if (record.body_format === "html") return <>{html}</>;
  if (record.body_format === "text") return <p className="record-plain">{record.body}</p>;
  return <Markdown remarkPlugins={[remarkGfm]} skipHtml
    urlTransform={href => safeLink(href, record.original_url) ?? ""}
    components={{
      a: ({ children, href }) => href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <>{children}</>,
      img: ({ alt }) => alt ? <>{alt}</> : null,
    }}>{record.body}</Markdown>;
}

function RelationshipEnd({ id, name, kind, current }: { id: string; name: string; kind: string; current: string | null }) {
  if (id === current) return <strong>{name}</strong>;
  return <Link to={(kind === "person" ? "/people/" : "/content/") + id}>{name}</Link>;
}

function fieldText(value: unknown): string | null {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (value && typeof value === "object" && ("key" in value || "name" in value)) {
    const name = "name" in value ? fieldText(value.name) : null;
    const key = "key" in value ? fieldText(value.key) : null;
    return name && key && name !== key ? name + " (" + key + ")" : name || key;
  }
  return null;
}

export function KnowledgeRecordRoute() {
  const { recordId } = useParams();
  const [params] = useSearchParams();
  return <KnowledgeRecord id={recordId!} version={params.get("version") ?? undefined} />;
}

export function KnowledgeRecord({ id, version }: { id: string; version?: string }) {
  const { service } = useSession();
  const record = useQuery({
    queryKey: ["knowledge-record", id, version],
    queryFn: () => service.json<RecordDetails>("/knowledge-base/records/" + id + (version ? "?version=" + encodeURIComponent(version) : "")),
    refetchOnMount: "always",
    refetchInterval: 60000,
  });
  const item = record.isSuccess ? record.data : null;
  const external = item && !item.synthetic ? safeLink(item.original_url, item.original_url) : undefined;
  const metadata = item ? [
    ...(item.kind === "jira" ? ["project", "status", "assignee"].map(field => [field, fieldText(item.metadata[field]) ?? (field === "assignee" ? "Unassigned" : null)] as const) : []),
    ["Source", item.source_name], ["Last synchronized", new Date(item.synced_at).toLocaleString()],
    ["Source updated", item.source_updated_at ? new Date(item.source_updated_at).toLocaleString() : null],
    ...(item.kind === "confluence" ? [["Page version", item.source_revision]] : []),
  ] : [];
  return <div className="page entity-reading record-reading">
    <Link className="back-link" to="/content"><ArrowLeft size={16} />All knowledge</Link>
    {record.isPending && <Feedback>Opening synchronized record…</Feedback>}
    {record.isError && <Feedback error>{record.error.message}<Button variant="outline" onClick={() => void record.refetch()}>Retry</Button></Feedback>}
    {item && <article>
      <header className="record-header">
        <div className="record-byline"><FileText size={17} /><span>{sourceLabel[item.kind] ?? item.source_name}</span>
          {item.issue_key && <span className="record-key">{item.issue_key}</span>}
          <span>{item.current ? "Synchronized record" : "Historical snapshot"}</span>
          {item.synthetic && <span>Demo source</span>}
        </div>
        <h1 className="wiki-title" dir="auto">{item.title}</h1>
        <div className="action-row">
          {external && <Button variant="outline" asChild><a href={external} target="_blank" rel="noopener noreferrer">Open original source<ArrowUpRight size={15} /></a></Button>}
          {item.entity_id && <Link className="text-action" to={"/graph?scope=" + item.entity_id + "&node=" + item.entity_id}><Network size={16} />Explore connections</Link>}
        </div>
        <dl className="record-metadata">{metadata.filter(([, value]) => value).map(([label, value]) =>
          <div key={label}><dt>{label}</dt><dd dir="auto">{value}</dd></div>
        )}</dl>
      </header>
      <section className="record-content" aria-label={item.kind === "jira" ? "Description" : "Synchronized page body"}>
        {item.kind === "jira" && <h2>Description</h2>}
        {item.body ? <div className="markdown record-body" dir="auto"><SourceBody record={item} /></div> :
          <p className="muted">There is no description in the synchronized issue.</p>}
      </section>
      {!!item.relationships.length && <section className="related-knowledge">
        <h2>Connected knowledge</h2>
        <ul className="record-relations">{item.relationships.map((r) => <li key={[r.source_id,r.predicate,r.target_id,r.chunk_id].join(":")}>
          <div><RelationshipEnd id={r.source_id} name={r.source_name} kind={r.source_kind} current={item.entity_id} />
            <span> {r.predicate.replaceAll("_", " ")} </span>
            <RelationshipEnd id={r.target_id} name={r.target_name} kind={r.target_kind} current={item.entity_id} />
          </div>
          <EvidenceAction id={r.chunk_id} title="View evidence" />
        </li>)}</ul>
      </section>}
    </article>}
  </div>;
}
