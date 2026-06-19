import { createFileRoute } from "@tanstack/react-router";
import { demoMapData } from "@/lib/demo/fixtures";

// GET /api/opportunity-map
// Returns the geographic opportunity intelligence payload:
// { opportunities, markets, connections, summary }.
// All scoring originates server-side; the frontend never recomputes it.
export const Route = createFileRoute("/api/opportunity-map")({
  server: {
    handlers: {
      GET: async () => Response.json(demoMapData),
    },
  },
});
