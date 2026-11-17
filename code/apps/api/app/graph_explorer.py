"""Bounded, permission-checked graph exploration.

Search starts a focused exploration; traversal budgets keep dense and cyclic
graphs bounded instead of returning an unreadable workspace-wide graph.
"""
from collections import Counter, defaultdict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import bindparam, text
from app.db import sql
from app.retrieval import CURRENT

ENTITY_JOIN = "FROM live_entities e JOIN document_versions v ON v.id=e.version_id JOIN documents d ON d.id=v.document_id"
ENTITY_ORDER = "ORDER BY e.canonical_id,v.created_at DESC,e.id"
KINDS = {"project", "person", "team", "task", "decision", "technology", "system", "event", "document"}



def execute_ids(conn, statement, ids, **params):
    return conn.execute(text(statement).bindparams(bindparam("ids", expanding=True)), {**params, "ids": [UUID(str(item)) for item in ids]})


def canonical_id(conn, viewer, entity_id):
    from app.main import entity_detail
    return entity_detail(conn, viewer, entity_id)["id"]


def pattern(value):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def kind_filter(kind, column="e.kind"):
    if kind and kind not in KINDS:
        raise HTTPException(422, "Unknown entity type.")
    return f" AND {column}=:kind" if kind else ""


def labels(conn, viewer, ids):
    if not ids:
        return {}
    rows = execute_ids(conn, f"""SELECT DISTINCT ON(e.canonical_id) e.canonical_id AS id,e.name,e.kind,
        v.filename,v.id AS version_id {ENTITY_JOIN} WHERE {CURRENT} AND e.canonical_id IN :ids
        {ENTITY_ORDER}""", ids, **viewer.access()).mappings().all()
    return {str(row.id): dict(row) for row in rows}


def counts_for(counts, entity_id):
    values = counts.get(str(entity_id), Counter())
    incoming, outgoing = values["incoming"], values["outgoing"]
    return {"incoming_count": incoming, "outgoing_count": outgoing, "connection_count": incoming + outgoing}


def neighbor_counts(conn, viewer, ids, kind=None, relationship=None):
    counts = defaultdict(Counter)
    if not ids:
        return counts
    predicate_filter = " AND r.predicate=:relationship" if relationship else ""
    rows = execute_ids(conn, """SELECT s.canonical_id AS source,t.canonical_id AS target,s.kind AS source_kind,t.kind AS target_kind
        FROM live_relationships r JOIN live_entities s ON s.id=r.source_id JOIN live_entities t ON t.id=r.target_id
        JOIN document_versions v ON v.id=r.version_id JOIN documents d ON d.id=v.document_id
        WHERE """ + CURRENT + " AND (s.canonical_id IN :ids OR t.canonical_id IN :ids)" + predicate_filter,
        ids, **viewer.access(), relationship=relationship).mappings().all()
    for row in rows:
        if row.source in ids and (not kind or row.target_kind == kind):
            counts[str(row.source)]["outgoing"] += 1
        if row.target in ids and (not kind or row.source_kind == kind):
            counts[str(row.target)]["incoming"] += 1
    return counts


