import { auth } from "@/auth";

/**
 * Server-side access to the FastAPI RAG backend.
 *
 * Every call originates here with the identity taken from the Next.js
 * session — the browser never talks to FastAPI directly and can never
 * spoof another user's X-User-ID.
 */

export const BACKEND_URL =
  process.env.BACKEND_URL || "http://127.0.0.1:8000";

export interface DocumentInfo {
  doc_id: string;
  user_id: string;
  filename: string;
  description: string;
  num_chunks: number;
  created_at: string;
}

export interface RagResult {
  type?: string;
  content?: string;
}

/** Thrown when the backend is unreachable or returns an error status. */
export class BackendError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "BackendError";
  }
}

/**
 * Require a session and return its username.
 *
 * Throws if called outside an authenticated request context.
 */
export async function requireUserId(): Promise<string> {
  const session = await auth();
  const id = session?.user?.id;
  if (!id) {
    throw new BackendError(401, "Not signed in.");
  }
  return id;
}

async function parseError(response: Response): Promise<never> {
  let detail = `${response.status} ${response.statusText}`;
  let code = "unknown_error";
  try {
    const body = (await response.json()) as {
      detail?: unknown;
      error?: { code?: string; message?: string };
    };
    // Structured envelope errors
    if (body.detail && typeof body.detail === "object") {
      const envelope = body.detail as { error?: { code?: string; message?: string } };
      if (envelope.error) {
        code = envelope.error.code ?? code;
        detail = envelope.error.message ?? detail;
      }
    } else if (typeof body.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // keep the status-line fallback
  }
  throw new BackendError(response.status, `${code}: ${detail}`);
}

export async function queryRag(
  userId: string,
  query: string,
): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/rag/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      session_id: userId,
      user_id: userId,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    await parseError(response);
  }

  const body = (await response.json()) as {
    data?: { result: RagResult };
    result?: RagResult;
  };
  // Support both envelope (data.result) and legacy (result) shapes
  const result = body.data?.result ?? body.result;
  return result?.content ?? "The assistant returned an empty response.";
}

export async function listDocuments(userId: string): Promise<DocumentInfo[]> {
  const response = await fetch(
    `${BACKEND_URL}/rag/documents`,
    {
      headers: { "X-User-ID": userId },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    await parseError(response);
  }

  const body = (await response.json()) as {
    data?: { documents: DocumentInfo[] };
    documents?: DocumentInfo[];
  };
  return body.data?.documents ?? body.documents ?? [];
}

export async function uploadDocument(
  userId: string,
  file: File,
  description: string,
): Promise<DocumentInfo> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  // Free text travels in the form body — header values can't contain
  // newlines or arbitrary unicode.
  formData.append("description", description);

  const response = await fetch(`${BACKEND_URL}/rag/documents/upload`, {
    method: "POST",
    headers: {
      "X-User-ID": userId,
    },
    body: formData,
  });

  if (!response.ok) {
    await parseError(response);
  }

  const body = (await response.json()) as {
    data?: { document: DocumentInfo };
    document?: DocumentInfo;
  };
  return body.data?.document ?? body.document!;
}

export async function deleteDocument(
  userId: string,
  docId: string,
): Promise<void> {
  const response = await fetch(
    `${BACKEND_URL}/rag/documents/${encodeURIComponent(docId)}`,
    {
      method: "DELETE",
      headers: { "X-User-ID": userId },
    },
  );

  if (!response.ok) {
    await parseError(response);
  }
}
