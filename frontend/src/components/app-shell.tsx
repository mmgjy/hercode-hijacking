import { Link, useRouterState } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { toast } from "sonner";
import { useMode } from "@/lib/mode";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/discover", label: "Discover" },
  { to: "/map", label: "Map" },
  { to: "/sources", label: "Sources" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { mode, setMode } = useMode();
  const queryClient = useQueryClient();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const resetDemo = async () => {
    await api.resetDemo(mode);
    await queryClient.invalidateQueries();
    toast.success("Demo state reset", { description: "Match reviews cleared." });
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-30 border-b bg-card/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-6 px-4">
          <Link to="/" className="flex items-center gap-2" aria-label="Hijacking home">
            <span className="h-2.5 w-2.5 rounded-full bg-brand" aria-hidden />
            <span className="text-base font-semibold tracking-tight">Hijacking</span>
            <span className="hidden text-xs text-muted-foreground sm:inline">Retail Opportunity Decision Engine</span>
          </Link>

          <nav className="ml-2 flex items-center gap-1" aria-label="Primary">
            {navItems.map((item) => {
              const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "rounded px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    active ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div
              className="flex items-center rounded-md border p-0.5 text-xs font-medium"
              role="group"
              aria-label="Data mode"
            >
              <button
                onClick={() => setMode("demo")}
                className={cn(
                  "rounded px-2.5 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  mode === "demo" ? "bg-action-research/15 text-action-research" : "text-muted-foreground",
                )}
                aria-pressed={mode === "demo"}
              >
                Demo
              </button>
              <button
                onClick={() => setMode("live")}
                className={cn(
                  "rounded px-2.5 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  mode === "live" ? "bg-action-test/15 text-action-test" : "text-muted-foreground",
                )}
                aria-pressed={mode === "live"}
              >
                Live
              </button>
            </div>
            <button
              onClick={resetDemo}
              className="rounded px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Reset demo
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">{children}</main>

      <footer className="border-t py-6">
        <div className="mx-auto w-full max-w-7xl px-4 text-xs text-muted-foreground">
          Hijacking searches only the configured sources and selected observation period. It does not claim to scan the
          entire market.
        </div>
      </footer>
    </div>
  );
}
