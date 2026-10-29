import type {
  Catalog,
  DraftBody,
  ImageHit,
  PictureInfo,
  Piece,
  ReadingProps,
  Settings,
  HandoutInfo,
  VideoInfo,
  VoiceCatalog,
} from "./types";

const API_BASE = "http://127.0.0.1:8776";

export type ProgressEvent = {
  kind: string;
  id?: string;
  label?: string;
  status?: "active" | "done";
  detail?: string;
  message?: string;
  record?: unknown;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let detail = response.statusText || "请求失败";
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function readProgress<T>(path: string, body: unknown, onEvent: (event: ProgressEvent) => void): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText || "请求失败";
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  if (!response.body) throw new Error("没有收到生成进度");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let record: T | null = null;
  const take = (block: string) => {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("");
    if (!data) return;
    const event = JSON.parse(data) as ProgressEvent;
    if (event.kind === "error") throw new Error(event.message || "生成失败");
    if (event.kind === "done") {
      record = event.record as T;
      return;
    }
    onEvent(event);
  };
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) take(part);
  }
  if (buffer.trim()) take(buffer);
  if (record === null) throw new Error("生成没有完成");
  return record;
}

export const api = {
  catalog: () => request<Catalog>("/catalog"),
  piece: (id: string) => request<Piece>(`/pieces/${encodeURIComponent(id)}`),
  voices: () => request<VoiceCatalog>("/voices"),
  sample: (role: string, lang: "zh" | "en", text = "") =>
    request<{ url: string; audioMs: number }>("/tts/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, lang, text }),
    }),
  settings: () => request<Settings>("/settings"),
  saveSettings: (pixabayKey: string | null) =>
    request<Settings>("/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pixabayKey }),
    }),
  saveDraft: (id: string, body: DraftBody) =>
    request<Piece>(`/pieces/${encodeURIComponent(id)}/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  resetDraft: (id: string) => request<Piece>(`/pieces/${encodeURIComponent(id)}/draft`, { method: "DELETE" }),
  keyword: (en: string, zh: string) =>
    request<{ keyword: string }>("/keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ en, zh }),
    }),
  resolvePicture: (keyword: string) => request<PictureInfo>(`/pictures/resolve?keyword=${encodeURIComponent(keyword)}`),
  searchImages: (query: string) => request<{ hits: ImageHit[] }>(`/images/search?q=${encodeURIComponent(query)}&limit=8`),
  importPicture: (hit: ImageHit, keyword: string) =>
    request<PictureInfo>("/pictures/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: hit.url, source: hit.source, credit: hit.credit, keyword }),
    }),
  preview: (id: string, body: DraftBody, onEvent: (event: ProgressEvent) => void) =>
    readProgress<ReadingProps>(`/pieces/${encodeURIComponent(id)}/preview/stream`, body, onEvent),
  render: (id: string, body: DraftBody, onEvent: (event: ProgressEvent) => void) =>
    readProgress<VideoInfo>(`/pieces/${encodeURIComponent(id)}/video/stream`, body, onEvent),
  handout: (id: string, body: DraftBody, onEvent: (event: ProgressEvent) => void) =>
    readProgress<HandoutInfo>(`/pieces/${encodeURIComponent(id)}/handout/stream`, body, onEvent),
};