def search(conn, viewer, query, kind=None, offset=0, limit=8):
    """Search all accessible entities, not only the current canvas."""
    params = {**viewer.access(), "q": pattern(query), "raw_q": query,
              "kind": kind, "limit": limit, "offset": offset}
    matching = f"""SELECT e.canonical_id,e.name,e.kind,e.version_id {ENTITY_JOIN}
        WHERE {CURRENT} {kind_filter(kind)} AND (e.name ILIKE :q ESCAPE '\\'
        OR EXISTS(SELECT 1 FROM entity_identifiers i WHERE i.organization_id=e.organization_id
          AND i.canonical_id=e.canonical_id AND i.value ILIKE :q ESCAPE '\\')
        OR EXISTS(SELECT 1 FROM entity_aliases a WHERE a.organization_id=e.organization_id
          AND a.canonical_id=e.canonical_id AND a.alias ILIKE :q ESCAPE '\\'))"""
    total = sql(conn, f"SELECT count(DISTINCT canonical_id) FROM ({matching}) matched", **params).scalar_one()
    rows = sql(conn, f"""WITH matched AS ({matching}), occurrences AS (
        SELECT canonical_id AS id,min(name) AS name,min(kind) AS kind,
          min(CASE WHEN lower(name)=lower(:raw_q) THEN 0 WHEN name ILIKE :q ESCAPE '\\' THEN 1 ELSE 2 END) AS rank
          FROM matched GROUP BY canonical_id)
        SELECT id,name,kind FROM occurrences ORDER BY rank,name,id LIMIT :limit OFFSET :offset""",
        **params).mappings().all()
    found_labels = labels(conn, viewer, [row.id for row in rows])
    counts = neighbor_counts(conn, viewer, [row.id for row in rows])
    nodes = [{**found_labels[str(row.id)], **counts_for(counts, row.id)}
             for row in rows if str(row.id) in found_labels]
    return {"nodes": nodes, "total": total, "offset": offset, "limit": limit,
            "has_more": offset + len(nodes) < total}


def relationship_types(conn, viewer):
    rows = sql(conn, """SELECT DISTINCT r.predicate FROM live_relationships r
        JOIN document_versions v ON v.id=r.version_id JOIN documents d ON d.id=v.document_id
        WHERE """ + CURRENT + " ORDER BY r.predicate", **viewer.access()).scalars().all()
    return list(rows)



def frontier_rows(conn, viewer, frontier, params, row_budget):
    """Select edges first; derive the opposite endpoint without a CASE join."""
    statement = f"""SELECT r.id,s.canonical_id AS source,t.canonical_id AS target,
        r.predicate AS label,r.effective_from,r.effective_to,r.chunk_id,
        CASE WHEN s.canonical_id IN :ids THEN t.kind ELSE s.kind END AS other_kind
        FROM live_relationships r JOIN live_entities s ON s.id=r.source_id JOIN live_entities t ON t.id=r.target_id
        JOIN document_versions v ON v.id=r.version_id JOIN documents d ON d.id=v.document_id
        WHERE {CURRENT} AND (s.canonical_id IN :ids OR t.canonical_id IN :ids)
        {params['edge_filter']} ORDER BY r.id LIMIT :row_budget"""
    rows = execute_ids(conn, statement, frontier, **params["values"], row_budget=row_budget).mappings().all()
    return [{**dict(row), "neighbor": row.target if row.source in frontier else row.source} for row in rows]


