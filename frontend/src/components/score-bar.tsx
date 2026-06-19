import { OriginBadgeTag } from "./badges";
import type { OriginBadge } from "@/lib/api/types";

interface ScoreBarProps {
  label: string;
  value: number;
  origin?: OriginBadge;
  explanation?: string;
  calculatedAt?: string;
}

export function ScoreBar({ label, value, origin, explanation, calculatedAt }: ScoreBarProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="flex items-center gap-2">
          {origin && <OriginBadgeTag origin={origin} />}
          <span className="text-sm font-semibold tabular-nums text-foreground">{value}</span>
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${value} of 100`}
      >
        <div className="h-full rounded-full bg-foreground/80" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      {explanation && <p className="text-xs text-muted-foreground">{explanation}</p>}
      {calculatedAt && (
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Calculated {new Date(calculatedAt).toLocaleString()}
        </p>
      )}
    </div>
  );
}
