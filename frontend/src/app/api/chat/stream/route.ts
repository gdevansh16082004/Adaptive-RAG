import { requireUserId, BACKEND_URL } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  let userId: string;
  try {
    userId = await requireUserId();
  } catch {
    return new Response("Not signed in.", { status: 401 });
  }

  let query: unknown;
  try {
    ({ query } = (await request.json()) as { query?: unknown });
  } catch {
    return new Response("Invalid JSON body.", { status: 400 });
  }

  if (typeof query !== "string" || !query.trim()) {
    return new Response("Query must be a non-empty string.", { status: 400 });
  }

  try {
    // Proxy SSE from FastAPI to the client
    const response = await fetch(`${BACKEND_URL}/rag/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        session_id: userId,
        user_id: userId,
      }),
    });

    if (!response.ok) {
      return new Response(await response.text(), { status: response.status });
    }

    // Forward the SSE stream directly
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Stream proxy failed:", error);
    return new Response("Could not connect to the backend.", { status: 502 });
  }
}