def explore(conn, viewer, root, depth=1, kind=None, relationship=None, offset=0, limit=24):
    """Breadth-first traversal with explicit node/edge budgets and stable pages.

    Offset pages immediate neighbors, allowing high-degree nodes to be explored.
    Deeper hops remain bounded; truncation is explicit in the response.
    """
    root = UUID(str(canonical_id(conn, viewer, root)))
    if str(root) not in labels(conn, viewer, [root]):
        raise HTTPException(404, "Entity not found.")
    edge_filter = " AND (CASE WHEN s.canonical_id IN :ids THEN t.kind ELSE s.kind END)=:kind" if kind else ""
    if relationship:
        edge_filter += " AND r.predicate=:relationship"
    params = {"values": {**viewer.access(), "kind": kind, "relationship": relationship}, "edge_filter": edge_filter}
    frontier, visited, edges, truncated = {root}, {root}, {}, False
    for level in range(depth):
        current = frontier
        if not current or len(visited) >= 80:
            truncated = truncated or bool(current)
            break
        if level == 0:
            neighbor_filter = kind_filter(kind, "other.kind")
            if relationship:
                neighbor_filter += " AND r.predicate=:relationship"
            neighbors = sql(conn, f"""SELECT DISTINCT other.canonical_id AS neighbor
                FROM live_relationships r JOIN live_entities s ON s.id=r.source_id JOIN live_entities t ON t.id=r.target_id
                JOIN live_entities other ON other.id=(CASE WHEN s.canonical_id=:root THEN t.id ELSE s.id END)
                JOIN document_versions v ON v.id=r.version_id JOIN documents d ON d.id=v.document_id
                WHERE {CURRENT} AND (s.canonical_id=:root OR t.canonical_id=:root)
                {neighbor_filter} ORDER BY other.canonical_id LIMIT :limit OFFSET :offset""",
                **params["values"], root=root, limit=limit + 1, offset=offset).mappings().all()
            truncated = truncated or len(neighbors) > limit
            frontier = {row.neighbor for row in neighbors[:limit]}
        rows = frontier_rows(conn, viewer, current, params, 121)
        if len(rows) > 120:
            rows, truncated = rows[:120], True
        next_frontier = set()
        for row in rows:
            # Page only the first hop; later hops discover new authorized neighbors.
            if row["source"] in current:
                neighbor = row["target"]
            elif row["target"] in current:
                neighbor = row["source"]
            else:
                continue
            if (level == 0 and neighbor not in frontier) or neighbor in current or neighbor == root:
                continue
            if len(visited) >= 80 and neighbor not in visited:
                truncated = True
                continue
            if str(row["id"]) not in edges and len(edges) >= 120:
                truncated = True
                continue
            edges[str(row["id"])] = {key: value for key, value in row.items() if key not in {"neighbor", "other_kind"}}
            if neighbor not in visited:
                next_frontier.add(neighbor)
                visited.add(neighbor)
        frontier = next_frontier
    found_labels = labels(conn, viewer, list(visited))
    # A concurrent permission change must not leave a partial relationship.
    edges = {key: edge for key, edge in edges.items()
             if str(edge["source"]) in found_labels and str(edge["target"]) in found_labels}
    counts = neighbor_counts(conn, viewer, [UUID(key) for key in found_labels], kind, relationship)
    filtered_counts = counts
    conflicts = []
    if found_labels:
        from app.main import CONFLICT_QUERY
        conflicts = sql(conn, CONFLICT_QUERY + " AND f.status IN ('open','needs_evidence')", **viewer.access()).mappings().all()
    conflict_counts = Counter(str(row.canonical_id) for row in conflicts)
    nodes = [{**found_labels[key], **counts_for(filtered_counts, UUID(key)),
              "conflict_count": conflict_counts.get(key, 0)} for key in found_labels]
    ordered = sorted(nodes, key=lambda node: (node["id"] != root, node["name"], str(node["id"])))
    return {"root": str(root), "depth": depth, "nodes": ordered, "edges": list(edges.values()),
            "truncated": truncated, "visible_node_count": len(ordered),
            "visible_edge_count": len(edges),
            "root_connection_count": filtered_counts[str(root)]["incoming"] + filtered_counts[str(root)]["outgoing"]}


def overview(conn, viewer, query):
    """An exact/near entity match supplements, never replaces, passage search."""
    found = search(conn, viewer, query, limit=1)
    if not found["nodes"]:
        return None
    entity = found["nodes"][0]
    terms = [term.casefold() for term in query.split() if len(term) > 2]
    name = entity["name"].casefold()
    # Exact entity/identifier matches are useful project/person summaries.
    # Broad questions must stay on ordinary passage search.
    identifier_match = any(
        sql(conn, f"""SELECT 1 {ENTITY_JOIN} WHERE {CURRENT} AND e.canonical_id=:id
            AND (lower(e.name)=lower(:query) OR EXISTS(
              SELECT 1 FROM entity_identifiers i WHERE i.organization_id=e.organization_id
              AND i.canonical_id=e.canonical_id AND lower(i.value)=lower(:query))) LIMIT 1""",
            **viewer.access(), id=entity["id"], query=query).first()
    )
    if not terms and not identifier_match:
        return None
    if terms and not identifier_match and not any(term in name or name in term for term in terms):
        return None
    graph = explore(conn, viewer, entity["id"], depth=1, limit=8)
    return {"entity": entity, "graph": graph}
