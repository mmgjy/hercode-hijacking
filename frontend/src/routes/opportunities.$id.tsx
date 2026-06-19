import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { ActionBadge, OriginBadgeTag } from "@/components/badges";
import { ScoreBar } from "@/components/score-bar";
import { StateBox, Spinner } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type { OpportunityDetail, ScanItem } from "@/lib/api/types";

export const Route = createFileRoute("/opportunities/$id")({
  head: () => ({ meta: [{ title: "Opportunity — Hijacking" }] }),
  component: OpportunityPage,
});

function Section({ title, children, note }: { title: string; children: React.ReactNode; note?: string }) {
  return (
    <section className="rounded-xl border bg-card p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {note && <p className="mt-0.5 text-sm text-muted-foreground">{note}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function OpportunityPage() {
  const { id } = Route.useParams();
  const { mode } = useMode();
  const queryClient = useQueryClient();

  const oppQ = useQuery({ queryKey: ["opp", mode, id], queryFn: () => api.getOpportunity(mode, id) });
  const evidenceQ = useQuery({ queryKey: ["evidence", mode, id], queryFn: () => api.getEvidence(mode, id) });
  const coverageQ = useQuery({ queryKey: ["coverage", mode, id], queryFn: () => api.getCoverage(mode, id) });
  const scanQ = useQuery({ queryKey: ["scan", mode, id], queryFn: () => api.getScanItems(mode, id) });

  const recalc = useMutation({
    mutationFn: () => api.recalculate(mode, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opp", mode, id] });
      toast.success("Decision recalculated", { description: "Only approved matches were used." });
    },
  });

  if (oppQ.isLoading) return <AppShell><Spinner label="Loading opportunity…" /></AppShell>;
  if (oppQ.error)
    return (
      <AppShell>
        <StateBox
          title={(oppQ.error as ApiError).status === 404 ? "Opportunity not found" : "Could not load opportunity"}
          description={(oppQ.error as ApiError).message}
          tone="error"
        >
          <Button variant="outline" asChild><Link to="/">Back to dashboard</Link></Button>
        </StateBox>
      </AppShell>
    );

  const opp = oppQ.data!;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <Link to="/" className="text-xs text-muted-foreground hover:text-foreground">← Dashboard</Link>
        </div>

        <Header opp={opp} onExport={() => exportOpportunity(mode, opp)} />

        <Section title="Decision summary">
          <p className="text-sm leading-relaxed text-foreground">{opp.decisionSummary}</p>
        </Section>

        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Score breakdown">
            <div className="space-y-4">
              {opp.scoreBreakdown.map((s) => (
                <ScoreBar key={s.key} label={s.label} value={s.value} origin={s.origin} explanation={s.explanation} calculatedAt={s.calculatedAt} />
              ))}
            </div>
          </Section>
          <Section title="Confidence">
            <div className="space-y-4">
              {opp.confidenceBreakdown.map((s) => (
                <ScoreBar key={s.key} label={s.label} value={s.value} origin={s.origin} explanation={s.explanation} calculatedAt={s.calculatedAt} />
              ))}
            </div>
          </Section>
        </div>

        <Rationale opp={opp} />

        <Section title="Global evidence inspector">
          {evidenceQ.isLoading && <Spinner label="Loading evidence…" />}
          {evidenceQ.error && <StateBox title="Could not load evidence" description={(evidenceQ.error as ApiError).message} tone="error" />}
          {evidenceQ.data && <EvidenceTable rows={evidenceQ.data} />}
        </Section>

        <Section
          title="Swiss transferability"
          note="Heuristic values are calculated from the Swiss market profile and are not verified sales data."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {opp.transferability.map((f) => (
              <div key={f.key} className="rounded-lg border bg-surface p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{f.label}</span>
                  <span className="text-sm font-semibold tabular-nums">{f.value}</span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-foreground/70" style={{ width: `${f.value}%` }} />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{f.reason}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">Basis: {f.basis} · Confidence {f.confidence}</p>
                {f.limitations && <p className="mt-1 text-[11px] text-action-research">{f.limitations}</p>}
                {f.heuristic && (
                  <span className="mt-2 inline-block rounded border border-action-contact/30 bg-action-contact/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-action-contact">
                    Calculated from market profile
                  </span>
                )}
              </div>
            ))}
          </div>
        </Section>

        <Section title="Swiss competitor coverage" note="Loaded from the backend; not hardcoded as live results.">
          {coverageQ.isLoading && <Spinner label="Loading coverage…" />}
          {coverageQ.error && <StateBox title="Could not load coverage" description={(coverageQ.error as ApiError).message} tone="error" />}
          {coverageQ.data && coverageQ.data.length === 0 && <StateBox title="No Swiss products found" />}
          {coverageQ.data && coverageQ.data.length > 0 && (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[820px] border-collapse text-sm">
                <thead>
                  <tr className="border-b bg-surface text-xs uppercase tracking-wider text-muted-foreground">
                    {["Retailer", "Approved", "Pending", "Rejected", "Brands", "Price range", "Features", "Availability", "Scan status", "Scan date", "Origin"].map((h) => (
                      <th key={h} scope="col" className="px-3 py-2.5 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {coverageQ.data.map((c) => (
                    <tr key={c.id} className="border-b last:border-0">
                      <td className="px-3 py-3 font-medium">{c.retailer}</td>
                      <td className="px-3 py-3 tabular-nums text-action-test">{c.approvedMatches}</td>
                      <td className="px-3 py-3 tabular-nums text-action-research">{c.pendingMatches}</td>
                      <td className="px-3 py-3 tabular-nums text-action-reject">{c.rejectedMatches}</td>
                      <td className="px-3 py-3 text-muted-foreground">{c.brands.join(", ") || "—"}</td>
                      <td className="px-3 py-3 text-muted-foreground">{c.priceRange}</td>
                      <td className="px-3 py-3 text-muted-foreground">{c.relevantFeatures.join(", ") || "—"}</td>
                      <td className="px-3 py-3 text-muted-foreground">{c.availability}</td>
                      <td className="px-3 py-3 text-xs capitalize text-muted-foreground">{c.scanStatus}</td>
                      <td className="px-3 py-3 text-xs text-muted-foreground">{c.scanDate}</td>
                      <td className="px-3 py-3"><OriginBadgeTag origin={c.origin} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <ProductMatchReview id={id} scanQ={scanQ} recalc={recalc} />

        <RisksSection opp={opp} />

        <Section title="Recommended action">
          <div className="flex items-center gap-3"><ActionBadge action={opp.recommendation.action} /><OriginBadgeTag origin={opp.recommendation.origin} /></div>
          {!opp.recommendation.complete && (
            <StateBox title="Recommendation incomplete" description="The backend response is incomplete. No recommendation is shown." tone="error" />
          )}
          <dl className="mt-4 space-y-3 text-sm">
            <KV label="Triggered rule" value={opp.recommendation.triggeredRule} />
            <KV label="Rationale" value={opp.recommendation.rationale} />
            <KVList label="Evidence supporting the action" items={opp.recommendation.supportingEvidence} />
            <KVList label="Evidence preventing a stronger action" items={opp.recommendation.preventingEvidence} />
            <KV label="Next operational step" value={opp.recommendation.nextStep} />
          </dl>
        </Section>

        {opp.action === "TEST" && opp.testPlan && (
          <Section title="Test plan" note="Suggested test template, not a sales forecast.">
            <dl className="grid gap-3 sm:grid-cols-2 text-sm">
              <KV label="Product scope" value={opp.testPlan.productScope} />
              <KV label="Suggested unit range" value={opp.testPlan.unitRange} />
              <KV label="Channel" value={opp.testPlan.channel} />
              <KV label="Duration" value={opp.testPlan.duration} />
              <KV label="Target customer" value={opp.testPlan.targetCustomer} />
              <KV label="Primary metric" value={opp.testPlan.primaryMetric} />
              <KVList label="Secondary metrics" items={opp.testPlan.secondaryMetrics} />
              <KV label="Suggested success threshold" value={opp.testPlan.successThreshold} />
              <KV label="Stop condition" value={opp.testPlan.stopCondition} />
              <KVList label="Main assumptions" items={opp.testPlan.assumptions} />
            </dl>
          </Section>
        )}
      </div>
    </AppShell>
  );
}

function Header({ opp, onExport }: { opp: OpportunityDetail; onExport: () => void }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ActionBadge action={opp.action} />
            <OriginBadgeTag origin={opp.origin} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">{opp.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{opp.productCategory}</p>
          <div className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
            <span><span className="text-muted-foreground">Strongest observed market:</span> {opp.strongestMarket}</span>
            <span><span className="text-muted-foreground">Earliest observed market in the available evidence:</span> {opp.earliestMarket}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex gap-6">
            <div className="text-right">
              <div className="text-2xl font-semibold tabular-nums">{opp.opportunityScore}</div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">Opportunity</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-semibold tabular-nums">{opp.confidence}</div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">Confidence</div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onExport}>Export JSON</Button>
            <Button variant="outline" size="sm" onClick={() => exportCsv(opp)}>Export CSV</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Rationale({ opp }: { opp: OpportunityDetail }) {
  const r = opp.rationale;
  const stats: [string, string][] = [
    ["Total raw signals", String(r.rawSignals)],
    ["Independent sources", String(r.independentSources)],
    ["Markets represented", r.markets.join(", ")],
    ["Brands represented", r.brands.join(", ")],
    ["Products represented", r.products.join(", ")],
    ["First observed", r.firstObserved],
    ["Latest observed", r.latestObserved],
    ["Dominant product type", r.dominantProductType],
    ["Dominant features", r.dominantFeatures.join(", ")],
    ["Dominant materials", r.dominantMaterials.join(", ")],
    ["Dominant customer segment", r.dominantSegment],
    ["Dominant usage occasion", r.dominantOccasion],
  ];
  return (
    <Section title="Why this opportunity was created">
      <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3 text-sm">
        {stats.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs uppercase tracking-wider text-muted-foreground">{k}</dt>
            <dd className="mt-0.5 font-medium">{v || "—"}</dd>
          </div>
        ))}
      </dl>
      <details className="mt-4 rounded-lg border bg-surface p-4">
        <summary className="cursor-pointer text-sm font-medium">How Hijacking grouped these signals</summary>
        <p className="mt-2 text-sm text-muted-foreground">{r.groupingExplanation}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          Normalized terms that caused clustering: {r.matchedTerms.join(", ")}
        </p>
      </details>
    </Section>
  );
}

function EvidenceTable({ rows }: { rows: import("@/lib/api/types").EvidenceRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[1000px] border-collapse text-sm">
        <thead>
          <tr className="border-b bg-surface text-xs uppercase tracking-wider text-muted-foreground">
            {["Source", "Type", "Market", "Date", "Signal", "Brand", "Feature/Material", "Price", "Direction", "Credibility", "Origin", "URL"].map((h) => (
              <th key={h} scope="col" className="px-3 py-2.5 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <Fragment key={e.id}>
              <tr className="border-b">
                <td className="px-3 py-3 font-medium">{e.source}</td>
                <td className="px-3 py-3 text-muted-foreground">{e.sourceType}</td>
                <td className="px-3 py-3">{e.market}</td>
                <td className="px-3 py-3 text-muted-foreground">{e.date}</td>
                <td className="px-3 py-3">{e.signal}</td>
                <td className="px-3 py-3 text-muted-foreground">{e.brand}</td>
                <td className="px-3 py-3 text-muted-foreground">{e.featureOrMaterial}</td>
                <td className="px-3 py-3 tabular-nums">{e.price}</td>
                <td className="px-3 py-3">
                  <span className={
                    e.direction === "supporting" ? "text-action-test" : e.direction === "counter" ? "text-action-reject" : "text-muted-foreground"
                  }>{e.direction}</span>
                </td>
                <td className="px-3 py-3 tabular-nums">{e.credibility}</td>
                <td className="px-3 py-3"><OriginBadgeTag origin={e.origin} /></td>
                <td className="px-3 py-3">
                  <a href={e.url} target="_blank" rel="noopener noreferrer" className="text-action-contact underline underline-offset-2">
                    Open
                  </a>
                </td>
              </tr>
              <tr className="border-b last:border-0">
                <td colSpan={12} className="px-3 pb-3">
                  <details>
                    <summary className="cursor-pointer text-xs text-muted-foreground">Inspect record</summary>
                    <div className="mt-2 grid gap-x-8 gap-y-2 rounded-md border bg-surface p-3 text-xs sm:grid-cols-2">
                      <span><b>Raw title:</b> {e.rawTitle}</span>
                      <span><b>Raw description:</b> {e.rawDescription}</span>
                      <span><b>Normalized product type:</b> {e.normalizedProductType}</span>
                      <span><b>Normalized features:</b> {e.normalizedFeatures.join(", ")}</span>
                      <span><b>Matched terms:</b> {e.matchedTerms.join(", ")}</span>
                      <span><b>Limitations:</b> {e.limitations || "—"}</span>
                      <span><b>Artifact:</b> {e.artifactRef}</span>
                    </div>
                  </details>
                </td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProductMatchReview({
  id,
  scanQ,
  recalc,
}: {
  id: string;
  scanQ: { data?: ScanItem[]; isLoading: boolean; error: Error | null };
  recalc: { mutate: () => void; isPending: boolean };
}) {
  const { mode } = useMode();
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});

  const review = useMutation({
    mutationFn: (vars: { itemId: string; status: ScanItem["reviewStatus"]; note?: string }) =>
      api.reviewScanItem(mode, vars.itemId, { status: vars.status, note: vars.note }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["scan", mode, id] }),
  });

  const items = scanQ.data ?? [];
  const pending = items.filter((i) => i.reviewStatus === "pending");
  if (!scanQ.isLoading && pending.length === 0 && items.length === 0) return null;

  return (
    <Section title="Product-match review">
      <div className="rounded-md border border-action-research/40 bg-action-research/5 p-3 text-sm">
        Only approved products contribute to Swiss coverage and assortment-gap calculations.
      </div>

      {scanQ.isLoading && <Spinner label="Loading scan items…" />}
      {scanQ.error && <StateBox title="Could not load scan items" description={scanQ.error.message} tone="error" />}

      {items.length > 0 && (
        <div className="mt-4 space-y-3">
          {items.map((it) => (
            <div key={it.id} className="rounded-lg border bg-surface p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{it.productName}</span>
                    <OriginBadgeTag origin={it.extractionOrigin} />
                    <span className={`text-xs font-medium ${
                      it.reviewStatus === "approved" ? "text-action-test" : it.reviewStatus === "rejected" ? "text-action-reject" : "text-action-research"
                    }`}>{it.reviewStatus}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {it.brand} · {it.price} · {it.retailer} · match {it.matchScore} · keywords: {it.matchedKeywords.join(", ")}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">Features: {it.features.join(", ")}</p>
                  <a href={it.productUrl} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-xs text-action-contact underline">
                    Product URL
                  </a>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" disabled={review.isPending}
                      onClick={() => review.mutate({ itemId: it.id, status: "approved", note: notes[it.id] })}>
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" disabled={review.isPending}
                      onClick={() => review.mutate({ itemId: it.id, status: "rejected", note: notes[it.id] })}>
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
              <input
                className="mt-3 w-full rounded-md border bg-card px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Add review note"
                defaultValue={it.reviewNote}
                onChange={(e) => setNotes((n) => ({ ...n, [it.id]: e.target.value }))}
              />
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <Button onClick={() => recalc.mutate()} disabled={recalc.isPending || pending.length > 0}>
          {recalc.isPending ? "Recalculating…" : "Recalculate decision"}
        </Button>
        {pending.length > 0 && (
          <span className="text-xs text-action-research">{pending.length} item(s) awaiting review before recalculation.</span>
        )}
      </div>
    </Section>
  );
}

function RisksSection({ opp }: { opp: OpportunityDetail }) {
  const groups: [string, string[]][] = [
    ["Counter-signals", opp.risks.counterSignals],
    ["Risks", opp.risks.risks],
    ["Missing evidence", opp.risks.missingEvidence],
    ["Internal retailer data required", opp.risks.internalDataRequired],
    ["Extraction limitations", opp.risks.extractionLimitations],
  ];
  return (
    <Section title="Risks and missing evidence">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {groups.map(([title, items]) => (
          <div key={title} className="rounded-lg border bg-surface p-4">
            <h3 className="text-sm font-medium">{title}</h3>
            {items.length === 0 ? (
              <p className="mt-1 text-xs text-muted-foreground">None recorded.</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                {items.map((i, idx) => <li key={idx}>{i}</li>)}
              </ul>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-foreground">{value}</dd>
    </div>
  );
}

function KVList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="mt-0.5">
        <ul className="list-disc space-y-0.5 pl-4 text-foreground">
          {items.map((i, idx) => <li key={idx}>{i}</li>)}
        </ul>
      </dd>
    </div>
  );
}

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportOpportunity(mode: "demo" | "live", opp: OpportunityDetail) {
  if (mode === "live") {
    window.open(api.exportUrl(opp.id, "json"), "_blank");
    return;
  }
  download(`${opp.id}.json`, JSON.stringify(opp, null, 2), "application/json");
}

function exportCsv(opp: OpportunityDetail) {
  const rows = [
    ["field", "value"],
    ["name", opp.name],
    ["action", opp.action],
    ["opportunityScore", String(opp.opportunityScore)],
    ["confidence", String(opp.confidence)],
    ["strongestMarket", opp.strongestMarket],
    ["swissCoverage", opp.swissCoverage],
    ...opp.scoreBreakdown.map((s) => [s.label, String(s.value)]),
  ];
  const csv = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  download(`${opp.id}.csv`, csv, "text/csv");
}
