import { lazy, StrictMode, Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, House, Link2, Menu, MessageSquare, Network, PanelLeftClose, PanelLeftOpen, Search, Settings, SquarePen, Users, Wrench } from "lucide-react";
import "@fontsource-variable/inter";
import "./styles.css";
import "./intelligence.css";
import "./linkmind.css";
import "./graph.css";
import "./repository.css";
import { SettingsPage, Sources } from "./Pages";
import { identities, Session, useSession, useViewer } from "./session";
import { Button, Feedback, SearchField, Sheet } from "./ui";
import type { Conversation } from "./contracts";

const Assistant = lazy(() => import("./Assistant").then(m => ({ default: m.Assistant })));
const SourceQuestion = lazy(() => import('./SourceQuestion'));
const Knowledge = lazy(() => import("./Knowledge").then(m => ({ default: m.Knowledge })));
const KnowledgeRecord = lazy(() => import("./KnowledgeRecord").then(m => ({ default: m.KnowledgeRecordRoute })));
const KnowledgeSync = lazy(() => import('./KnowledgeSync'));
const Repository = lazy(() => import("./Repository").then(m => ({ default: m.Repository })));
const Connections = lazy(() => import('./Connections'));
const SearchPage = lazy(() => import("./IntelligencePages").then(m => ({ default: m.SearchPage })));
const Processing = lazy(() => import("./IntelligencePages").then(m => ({ default: m.Processing })));
const Conflicts = lazy(() => import("./IntelligencePages").then(m => ({ default: m.Conflicts })));
const ChatDiagnostics = lazy(() => import("./ChatDiagnostics").then(m => ({ default: m.ChatDiagnostics })));
const Usage = lazy(() => import("./IntelligencePages").then(m => ({ default: m.UsageDashboard })));
const Graph = lazy(() => import("./GraphWorkspace").then(m => ({ default: m.GraphWorkspace })));
const primary = [{ path: "/", title: "Home", icon: House }, { path: "/search", title: "Search", icon: Search }, { path: "/graph", title: "Graph", icon: Network }, { path: "/people", title: "People", icon: Users }, { path: "/content", title: "Content", icon: BookOpen }];
const administration = [{ path: "/admin/sources", title: "Data Sources" }, {path:'/admin/connections',title:'Sources & Connections'}, {path:'/admin/knowledge-sync',title:'Knowledge Sync'}, { path: "/admin/processing", title: "Processing" }, { path: "/admin/conflicts", title: "Conflicts" }, { path: "/admin/usage", title: "AI Usage" }, { path: "/admin/chat-diagnostics", title: "Chat diagnostics" }, { path: "/admin/settings", title: "Settings" }];

function LegacyRoute({ to }: { to?: string }) {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  let path = to ?? "/";
  if (location.pathname === "/ask") { const id = params.get("conversation"); if (id) path = "/chat/" + encodeURIComponent(id); params.delete("conversation"); }
  if (location.pathname === "/wiki") { const id = params.get("page"); if (id) path = "/content/" + encodeURIComponent(id); params.delete("page"); }
  return <Navigate replace to={path + (params.size ? "?" + params : "") + location.hash} />;
}

