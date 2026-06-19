import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { ActionBadge, OriginBadgeTag } from "@/components/badges";
import { StateBox, Spinner } from "@/components/states";
import { useMode } from "@/lib/mode";
import { api, ApiError } from "@/lib/api/client";
import type {
  ActionType,
  MapMarket,
  MapOpportunity,
  OpportunityMapData,
} from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/map")({
  head: () => ({
    meta: [
      { title: "Opportunity Map — Hijacking" },
      {
        name: "description",
        content:
          "Switzerland-centric opportunity flow: strongest observed markets, discovered opportunities, and recommended Swiss actions at a glance.",
      },
    ],
  }),
  component: OpportunityMap,
});

const actionColor: Record<ActionType, string> = {
  TEST: "var(--action-test)",
  CONTACT: "var(--action-contact)",
  RESEARCH: "var(--action-research)",
  MONITOR: "var(--action-monitor)",
  REJECT: "var(--action-reject)",
};

const ACTION_ORDER: ActionType[] = ["TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT"];
const ACTION_LABEL: Record<ActionType, string> = {
  TEST: "Test in Switzerland",
  CONTACT: "Contact suppliers",
  RESEARCH: "Research further",
  MONITOR: "Monitor only",
  REJECT: "Do not pursue",
};

function OpportunityMap() {
  const { mode } = useMode();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["opportunity-map", mode],
    queryFn: () => api.getMap(mode),
  });

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Opportunity Map</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Switzerland-centric flow — strongest markets, discovered opportunities, and the recommended Swiss action.
          </p>
        </div>
      </div>

      {isLoading && <Spinner label="Loading opportunity flow…" />}
      {error && (
        <StateBox
          title={mode === "live" ? "Backend unavailable" : "Could not load map"}
          description={(error as ApiError).message}
          tone="error"
        >
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </StateBox>
      )}

      {data && <FlowScreen data={data} />}
    </AppShell>
  );
}

