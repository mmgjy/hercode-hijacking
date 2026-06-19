import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { ActionBadge, OriginBadgeTag } from "@/components/badges";
import { StateBox, Spinner } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type { OpportunitySummary } from "@/lib/api/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Hijacking" },
      { name: "description", content: "Emerging retail opportunities discovered from global sources and validated against the Swiss market." },
    ],
  }),
  component: Dashboard,
});

const coverageLabel: Record<OpportunitySummary["swissCoverage"], string> = {
  none: "None",
  partial: "Partial",
  "well-covered": "Well covered",
};

function Dashboard() {
  const { mode } = useMode();
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["opportunities", mode],
    queryFn: () => api.listOpportunities(mode),
  });

  return (
    <AppShell>
      <section className="mb-8 grid gap-6 rounded-xl border bg-card p-8 lg:grid-cols-[1.4fr_1fr] lg:items-center">
        <div>
          <div className="mb-3 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-brand" aria-hidden />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Retail Opportunity Decision Engine
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Hijacking finds repeated product, feature, and material signals across global retail sources.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            It checks whether the opportunity is under-served in Switzerland and recommends what the retailer should do
            next. Trend platforms show what is rising. Hijacking shows whether the local opportunity is real, whether it
            fits Switzerland, and what evidence would justify action.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild>
              <Link to="/discover">Run opportunity discovery</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/discovery/$runId" params={{ runId: "run_demo_0421" }}>
                Open demo results
              </Link>
            </Button>
          </div>
        </div>
        <div className="rounded-lg border bg-surface p-5 text-sm">
          <p className="font-medium text-foreground">Workflow</p>
          <ol className="mt-3 space-y-2 text-muted-foreground">
            <li>1. Global signals</li>
            <li>2. Automatic opportunity discovery</li>
            <li>3. Swiss competitor coverage scan</li>
            <li>4. Local transferability assessment</li>
            <li>5. Evidence-backed retail action</li>
          </ol>
        </div>
      </section>

      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Discovered opportunities</h2>
          <p className="text-sm text-muted-foreground">
            Emerging opportunities discovered from the configured global source set and validated against the Swiss market.
          </p>
        </div>
      </div>

      {isLoading && <Spinner label="Loading opportunities…" />}

      {error && (
        <StateBox
          title={mode === "live" ? "Backend unavailable" : "Could not load opportunities"}
          description={(error as ApiError).message}
          tone="error"
        >
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </StateBox>
      )}

      {!isLoading && !error && (!data || data.length === 0) && (
        <StateBox title="No opportunities yet" description="Start a discovery run to surface opportunities.">
          <Button asChild>
            <Link to="/discover">Run opportunity discovery</Link>
          </Button>
        </StateBox>
      )}

      {!isLoading && !error && data && data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <table className="w-full min-w-[980px] border-collapse text-sm">
            <caption className="sr-only">Discovered retail opportunities</caption>
            <thead>
              <tr className="border-b bg-surface text-xs uppercase tracking-wider text-muted-foreground">
                <th scope="col" className="px-3 py-2.5 font-medium">Rank</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Opportunity</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Strongest market</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Global signal</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Swiss fit</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Swiss coverage</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Opportunity</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Confidence</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Action</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Main missing evidence</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o) => (
                <tr
                  key={o.id}
                  tabIndex={0}
                  onClick={() => navigate({ to: "/opportunities/$id", params: { id: o.id } })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate({ to: "/opportunities/$id", params: { id: o.id } });
                  }}
                  className="cursor-pointer border-b last:border-0 transition-colors hover:bg-secondary/60 focus-visible:bg-secondary focus-visible:outline-none"
                >
                  <td className="px-3 py-3 tabular-nums text-muted-foreground">{o.rank}</td>
                  <td className="px-3 py-3 font-medium">
                    <span className="flex items-center gap-2">
                      {o.name}
                      <OriginBadgeTag origin={o.origin} />
                    </span>
                  </td>
                  <td className="px-3 py-3">{o.strongestMarket}</td>
                  <td className="px-3 py-3 tabular-nums">{o.globalSignal}</td>
                  <td className="px-3 py-3 tabular-nums">{o.swissFit}</td>
                  <td className="px-3 py-3">{coverageLabel[o.swissCoverage]}</td>
                  <td className="px-3 py-3 font-semibold tabular-nums">{o.opportunityScore}</td>
                  <td className="px-3 py-3 tabular-nums">{o.confidence}</td>
                  <td className="px-3 py-3"><ActionBadge action={o.action} /></td>
                  <td className="px-3 py-3 text-muted-foreground">{o.mainMissingEvidence}</td>
                  <td className="px-3 py-3 text-xs capitalize text-muted-foreground">{o.discoveryStatus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
