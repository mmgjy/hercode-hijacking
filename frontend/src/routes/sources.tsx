import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { StateBox, Spinner } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type { SourceStatus } from "@/lib/api/types";

export const Route = createFileRoute("/sources")({
  head: () => ({
    meta: [
      { title: "Sources — Hijacking" },
      { name: "description", content: "Status of configured global discovery sources and Swiss validation sources." },
    ],
  }),
  component: Sources,
});

function Sources() {
  const { mode } = useMode();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sources", mode],
    queryFn: () => api.sources(mode),
  });

  const global = (data ?? []).filter((s) => s.scope === "global");
  const swiss = (data ?? []).filter((s) => s.scope === "swiss");

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Sources</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Source configuration is controlled by the backend or administrator. Regular users cannot add scraper domains.
      </p>

      {isLoading && <Spinner label="Loading sources…" />}
      {error && (
        <StateBox title="Could not load sources" description={(error as ApiError).message} tone="error">
          <Button variant="outline" onClick={() => refetch()}>Retry</Button>
        </StateBox>
      )}

      {data && (
        <div className="mt-6 space-y-8">
          <SourceTable
            title="Global discovery sources"
            subtitle="Used to find emerging product patterns."
            rows={global}
          />
          <SourceTable
            title="Swiss validation sources"
            subtitle="Used to measure local competitor coverage."
            rows={swiss}
          />
        </div>
      )}
    </AppShell>
  );
}

function SourceTable({ title, subtitle, rows }: { title: string; subtitle: string; rows: SourceStatus[] }) {
  return (
    <section>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
      <div className="mt-3 overflow-x-auto rounded-lg border bg-card">
        <table className="w-full min-w-[860px] border-collapse text-sm">
          <thead>
            <tr className="border-b bg-surface text-xs uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="px-3 py-2.5 font-medium">Source</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Type</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Geography</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Domain</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Active</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Last success</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Last error</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Mode</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Signals</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b last:border-0">
                <td className="px-3 py-3 font-medium">{s.name}</td>
                <td className="px-3 py-3 text-muted-foreground">{s.sourceType}</td>
                <td className="px-3 py-3 text-muted-foreground">{s.geography}</td>
                <td className="px-3 py-3 text-muted-foreground">{s.domain}</td>
                <td className="px-3 py-3">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-medium ${s.active ? "text-action-test" : "text-muted-foreground"}`}
                  >
                    <span className={`h-2 w-2 rounded-full ${s.active ? "bg-action-test" : "bg-muted-foreground/40"}`} aria-hidden />
                    {s.active ? "Active" : "Disabled"}
                  </span>
                </td>
                <td className="px-3 py-3 text-muted-foreground">
                  {s.lastSuccess ? new Date(s.lastSuccess).toLocaleString() : "—"}
                </td>
                <td className="px-3 py-3 text-xs text-action-reject">{s.lastError ?? "—"}</td>
                <td className="px-3 py-3 text-xs text-muted-foreground">{s.supportedMode}</td>
                <td className="px-3 py-3 tabular-nums">{s.signalsCollected}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
