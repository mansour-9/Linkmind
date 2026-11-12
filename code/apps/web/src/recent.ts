import type { Entity } from "./api";

function recentKey(token: string) {
  return "company-brain:recent:" + token;
}

export function getRecent(token: string): string[] {
  try {
    const items: unknown = JSON.parse(sessionStorage.getItem(recentKey(token)) ?? "[]");
    return Array.isArray(items) ? items.filter((id): id is string => typeof id === "string").slice(0, 8) : [];
  } catch {
    return [];
  }
}

export function rememberEntity(token: string, entity: Entity) {
  try {
    sessionStorage.setItem(recentKey(token), JSON.stringify([
      entity.id, ...getRecent(token).filter((id) => id !== entity.id),
    ].slice(0, 8)));
  } catch {
    // Browsing still works when storage is unavailable.
  }
}

export function graphLink(id: string) {
  return "/graph?" + new URLSearchParams({ node: id }).toString();
}
