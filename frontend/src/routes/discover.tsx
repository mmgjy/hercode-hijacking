import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { StateBox } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type { DiscoveryRunInput } from "@/lib/api/types";

export const Route = createFileRoute("/discover")({
  head: () => ({
    meta: [
      { title: "Run opportunity discovery — Hijacking" },
      { name: "description", content: "Start an automatic discovery run over configured global sources." },
    ],
  }),
  component: Discover,
});

const labelCls = "block text-sm font-medium text-foreground";
const fieldCls =
  "mt-1.5 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function Discover() {
  const { mode } = useMode();
  const navigate = useNavigate();

  const sourceSetsQ = useQuery({ queryKey: ["source-sets", mode], queryFn: () => api.sourceSets(mode) });

  const [form, setForm] = useState<DiscoveryRunInput>({
    category: "Outdoor retail",
    targetMarket: "Switzerland",
    sourceSetId: "outdoor-global-default",
    observationPeriod: "90",
    maxOpportunities: 5,
    focusKeywords: "",
  });

  const createRun = useMutation({
    mutationFn: () => api.createRun(mode, form),
    onSuccess: (res) => navigate({ to: "/discovery/$runId", params: { runId: res.id } }),
  });

  const set = <K extends keyof DiscoveryRunInput>(k: K, v: DiscoveryRunInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight">Run opportunity discovery</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The system discovers opportunities automatically. You configure the scope of the run only.
        </p>

        <form
          className="mt-6 space-y-5 rounded-xl border bg-card p-6"
          onSubmit={(e) => {
            e.preventDefault();
            createRun.mutate();
          }}
        >
          <div>
            <label className={labelCls} htmlFor="category">Category</label>
            <input
              id="category"
              className={fieldCls}
              value={form.category}
              onChange={(e) => set("category", e.target.value)}
            />
          </div>

          <div>
            <label className={labelCls} htmlFor="market">Target market</label>
            <input
              id="market"
              className={fieldCls}
              value={form.targetMarket}
              onChange={(e) => set("targetMarket", e.target.value)}
            />
          </div>

          <div>
            <label className={labelCls} htmlFor="sourceset">Source set</label>
            <select
              id="sourceset"
              className={fieldCls}
              value={form.sourceSetId}
              onChange={(e) => set("sourceSetId", e.target.value)}
            >
              {(sourceSetsQ.data ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.sourceCount} sources)
                </option>
              ))}
            </select>
            {sourceSetsQ.isError && (
              <p className="mt-1 text-xs text-action-reject">
                Could not load source sets: {(sourceSetsQ.error as ApiError).message}
              </p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls} htmlFor="period">Observation period</label>
              <select
                id="period"
                className={fieldCls}
                value={form.observationPeriod}
                onChange={(e) => set("observationPeriod", e.target.value as DiscoveryRunInput["observationPeriod"])}
              >
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="180">Last 180 days</option>
              </select>
            </div>
            <div>
              <label className={labelCls} htmlFor="max">Maximum opportunities</label>
              <select
                id="max"
                className={fieldCls}
                value={form.maxOpportunities}
                onChange={(e) => set("maxOpportunities", Number(e.target.value) as DiscoveryRunInput["maxOpportunities"])}
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </div>
          </div>

          <div>
            <label className={labelCls} htmlFor="keywords">Optional focus keywords</label>
            <input
              id="keywords"
              className={fieldCls}
              placeholder="technical apparel, materials, hiking, sun protection"
              value={form.focusKeywords}
              onChange={(e) => set("focusKeywords", e.target.value)}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Optional. Narrow discovery without providing an opportunity hypothesis.
            </p>
          </div>

          {createRun.isError && (
            <StateBox title="Could not start discovery" description={(createRun.error as ApiError).message} tone="error" />
          )}

          <div className="flex items-center gap-3 pt-1">
            <Button type="submit" disabled={createRun.isPending}>
              {createRun.isPending ? "Starting…" : "Start discovery"}
            </Button>
            <span className="text-xs text-muted-foreground">Mode: {mode === "demo" ? "Demo (fixtures)" : "Live"}</span>
          </div>

          <p className="rounded-md border bg-surface p-3 text-xs text-muted-foreground">
            Hijacking searches only the configured sources and selected observation period. It does not claim to scan the
            entire market.
          </p>
        </form>
      </div>
    </AppShell>
  );
}
