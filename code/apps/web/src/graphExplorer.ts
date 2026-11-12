import type { ExplorerGraph, ExplorerNode } from "./api";

export type Position = { x: number; y: number };
export function mergeGraphs(primary: ExplorerGraph | null, expansions: Record<string, ExplorerGraph>): ExplorerGraph {
  if (!primary) return { root: "", depth: 1, nodes: [], edges: [], truncated: false,
    visible_node_count: 0, visible_edge_count: 0, root_connection_count: 0 };
  const nodes = new Map(primary.nodes.map(node => [node.id, node]));
  const edges = new Map(primary.edges.map(edge => [edge.id, edge]));
  // Expansions only add nodes still connected to the current, authorized root.
  for (const graph of Object.values(expansions)) {
    if (!nodes.has(graph.root)) continue;
    graph.nodes.forEach(node => nodes.set(node.id, nodes.get(node.id) ?? node));
    graph.edges.forEach(edge => edges.set(edge.id, edge));
  }
  const visibleEdges = [...edges.values()].filter(edge => nodes.has(edge.source) && nodes.has(edge.target));
  return { ...primary, nodes: [...nodes.values()], edges: visibleEdges,
    truncated: primary.truncated || Object.values(expansions).some(graph => graph.truncated),
    visible_node_count: nodes.size, visible_edge_count: visibleEdges.length };
}

export function radialPositions(graph: ExplorerGraph, roots: string[], old: Map<string, Position> = new Map()) {
  const positions = new Map(old);
  const adjacency = new Map<string, string[]>();
  graph.nodes.forEach(node => adjacency.set(node.id, []));
  graph.edges.forEach(edge => {
    adjacency.get(edge.source)?.push(edge.target);
    adjacency.get(edge.target)?.push(edge.source);
  });
  const distance = new Map<string, number>();
  const queue = roots.filter(root => adjacency.has(root));
  queue.forEach(root => distance.set(root, 0));
  for (const id of queue) {
    for (const neighbor of adjacency.get(id) ?? []) {
      if (!distance.has(neighbor)) {
        distance.set(neighbor, (distance.get(id) ?? 0) + 1);
        queue.push(neighbor);
      }
    }
  }
  const rings = new Map<number, string[]>();
  graph.nodes.forEach(node => {
    const level = Math.min(distance.get(node.id) ?? 3, 3);
    if (!rings.has(level)) rings.set(level, []);
    rings.get(level)?.push(node.id);
  });
  for (const [level, ids] of rings) {
    ids.sort();
    ids.forEach((id, index) => {
      if (positions.has(id)) return;
      if (level === 0 && queue.length === 1) {
        positions.set(id, { x: 0, y: 0 });
        return;
      }
      const angle = (index / ids.length) * Math.PI * 2 - Math.PI / 2 + level * .27;
      const ring = level === 0 ? 245 : 240 + level * 180 + Math.floor(index / 12) * 85;
      positions.set(id, { x: Math.cos(angle) * ring + (level === 0 ? index * 300 : 0), y: Math.sin(angle) * ring * .76 });
    });
  }
  return positions;
}

export function connectedIds(graph: ExplorerGraph, selected: string | null) {
  if (!selected) return null;
  const ids = new Set([selected]);
  graph.edges.forEach(edge => {
    if (edge.source === selected) ids.add(edge.target);
    if (edge.target === selected) ids.add(edge.source);
  });
  return ids;
}
