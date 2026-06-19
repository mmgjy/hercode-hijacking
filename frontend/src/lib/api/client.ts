import type {
  DiscoveryRun,
  DiscoveryRunInput,
  EvidenceRecord,
  OpportunityDetail,
  OpportunityMapData,
  OpportunitySummary,
  Recommendation,
  RetailerCoverage,
  RunMode,
  ScanItem,
  SourceSet,
  SourceStatus,
} from "./types";
import {
  demoCoverage,
  demoEvidence,
  demoMapData,
  demoOpportunities,
  demoOpportunityDetails,
  demoRun,
  demoScanItems,
  demoSourceSets,
  demoSources,
} from "../demo/fixtures";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public errorType = "request_failed",
  ) {
    super(message);
  }
}

async function liveGet<T>(path: string): Promise<T> {
  if (!BASE) throw new ApiError("Live backend not configured (VITE_API_BASE_URL is empty).", undefined, "not_configured");
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`);
  } catch (e) {
    throw new ApiError(`Backend unavailable: ${(e as Error).message}`, undefined, "network");
  }
  if (!res.ok) throw new ApiError(`Request failed (${res.status})`, res.status, "http_error");
  return (await res.json()) as T;
}

async function livePost<T>(path: string, body?: unknown): Promise<T> {
  if (!BASE) throw new ApiError("Live backend not configured (VITE_API_BASE_URL is empty).", undefined, "not_configured");
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError(`Backend unavailable: ${(e as Error).message}`, undefined, "network");
  }
  if (!res.ok) throw new ApiError(`Request failed (${res.status})`, res.status, "http_error");
  return (await res.json()) as T;
}

// ---- Demo mutable state (scan reviews) persisted in localStorage ----
const REVIEW_KEY = "hijacking-demo-reviews";

function loadReviews(): Record<string, { status: ScanItem["reviewStatus"]; note?: string }> {
  if (typeof localStorage === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(REVIEW_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function saveReviews(r: Record<string, { status: ScanItem["reviewStatus"]; note?: string }>) {
  if (typeof localStorage !== "undefined") localStorage.setItem(REVIEW_KEY, JSON.stringify(r));
}

export function resetDemoState() {
  if (typeof localStorage !== "undefined") localStorage.removeItem(REVIEW_KEY);
}

function applyReviews(items: ScanItem[]): ScanItem[] {
  const reviews = loadReviews();
  return items.map((i) => (reviews[i.id] ? { ...i, reviewStatus: reviews[i.id].status, reviewNote: reviews[i.id].note } : i));
}

// ---- Public API ----
export const api = {
  health: (mode: RunMode) => (mode === "demo" ? Promise.resolve({ status: "ok", mode: "demo" }) : liveGet<{ status: string }>("/health")),

  sourceSets: (mode: RunMode): Promise<SourceSet[]> =>
    mode === "demo" ? Promise.resolve(demoSourceSets) : liveGet("/api/source-sets"),

  sources: (mode: RunMode): Promise<SourceStatus[]> =>
    mode === "demo" ? Promise.resolve(demoSources) : liveGet("/api/sources"),

  getMap: (mode: RunMode): Promise<OpportunityMapData> =>
    mode === "demo" ? Promise.resolve(demoMapData) : liveGet("/api/opportunity-map"),

  createRun: (mode: RunMode, input: DiscoveryRunInput): Promise<{ id: string }> =>
    mode === "demo" ? Promise.resolve({ id: demoRun.id }) : livePost("/api/discovery-runs", input),

  getRun: (mode: RunMode, id: string): Promise<DiscoveryRun> =>
    mode === "demo" ? Promise.resolve({ ...demoRun, id }) : liveGet(`/api/discovery-runs/${id}`),

  getRunOpportunities: (mode: RunMode, id: string): Promise<OpportunitySummary[]> =>
    mode === "demo" ? Promise.resolve(demoOpportunities.map((o) => ({ ...o, runId: id }))) : liveGet(`/api/discovery-runs/${id}/opportunities`),

  listOpportunities: (mode: RunMode): Promise<OpportunitySummary[]> =>
    mode === "demo" ? Promise.resolve(demoOpportunities) : liveGet(`/api/discovery-runs/latest/opportunities`),

  getOpportunity: (mode: RunMode, id: string): Promise<OpportunityDetail> => {
    if (mode === "demo") {
      const d = demoOpportunityDetails[id];
      if (!d) return Promise.reject(new ApiError("Opportunity not found", 404, "not_found"));
      return Promise.resolve(d);
    }
    return liveGet(`/api/opportunities/${id}`);
  },

  getEvidence: (mode: RunMode, id: string): Promise<EvidenceRecord[]> =>
    mode === "demo" ? Promise.resolve(demoEvidence(id)) : liveGet(`/api/opportunities/${id}/evidence`),

  getCoverage: (mode: RunMode, id: string): Promise<RetailerCoverage[]> =>
    mode === "demo" ? Promise.resolve(demoCoverage(id)) : liveGet(`/api/opportunities/${id}/coverage`),

  getScanItems: (mode: RunMode, id: string): Promise<ScanItem[]> =>
    mode === "demo" ? Promise.resolve(applyReviews(demoScanItems(id))) : liveGet(`/api/opportunities/${id}/scan-items`),

  getRecommendation: (mode: RunMode, id: string): Promise<Recommendation> =>
    mode === "demo"
      ? Promise.resolve(demoOpportunityDetails[id]?.recommendation ?? Promise.reject(new ApiError("Not found", 404)))
      : liveGet(`/api/opportunities/${id}/recommendation`),

  reviewScanItem: (
    mode: RunMode,
    id: string,
    body: { status: ScanItem["reviewStatus"]; note?: string },
  ): Promise<{ ok: true }> => {
    if (mode === "demo") {
      const reviews = loadReviews();
      reviews[id] = { status: body.status, note: body.note };
      saveReviews(reviews);
      return Promise.resolve({ ok: true });
    }
    return livePost(`/api/scan-items/${id}/review`, body);
  },

  recalculate: (mode: RunMode, id: string): Promise<Recommendation> =>
    mode === "demo"
      ? Promise.resolve(demoOpportunityDetails[id]?.recommendation ?? Promise.reject(new ApiError("Not found", 404)))
      : livePost(`/api/opportunities/${id}/recalculate`),

  exportUrl: (id: string, format: "json" | "csv") => `${BASE}/api/opportunities/${id}/export.${format}`,

  resetDemo: (mode: RunMode): Promise<{ ok: true }> => {
    resetDemoState();
    if (mode === "live") return livePost("/api/demo/reset");
    return Promise.resolve({ ok: true });
  },
};
