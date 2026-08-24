import { NextResponse } from "next/server";

import { BackendError, queryRag, requireUserId } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  let userId: string;
  try {
    userId = await requireUserId();
  } catch {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  let query: unknown;
  try {
    ({ query } = (await request.json()) as { query?: unknown });
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (typeof query !== "string" || !query.trim()) {
    return NextResponse.json(
      { error: "Query must be a non-empty string." },
      { status: 400 },
    );
  }

  try {
    // The RAG graph makes several sequential LLM calls; this routinely
    // exceeds a few seconds.
    const content = await queryRag(userId, query);
    return NextResponse.json({ content });
  } catch (error) {
    if (error instanceof BackendError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }
    console.error("Chat proxy failed:", error);
    return NextResponse.json(
      { error: "The assistant is unavailable right now. Try again shortly." },
      { status: 502 },
    );
  }
}
