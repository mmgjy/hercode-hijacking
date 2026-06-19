import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { StateBox, Spinner } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type { StageStatus } from "@/lib/api/types";

export const Route = createFileRoute("/discovery/$runId")({
  head: () => ({ meta: [{ title: "Discovery progress — Hijacking" }] }),
  component: Progress,
});

const stageDot: Record<StageStatus, string> = {
  pending: "bg-muted-foreground/30",
  running: "bg-action-contact animate-pulse",
  complete: "bg-action-test",
  partial: "bg-action-research",
  failed: "bg-action-reject",
};

function Progress() {
  const { runId } = Route.useParams();
  const { mode } = useMode();

  const { data: run, isLoading, error, refetch } = useQuery({
    queryKey: ["run", mode, runId],
    queryFn: () => api.getRun(mode, runId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "complete" || s === "failed" || s === "partial" ? false : 1500;
    },
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight">Discovery progress</h1>

        {isLoading && <Spinner label="Loading discovery run…" />}

        {error && (
          <StateBox title="Could not load run" description={(error as ApiError).message} tone="error">
            <Button variant="outline" onClick={() => refetch()}>Retry</Button>
          </StateBox>
        )}

        {run && (
          <>
            <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 rounded-xl border bg-card p-5 text-sm sm:grid-cols-3">
              <Meta label="Run ID" value={run.id} />
              <Meta label="Start time" value={new Date(run.startedAt).toLocaleString()} />
              <Meta label="Mode" value={run.mode.toUpperCase()} />
              <Meta label="Source set" value={run.sourceSetName} />
              <Meta label="Raw signals" value={String(run.rawSignals)} />
              <Meta label="Normalized signals" value={String(run.normalizedSignals)} />
              <Meta label="Opportunity clusters" value={String(run.clusters)} />
            </dl>

            <ol className="mt-6 space-y-2">
              {run.stages.map((stage, i) => (
                <li key={stage.key} className="flex items-start gap-3 rounded-lg border bg-card p-3">
                  <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${stageDot[stage.status]}`} aria-hidden />
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">
                        {i + 1}. {stage.label}
                      </span>
                      <span className="text-xs uppercase tracking-wider text-muted-foreground">{stage.status}</span>
                    </div>
                    {stage.detail && <p className="mt-0.5 text-xs text-muted-foreground">{stage.detail}</p>}
                  </div>
                </li>
              ))}
            </ol>

            {run.warnings.length > 0 && (
              <div className="mt-4 rounded-lg border border-action-research/40 bg-action-research/5 p-4">
                <p className="text-sm font-medium text-foreground">Warnings</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {run.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-6 flex items-center gap-3">
              {run.status === "complete" || run.status === "partial" ? (
                <Button asChild>
                  <Link to="/" >View discovered opportunities</Link>
                </Button>
              ) : run.status === "failed" ? (
                <StateBox title="Discovery failed" description="Live collection failed. See stage status above." tone="error">
                  <Button variant="outline" onClick={() => refetch()}>Retry</Button>
                </StateBox>
              ) : (
                <Spinner label="Discovery running…" />
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
    </div>
  );
}