function FlowScreen({ data }: { data: OpportunityMapData }) {
  const [actionFilter, setActionFilter] = useState<"all" | ActionType>("all");
  const [minConfidence, setMinConfidence] = useState(0);
  const [category, setCategory] = useState("all");
  const [period, setPeriod] = useState("all");
  const [sourceSet, setSourceSet] = useState("all");
  const [selectedOppId, setSelectedOppId] = useState<string | null>(null);
  const [selectedMarketId, setSelectedMarketId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);

  const visibleOpps = useMemo(
    () =>
      data.opportunities
        .filter((o) => (actionFilter === "all" || o.action === actionFilter) && o.confidence >= minConfidence)
        .sort((a, b) => b.opportunityScore - a.opportunityScore),
    [data, actionFilter, minConfidence],
  );
  const visibleOppIds = useMemo(() => new Set(visibleOpps.map((o) => o.id)), [visibleOpps]);

  const marketById = useMemo(() => new Map(data.markets.map((m) => [m.id, m])), [data]);

  // Strongest observed source markets (non-Swiss), highest momentum first.
  const sourceMarkets = useMemo(
    () =>
      data.markets
        .filter((m) => !m.isSwiss && m.opportunityIds.some((id) => visibleOppIds.has(id)) && m.confidence >= minConfidence)
        .sort((a, b) => b.signalStrength - a.signalStrength),
    [data, visibleOppIds, minConfidence],
  );

  // Recommended Swiss action buckets present among visible opportunities.
  const actionBuckets = useMemo(() => {
    const map = new Map<ActionType, MapOpportunity[]>();
    for (const o of visibleOpps) {
      const arr = map.get(o.action) ?? [];
      arr.push(o);
      map.set(o.action, arr);
    }
    return ACTION_ORDER.filter((a) => map.has(a)).map((a) => ({ action: a, opps: map.get(a)! }));
  }, [visibleOpps]);

  const selectedOpp = selectedOppId ? data.opportunities.find((o) => o.id === selectedOppId) ?? null : null;
  const selectedMarket = selectedMarketId ? marketById.get(selectedMarketId) ?? null : null;

  // Active node: the selected or hovered opportunity drives highlighting.
  const activeOppId = hoverId && visibleOppIds.has(hoverId) ? hoverId : selectedOppId;
  const activeOpp = activeOppId ? data.opportunities.find((o) => o.id === activeOppId) ?? null : null;
  const activeMarketCountries = activeOpp ? new Set(activeOpp.markets) : null;

  return (
    <div className="mt-5 space-y-4">
      <SummaryStrip data={data} />

      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-card p-3">
        <FilterSelect label="Category" value={category} onChange={setCategory} options={[["all", "All categories"], ["outdoor", "Outdoor retail"]]} />
        <FilterSelect
          label="Action"
          value={actionFilter}
          onChange={(v) => setActionFilter(v as "all" | ActionType)}
          options={[["all", "All actions"], ["TEST", "Test"], ["CONTACT", "Contact"], ["RESEARCH", "Research"], ["MONITOR", "Monitor"], ["REJECT", "Reject"]]}
        />
        <FilterSelect label="Period" value={period} onChange={setPeriod} options={[["all", "All periods"], ["30", "30 days"], ["90", "90 days"], ["180", "180 days"]]} />
        <FilterSelect label="Source set" value={sourceSet} onChange={setSourceSet} options={[["all", "All source sets"], ["outdoor-global-default", "Outdoor global default"]]} />
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Min confidence
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-28 accent-[var(--brand)]"
          />
          <span className="w-8 tabular-nums text-foreground">{minConfidence}</span>
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[7fr_3fr]">
        <div className="rounded-lg border bg-card p-4">
          <FlowDiagram
            sourceMarkets={sourceMarkets}
            opps={visibleOpps}
            actionBuckets={actionBuckets}
            activeOppId={activeOppId}
            activeMarketCountries={activeMarketCountries}
            selectedMarketId={selectedMarketId}
            selectedOppId={selectedOppId}
            onSelectMarket={(id) => {
              setSelectedMarketId(id);
              setSelectedOppId(null);
            }}
            onSelectOpp={(id) => {
              setSelectedOppId(id);
              setSelectedMarketId(null);
            }}
            onHover={setHoverId}
          />
          <MiniMap markets={sourceMarkets} highlight={activeMarketCountries} />
          <Legend />
        </div>

        <div className="rounded-lg border bg-card p-4">
          {selectedMarket ? (
            <MarketPanel market={selectedMarket} onBack={() => setSelectedMarketId(null)} />
          ) : selectedOpp ? (
            <OppPanel
              opp={selectedOpp}
              connection={data.connections.find((c) => c.opportunityId === selectedOpp.id) ?? null}
              onBack={() => setSelectedOppId(null)}
            />
          ) : (
            <OppList opps={visibleOpps} onSelect={(id) => { setSelectedOppId(id); setSelectedMarketId(null); }} />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------- Flow diagram with connecting lines ----------------

type Line = { x1: number; y1: number; x2: number; y2: number; active: boolean; color: string };

function FlowDiagram({
  sourceMarkets,
  opps,
  actionBuckets,
  activeOppId,
  activeMarketCountries,
  selectedMarketId,
  selectedOppId,
  onSelectMarket,
  onSelectOpp,
  onHover,
}: {
  sourceMarkets: MapMarket[];
  opps: MapOpportunity[];
  actionBuckets: { action: ActionType; opps: MapOpportunity[] }[];
  activeOppId: string | null;
  activeMarketCountries: Set<string> | null;
  selectedMarketId: string | null;
  selectedOppId: string | null;
  onSelectMarket: (id: string) => void;
  onSelectOpp: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const marketRefs = useRef(new Map<string, HTMLDivElement>());
  const oppRefs = useRef(new Map<string, HTMLDivElement>());
  const actionRefs = useRef(new Map<string, HTMLDivElement>());
  const [lines, setLines] = useState<Line[]>([]);
  const [size, setSize] = useState({ w: 0, h: 0 });

  const setRef = (m: React.MutableRefObject<Map<string, HTMLDivElement>>, id: string) => (el: HTMLDivElement | null) => {
    if (el) m.current.set(id, el);
    else m.current.delete(id);
  };

  const recompute = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const base = container.getBoundingClientRect();
    setSize({ w: base.width, h: base.height });

    const anchor = (el: HTMLDivElement | undefined, side: "left" | "right") => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: (side === "right" ? r.right : r.left) - base.left, y: r.top + r.height / 2 - base.top };
    };

    const next: Line[] = [];
    for (const o of opps) {
      const oppEl = oppRefs.current.get(o.id);
      const oppLeft = anchor(oppEl, "left");
      const oppRight = anchor(oppEl, "right");
      const isActive = activeOppId === o.id;

      // market -> opportunity
      for (const mk of sourceMarkets) {
        if (!mk.opportunityIds.includes(o.id)) continue;
        const from = anchor(marketRefs.current.get(mk.id), "right");
        if (from && oppLeft) {
          next.push({
            x1: from.x, y1: from.y, x2: oppLeft.x, y2: oppLeft.y,
            active: isActive, color: actionColor[o.action],
          });
        }
      }
      // opportunity -> action
      const to = anchor(actionRefs.current.get(o.action), "left");
      if (oppRight && to) {
        next.push({
          x1: oppRight.x, y1: oppRight.y, x2: to.x, y2: to.y,
          active: isActive, color: actionColor[o.action],
        });
      }
    }
    setLines(next);
  }, [opps, sourceMarkets, activeOppId]);

  useLayoutEffect(() => {
    recompute();
    const ro = new ResizeObserver(recompute);
    if (containerRef.current) ro.observe(containerRef.current);
    window.addEventListener("resize", recompute);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", recompute);
    };
  }, [recompute]);

  const dim = (isDimmed: boolean) => (activeOppId && isDimmed ? "opacity-40" : "opacity-100");

  return (
    <div ref={containerRef} className="relative">
      <svg className="pointer-events-none absolute inset-0 h-full w-full" width={size.w} height={size.h} aria-hidden>
        {lines.map((l, i) => {
          const mx = (l.x1 + l.x2) / 2;
          return (
            <path
              key={i}
              d={`M ${l.x1} ${l.y1} C ${mx} ${l.y1}, ${mx} ${l.y2}, ${l.x2} ${l.y2}`}
              fill="none"
              stroke={l.active ? l.color : "var(--border)"}
              strokeWidth={l.active ? 1.75 : 1}
              opacity={activeOppId ? (l.active ? 0.9 : 0.2) : 0.5}
            />
          );
        })}
      </svg>

      <div className="relative grid grid-cols-3 gap-x-6">
        {/* Column headers */}
        <ColHeader index={1} title="Strongest markets" hint="Where the signal is emerging" />
        <ColHeader index={2} title="Opportunities" hint="Switzerland is the reference market" center />
        <ColHeader index={3} title="Recommended Swiss action" hint="The decision" right />

        {/* Left: markets */}
        <div className="space-y-2 py-1">
          {sourceMarkets.length === 0 && <Empty>No markets match filters.</Empty>}
          {sourceMarkets.map((mk) => {
            const isDimmed = activeMarketCountries ? !activeMarketCountries.has(mk.country) : false;
            return (
              <div
                key={mk.id}
                ref={setRef(marketRefs, mk.id)}
                role="button"
                tabIndex={0}
                onClick={() => onSelectMarket(mk.id)}
                onKeyDown={(e) => e.key === "Enter" && onSelectMarket(mk.id)}
                className={cn(
                  "cursor-pointer rounded-lg border bg-surface px-3 py-2 transition-all hover:border-foreground/30",
                  selectedMarketId === mk.id && "border-foreground/50 ring-1 ring-foreground/20",
                  dim(isDimmed),
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium leading-tight">{mk.country}</span>
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: actionColor[mk.action] }} aria-hidden />
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-foreground/70" style={{ width: `${mk.signalStrength}%` }} />
                </div>
                <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
                  <span>Momentum <span className="tabular-nums text-foreground">{mk.signalStrength}</span></span>
                  <span>{mk.evidenceCount} ev.</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Middle: opportunities */}
        <div className="space-y-2 py-1">
          {opps.length === 0 && <Empty>No opportunities match filters.</Empty>}
          {opps.map((o) => {
            const isDimmed = activeOppId ? activeOppId !== o.id : false;
            return (
              <div
                key={o.id}
                ref={setRef(oppRefs, o.id)}
                role="button"
                tabIndex={0}
                onClick={() => onSelectOpp(o.id)}
                onKeyDown={(e) => e.key === "Enter" && onSelectOpp(o.id)}
                onMouseEnter={() => onHover(o.id)}
                onMouseLeave={() => onHover(null)}
                className={cn(
                  "cursor-pointer rounded-lg border bg-surface p-3 transition-all hover:border-foreground/30",
                  selectedOppId === o.id && "border-foreground/50 ring-1 ring-foreground/20",
                  dim(isDimmed),
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="flex items-start gap-1.5 text-sm font-medium leading-tight">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: actionColor[o.action] }} aria-hidden />
                    {o.name}
                  </span>
                  <ActionBadge action={o.action} />
                </div>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                  <span>Conf <span className="tabular-nums text-foreground">{o.confidence}</span></span>
                  <span>Swiss gap <span className="tabular-nums text-foreground">{o.swissGap}</span></span>
                  <span>From <span className="text-foreground">{o.strongestMarket}</span></span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: recommended Swiss action */}
        <div className="space-y-2 py-1">
          {actionBuckets.length === 0 && <Empty>No actions to recommend.</Empty>}
          {actionBuckets.map(({ action, opps: bucket }) => {
            const isDimmed = actionDimmed(action, activeOppId, opps);
            return (
              <div
                key={action}
                ref={setRef(actionRefs, action)}
                className={cn(
                  "rounded-lg border bg-surface p-3 transition-all",
                  dim(isDimmed),
                )}
                style={{ borderLeftColor: actionColor[action], borderLeftWidth: 3 }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold leading-tight">{ACTION_LABEL[action]}</span>
                  <ActionBadge action={action} />
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  {bucket.length} {bucket.length === 1 ? "opportunity" : "opportunities"}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Helper: whether an action bucket should be dimmed given the active opportunity.
function actionDimmed(action: ActionType, activeOppId: string | null, opps: MapOpportunity[]): boolean {
  if (!activeOppId) return false;
  const active = opps.find((o) => o.id === activeOppId);
  return !active || active.action !== action;
}

function ColHeader({ index, title, hint, center, right }: { index: number; title: string; hint: string; center?: boolean; right?: boolean }) {
  return (
    <div className={cn("mb-1 pb-2", center && "text-center", right && "text-right")}>
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {index}. {title}
      </div>
      <div className="text-[11px] text-muted-foreground/70">{hint}</div>
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">{children}</p>;
}

// ---------------- Miniature contextual world map ----------------

const VB_W = 1000;
const VB_H = 500;
const px = (lng: number) => ((lng + 180) / 360) * VB_W;
const py = (lat: number) => ((90 - lat) / 180) * VB_H;
const continents = [
  "M150,150 q40,-50 110,-40 q60,10 70,60 q10,60 -30,110 q-30,40 -90,30 q-60,-10 -70,-70 q-10,-60 10,-90 Z",
  "M300,280 q30,-20 55,5 q25,40 5,90 q-20,45 -55,30 q-25,-15 -20,-65 q5,-45 15,-60 Z",
  "M470,110 q40,-20 70,0 q20,25 -10,45 q-45,20 -70,-10 q-10,-25 10,-35 Z",
  "M490,190 q50,-15 80,15 q25,50 0,110 q-30,45 -65,25 q-30,-25 -25,-90 q5,-50 10,-60 Z",
  "M560,90 q90,-40 200,-15 q70,25 65,90 q-10,70 -120,80 q-110,5 -150,-50 q-25,-50 5,-105 Z",
  "M790,330 q40,-20 75,0 q20,25 -10,45 q-45,20 -70,-10 q-10,-25 5,-35 Z",
];

function MiniMap({ markets, highlight }: { markets: MapMarket[]; highlight: Set<string> | null }) {
  return (
    <div className="mt-4 border-t pt-3">
      <div className="mb-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">Geographic context</div>
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="h-auto w-full max-w-md" role="img" aria-label="Geographic context of source markets">
        {continents.map((d, i) => (
          <path key={i} d={d} fill="var(--muted)" stroke="var(--border)" strokeWidth={0.75} />
        ))}
        {markets.map((m) => {
          const dimmed = highlight ? !highlight.has(m.country) : false;
          return (
            <circle
              key={m.id}
              cx={px(m.lng)}
              cy={py(m.lat)}
              r={4 + (m.signalStrength / 100) * 8}
              fill={actionColor[m.action]}
              opacity={dimmed ? 0.25 : 0.85}
              stroke="white"
              strokeWidth={1}
            >
              <title>{`${m.country} · momentum ${m.signalStrength}`}</title>
            </circle>
          );
        })}
        {/* Switzerland reference */}
        <circle cx={px(8.2)} cy={py(46.8)} r={6} fill="none" stroke="var(--brand)" strokeWidth={2} />
        <text x={px(8.2)} y={py(46.8) - 12} textAnchor="middle" fontSize={13} fill="var(--brand)" className="select-none">CH</text>
      </svg>
    </div>
  );
}

// ---------------- Shared UI (summary, legend, filters, panels) ----------------

function SummaryStrip({ data }: { data: OpportunityMapData }) {
  const s = data.summary;
  const items: [string, string][] = [
    [`${s.totalOpportunities}`, "Opportunities"],
    [`${s.highestConfidence}`, "Highest confidence"],
    [`${s.highestSwissGap}`, "Highest Swiss gap"],
    [`${s.totalMarkets}`, "Markets observed"],
    [`${s.totalSources}`, "Evidence sources"],
  ];
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-3 lg:grid-cols-5">
      {items.map(([value, label]) => (
        <div key={label} className="bg-card px-4 py-3">
          <div className="text-2xl font-semibold tabular-nums tracking-tight">{value}</div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
        </div>
      ))}
    </div>
  );
}

function Legend() {
  const items: [ActionType, string][] = [
    ["TEST", "Test"],
    ["CONTACT", "Contact"],
    ["RESEARCH", "Research"],
    ["MONITOR", "Monitor"],
    ["REJECT", "Reject"],
  ];
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3 text-xs text-muted-foreground">
      {items.map(([a, label]) => (
        <span key={a} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: actionColor[a] }} aria-hidden />
          {label}
        </span>
      ))}
      <span className="ml-auto">Bar = momentum · Lines link evidence → opportunity → action</span>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border bg-background px-2 py-1 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function OppList({ opps, onSelect }: { opps: MapOpportunity[]; onSelect: (id: string) => void }) {
  return (
    <div>
      <h2 className="text-sm font-semibold">Opportunity clusters</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">Select a cluster to inspect, or click any node in the flow.</p>
      {opps.length === 0 && (
        <p className="mt-6 text-center text-sm text-muted-foreground">No opportunities match the current filters.</p>
      )}
      <ul className="mt-3 space-y-2">
        {opps.map((o) => (
          <li key={o.id}>
            <button
              onClick={() => onSelect(o.id)}
              className="w-full rounded-lg border bg-surface p-3 text-left transition-colors hover:bg-secondary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="flex items-center gap-1.5 text-sm font-medium leading-tight">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: actionColor[o.action] }} aria-hidden />
                  {o.name}
                </span>
                <ActionBadge action={o.action} />
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>Strongest: <span className="text-foreground">{o.strongestMarket}</span></span>
                <span>Conf <span className="tabular-nums text-foreground">{o.confidence}</span></span>
                <span>Swiss gap <span className="tabular-nums text-foreground">{o.swissGap}</span></span>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b py-1.5 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium tabular-nums">{value}</span>
    </div>
  );
}

function OppPanel({
  opp,
  connection,
  onBack,
}: {
  opp: MapOpportunity;
  connection: { sourceMarket: string; transferabilityScore: number; swissGapScore: number } | null;
  onBack: () => void;
}) {
  const coverageLabel = { none: "None", partial: "Partial", "well-covered": "Well covered" }[opp.swissCoverage];
  return (
    <div>
      <button onClick={onBack} className="text-xs text-muted-foreground hover:text-foreground">← Back to clusters</button>
      <div className="mt-2 flex items-start justify-between gap-2">
        <h2 className="text-base font-semibold leading-tight">{opp.name}</h2>
        <OriginBadgeTag origin={opp.origin} />
      </div>
      <div className="mt-2">
        <ActionBadge action={opp.action} />
      </div>

      {connection && (
        <div className="mt-3 rounded-lg border border-brand/30 bg-brand/5 p-3 text-sm">
          <div className="flex items-center justify-center gap-2 font-medium">
            <span>{connection.sourceMarket}</span>
            <span aria-hidden>→</span>
            <span className="text-brand">Switzerland</span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-center text-xs">
            <div className="rounded border bg-card py-1.5">
              <div className="text-base font-semibold tabular-nums">{connection.transferabilityScore}</div>
              <div className="text-muted-foreground">Transferability</div>
            </div>
            <div className="rounded border bg-card py-1.5">
              <div className="text-base font-semibold tabular-nums">{connection.swissGapScore}</div>
              <div className="text-muted-foreground">Swiss gap</div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-3">
        <Row label="Confidence" value={opp.confidence} />
        <Row label="Strongest observed market" value={opp.strongestMarket} />
        <Row label="Earliest observed market" value={opp.earliestMarket} />
        <Row label="Swiss fit" value={opp.swissFit} />
        <Row label="Swiss coverage" value={coverageLabel} />
        <Row label="Opportunity score" value={opp.opportunityScore} />
        <Row label="Signals" value={opp.signalCount} />
        <Row label="Sources" value={opp.sourceCount} />
        <Row label="Markets" value={opp.marketCount} />
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <div>
          <div className="font-medium text-foreground">Main supporting evidence</div>
          <p className="text-muted-foreground">{opp.mainSupportingEvidence}</p>
        </div>
        <div>
          <div className="font-medium text-foreground">Main missing evidence</div>
          <p className="text-muted-foreground">{opp.mainMissingEvidence}</p>
        </div>
      </div>

      <Button asChild className="mt-4 w-full">
        <Link to="/opportunities/$id" params={{ id: opp.id }}>
          Open Opportunity Detail
        </Link>
      </Button>
    </div>
  );
}

function MarketPanel({ market, onBack }: { market: MapMarket; onBack: () => void }) {
  return (
    <div>
      <button onClick={onBack} className="text-xs text-muted-foreground hover:text-foreground">← Back to clusters</button>
      <div className="mt-2 flex items-start justify-between gap-2">
        <h2 className="text-base font-semibold leading-tight">{market.country}</h2>
        <OriginBadgeTag origin={market.origin} />
      </div>
      <div className="mt-3">
        <Row label="Global momentum" value={market.signalStrength} />
        <Row label="Confidence" value={market.confidence} />
        <Row label="Evidence records" value={market.evidenceCount} />
        <Row label="Recommended action" value={<ActionBadge action={market.action} />} />
      </div>

      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Evidence traceability</h3>
      <ul className="mt-2 space-y-2">
        {market.evidence.map((e, i) => (
          <li key={i} className="rounded-lg border bg-surface p-3 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-foreground">{e.source}</span>
              <span
                className={cn(
                  "rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase",
                  e.direction === "supporting"
                    ? "border-action-test/30 text-action-test"
                    : e.direction === "counter"
                      ? "border-action-reject/30 text-action-reject"
                      : "border-border text-muted-foreground",
                )}
              >
                {e.direction}
              </span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-muted-foreground">
              <span>Date: <span className="text-foreground">{e.date}</span></span>
              <span>Strength: <span className="tabular-nums text-foreground">{e.strength}</span></span>
              <span>Product: <span className="text-foreground">{e.product}</span></span>
              <span>Brand: <span className="text-foreground">{e.brand}</span></span>
            </div>
            <div className="mt-1 text-muted-foreground">Feature: <span className="text-foreground">{e.feature}</span></div>
            <a
              href={e.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1.5 inline-block break-all text-brand hover:underline"
            >
              {e.url}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