const tabletQuery = "(min-width:640px) and (max-width:1100px)";
function subscribeTablet(callback: () => void) { const media = window.matchMedia(tabletQuery); media.addEventListener("change", callback); return () => media.removeEventListener("change", callback); }
function Workspace({ token, onSwitch }: { token: string; onSwitch: (token: string) => void }) {
  const location = useLocation();
  const { service } = useSession();
  const viewer = useViewer();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedTablet, setExpandedTablet] = useState(false);
  const tablet = useSyncExternalStore(subscribeTablet, () => window.matchMedia(tabletQuery).matches);
  const sidebarCollapsed = tablet ? !expandedTablet : collapsed;
  const [menu, setMenu] = useState(false);
  const [allHistory, setAllHistory] = useState(false);
  const [profile, setProfile] = useState(false);
  const [historyFilter, setHistoryFilter] = useState("");
  const menuButton = useRef<HTMLButtonElement>(null);
  const historyButton = useRef<HTMLButtonElement>(null);
  const profileButton = useRef<HTMLButtonElement>(null);
  const conversations = useQuery({ queryKey: ["conversations"], queryFn: () => service.json<Conversation[]>("/conversations"), refetchInterval: 10000 });
  const admin = location.pathname.startsWith("/admin");
  const assistant = location.pathname === "/" || location.pathname.startsWith("/chat/") || location.pathname==='/ask/sources';
  const operational = ["admin", "reviewer"].includes(viewer.data?.role ?? "");
  const graph = location.pathname === "/graph" || location.pathname === "/content/graph";
  const title = admin ? administration.find(d => d.path === location.pathname)?.title ?? "Admin Console" : assistant ? "Assistant" : graph ? "Graph" : location.pathname.startsWith("/people") ? "People" : location.pathname.startsWith("/content") ? "Content" : "Search";
  useEffect(() => { document.title = title + " · Linkmind"; setMenu(false); }, [title, location.pathname]);
  const navigation = <nav aria-label="Workspace">{primary.map(({ path, title: label, icon: Icon }) => <NavLink key={path} to={path} end={path === "/"} className={"nav-item" + (path === "/" && (location.pathname.startsWith("/chat/") || location.pathname==='/ask/sources') ? " active-assistant" : "")} title={label} aria-label={label} onClick={() => setMenu(false)}><Icon size={21} strokeWidth={1.7} /><span>{label}</span></NavLink>)}</nav>;
  const recents = <div className="sidebar-recents"><h2>Recent</h2>
    {conversations.isPending && <p className="sidebar-hint">Loading conversations…</p>}
    {conversations.isError && <Button variant="ghost" onClick={() => void conversations.refetch()}>Retry history</Button>}
    {conversations.isSuccess && !conversations.data.length && <p className="sidebar-hint">Your conversations will appear here.</p>}
    <nav aria-label="Recent conversations">{conversations.data?.slice(0, 8).map(c => <NavLink className="recent-conversation" key={c.id} title={c.title} to={"/chat/" + c.id} onClick={() => setMenu(false)}><MessageSquare size={17} /><span>{c.title}</span></NavLink>)}</nav>
    {!!conversations.data?.length && <Button ref={historyButton} variant="ghost" className="see-all" onClick={() => { setMenu(false); setAllHistory(true); }}>See all</Button>}
  </div>;
  const profileControl = <Button ref={profileButton} variant="ghost" className="profile-button" aria-label="Profile and workspace" title="Profile and workspace" onClick={() => { setMenu(false); setProfile(true); }}><span className="avatar">{viewer.data?.name.slice(0, 1) ?? "L"}</span><span><strong>{viewer.data?.name ?? "Your workspace"}</strong><small>{viewer.data?.organization ?? "Loading…"}</small></span></Button>;
  const sidebarContents = <><div className="sidebar-top"><Link to="/" className="brand" aria-label="Linkmind home"><Link2 className="brand-mark" size={29} strokeWidth={2.6} /><span className="brand-name">Linkmind</span></Link><div className="sidebar-top-actions"><Button variant="ghost" className="icon-button" asChild><Link to="/" aria-label="New conversation" title="New conversation"><SquarePen size={18} /></Link></Button><Button variant="ghost" className="icon-button collapse-button" title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"} aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"} onClick={() => { if (tablet) setExpandedTablet(!expandedTablet); else setCollapsed(!collapsed); }}>{sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</Button></div></div>
    {navigation}{recents}<div className="sidebar-bottom"><Link className={"nav-item" + (admin ? " active-assistant" : "")} aria-current={admin ? "page" : undefined} to="/admin/sources" title="Admin Console" aria-label="Admin Console" onClick={() => setMenu(false)}><Wrench size={20} strokeWidth={1.7} /><span>Admin Console</span></Link>{profileControl}<span className="local-mode">Local demo</span></div></>;
  return <div className={"workspace" + (sidebarCollapsed ? " workspace-collapsed" : "") + (expandedTablet ? " tablet-expanded" : "")}>
    <a className="skip-link" href="#workspace-content">Skip to content</a>
    <aside className="sidebar">{sidebarContents}</aside>
    <div className="workspace-body"><header className="mobile-topbar"><Button ref={menuButton} variant="ghost" className="icon-button" aria-label="Open navigation" onClick={() => setMenu(true)}><Menu size={21} /></Button><Link to="/" className="mobile-brand"><Link2 size={21} />Linkmind</Link><Button variant="ghost" className="icon-button" aria-label="Profile and workspace" onClick={() => setProfile(true)}><Settings size={19} /></Button></header>
      {!assistant && <header className="context-bar"><span>{admin ? "Admin Console" : title}</span><span>{viewer.data?.organization}</span></header>}
      <main id="workspace-content" className={assistant ? "assistant-main" : graph ? "graph-main-route" : ""} tabIndex={-1}>
        {admin && <nav className="section-tabs admin-tabs" aria-label="Admin Console">{administration.filter(d => (!["/admin/usage","/admin/chat-diagnostics"].includes(d.path) || operational) && (d.path !== "/admin/connections" || viewer.data?.role === "admin")).map(d => <NavLink key={d.path} to={d.path}>{d.title}</NavLink>)}</nav>}
        {location.pathname.startsWith("/content") && <nav className="section-tabs" aria-label="Content views"><NavLink to="/content" className={!location.pathname.startsWith("/content/documents") ? "selected" : ""} end>Knowledge</NavLink><NavLink to="/content/documents">Documents</NavLink></nav>}
        <Suspense fallback={<div className="page"><Feedback>Loading…</Feedback></div>}><Routes>
          <Route path="/" element={<Assistant />} /><Route path="/chat/:conversationId" element={<Assistant />} />
          <Route path="/ask/sources" element={<SourceQuestion />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/admin/connections" element={<Connections />} />
          <Route path="/admin/knowledge-sync" element={<KnowledgeSync />} />
          <Route path="/people" element={<Knowledge people />} /><Route path="/people/:entityId" element={<Knowledge people />} />
          <Route path="/content" element={<Knowledge />} /><Route path="/content/:entityId" element={<Knowledge />} />
          <Route path="/content/records/:recordId" element={<KnowledgeRecord />} />
          <Route path="/content/documents" element={<Repository />} /><Route path="/content/graph" element={<LegacyRoute to="/graph" />} /><Route path="/graph" element={<Graph />} />
          <Route path="/admin" element={<Navigate replace to="/admin/sources" />} />
          <Route path="/admin/sources" element={<Sources />} /><Route path="/admin/processing" element={<Processing />} />
          <Route path="/admin/conflicts" element={<Conflicts />} /><Route path="/admin/settings" element={<SettingsPage />} />
          <Route path="/admin/chat-diagnostics" element={operational ? <ChatDiagnostics /> : <Feedback>Diagnostics require a reviewer role.</Feedback>} />
          <Route path="/admin/usage" element={operational ? <Usage /> : viewer.isPending ? <Feedback>Checking access…</Feedback> : <div className="page"><h1>AI Usage</h1><Feedback>AI Usage is available to reviewers and administrators.</Feedback></div>} />
          <Route path="/ask" element={<LegacyRoute />} /><Route path="/wiki" element={<LegacyRoute to="/content" />} /><Route path="/graph" element={<Graph />} />
          {["sources", "processing", "conflicts", "usage", "settings"].map(path => <Route key={path} path={"/" + path} element={<LegacyRoute to={"/admin/" + path} />} />)}
          <Route path="*" element={<div className="page"><h1>Page not found</h1><p className="muted">This page may have moved.</p><Button variant="outline" asChild><Link to="/"><ArrowLeft size={16} />Back to Home</Link></Button></div>} />
        </Routes></Suspense>
      </main>
    </div>
    <Sheet title="Navigation" description="Your Linkmind workspace." side="left" open={menu} onOpenChange={setMenu} returnFocus={menuButton}><div className="mobile-navigation">{sidebarContents}</div></Sheet>
    <Sheet title="Your conversations" description="Your saved conversations in this workspace." open={allHistory} onOpenChange={setAllHistory} returnFocus={historyButton}><SearchField className="library-search" aria-label="Find a conversation" placeholder="Find a conversation…" value={historyFilter} onChange={e => setHistoryFilter(e.target.value)} /><nav className="all-history">{conversations.data?.filter(c => c.title.toLowerCase().includes(historyFilter.toLowerCase())).map(c => <Link to={"/chat/" + c.id} key={c.id} onClick={() => setAllHistory(false)}><MessageSquare size={16} />{c.title}</Link>)}</nav>{conversations.isSuccess && !conversations.data.some(c => c.title.toLowerCase().includes(historyFilter.toLowerCase())) && <Feedback>No matching conversations.</Feedback>}</Sheet>
    <Sheet title="Profile and workspace" description="Your active identity and access." open={profile} onOpenChange={setProfile} returnFocus={profileButton}><div className="profile-details"><span className="avatar">{viewer.data?.name.slice(0,1)}</span><h2>{viewer.data?.name}</h2><p>{viewer.data?.organization}</p><p className="muted">Local demo · {viewer.data?.role}</p><label>Demo identity<select aria-label="Demo identity" value={token} onChange={e => { setProfile(false); onSwitch(e.target.value); }}>{identities.map(identity => <option key={identity.token} value={identity.token}>{identity.label}</option>)}</select></label><p className="muted">Switching identity resets your view. Conversations are private to each user.</p><Button asChild variant="outline"><Link to="/admin/settings" onClick={() => setProfile(false)}>Workspace settings</Link></Button></div></Sheet>
  </div>;
}
function App() {
  const [token, setToken] = useState(() => { try { const saved = sessionStorage.getItem("linkmind.demoIdentity"); return identities.find(identity => identity.token === saved)?.token ?? identities[0].token; } catch { return identities[0].token; } });
  const navigate = useNavigate();
  return <Session key={token} token={token}><Workspace token={token} onSwitch={identity => { navigate("/", { replace: true }); try { sessionStorage.setItem("linkmind.demoIdentity", identity); } catch { /* Demo switching still works without browser storage. */ } setToken(identity); }} /></Session>;
}
createRoot(document.getElementById("root")!).render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>);

import './chat-polish.css';
