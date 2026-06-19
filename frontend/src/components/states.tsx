import { type ReactNode } from "react";

export function StateBox({
  title,
  description,
  tone = "neutral",
  children,
}: {
  title: string;
  description?: string;
  tone?: "neutral" | "error" | "info";
  children?: ReactNode;
}) {
  const toneClass =
    tone === "error"
      ? "border-action-reject/40 bg-action-reject/5"
      : tone === "info"
        ? "border-action-contact/30 bg-action-contact/5"
        : "border-border bg-surface";
  return (
    <div className={`rounded-lg border p-8 text-center ${toneClass}`} role="status" aria-live="polite">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
      {children && <div className="mt-4 flex justify-center">{children}</div>}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-muted-foreground" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground" aria-hidden />
      {label}
    </div>
  );
}
