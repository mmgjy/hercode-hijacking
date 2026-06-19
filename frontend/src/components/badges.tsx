import { cn } from "@/lib/utils";
import type { ActionType, OriginBadge } from "@/lib/api/types";

const actionStyles: Record<ActionType, string> = {
  TEST: "bg-action-test/12 text-action-test border-action-test/30",
  CONTACT: "bg-action-contact/12 text-action-contact border-action-contact/30",
  RESEARCH: "bg-action-research/15 text-action-research border-action-research/35",
  MONITOR: "bg-action-monitor/12 text-action-monitor border-action-monitor/30",
  REJECT: "bg-action-reject/12 text-action-reject border-action-reject/30",
};

export function ActionBadge({ action, className }: { action: ActionType; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold tracking-wide",
        actionStyles[action],
        className,
      )}
    >
      {action}
    </span>
  );
}

const originStyles: Record<OriginBadge, string> = {
  LIVE: "bg-action-test/10 text-action-test border-action-test/30",
  DEMO: "bg-action-research/12 text-action-research border-action-research/30",
  REPLAY: "bg-muted text-muted-foreground border-border",
  CALCULATED: "bg-action-contact/10 text-action-contact border-action-contact/30",
  "MANUAL REVIEW": "bg-brand/10 text-brand border-brand/30",
};

export function OriginBadgeTag({ origin, className }: { origin: OriginBadge; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        originStyles[origin],
        className,
      )}
      title={`Data origin: ${origin}`}
    >
      {origin}
    </span>
  );
}
