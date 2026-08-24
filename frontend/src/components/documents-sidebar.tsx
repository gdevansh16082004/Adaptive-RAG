"use client";

import { FormEvent, useState } from "react";

import type { DocumentInfo } from "@/lib/backend";

export default function DocumentsSidebar({
  initialDocuments,
}: {
  initialDocuments: DocumentInfo[];
}) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(
    null,
  );

  async function refresh() {
    const response = await fetch("/api/documents");
    if (response.ok) {
      const data = (await response.json()) as { documents: DocumentInfo[] };
      setDocuments(data.documents);
    }
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !description.trim() || busy) {
      return;
    }

    setBusy(true);
    setNotice(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("description", description.trim());

      const response = await fetch("/api/documents", {
        method: "POST",
        body: formData,
      });
      const data = (await response.json()) as { error?: string };

      if (!response.ok) {
        setNotice({ kind: "error", text: data.error ?? "Upload failed." });
      } else {
        setNotice({ kind: "ok", text: `Uploaded ${file.name}.` });
        setFile(null);
        setDescription("");
        await refresh();
      }
    } catch {
      setNotice({ kind: "error", text: "Upload failed. Try again." });
    } finally {
      setBusy(false);
    }
  }

  async function remove(docId: string) {
    if (deletingId) {
      return;
    }
    setDeletingId(docId);
    setNotice(null);
    try {
      const response = await fetch(`/api/documents/${docId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const data = (await response.json()) as { error?: string };
        setNotice({ kind: "error", text: data.error ?? "Delete failed." });
      } else {
        await refresh();
      }
    } catch {
      setNotice({ kind: "error", text: "Delete failed. Try again." });
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900/60">
      <div className="border-b border-zinc-800 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Your documents</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Private to your account
        </p>
      </div>

      <form onSubmit={upload} className="space-y-3 border-b border-zinc-800 p-4">
        <label
          htmlFor="doc-file"
          className="block cursor-pointer rounded-lg border border-dashed border-zinc-700 px-3 py-4 text-center text-xs text-zinc-400 transition hover:border-emerald-600 hover:text-zinc-300"
        >
          {file ? (
            <span className="font-medium text-emerald-400">{file.name}</span>
          ) : (
            <>Click to choose a PDF or TXT</>
          )}
        </label>
        <input
          id="doc-file"
          type="file"
          accept=".pdf,.txt"
          className="sr-only"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />

        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={2}
          maxLength={300}
          placeholder="Describe this document, e.g. “Employee handbook with vacation policy”"
          className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-emerald-500"
        />

        <button
          type="submit"
          disabled={!file || !description.trim() || busy}
          className="w-full rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Uploading & indexing…" : "Upload document"}
        </button>

        {notice && (
          <p
            role="status"
            className={`rounded-lg px-3 py-2 text-xs ${
              notice.kind === "ok"
                ? "border border-emerald-900/60 bg-emerald-950/40 text-emerald-300"
                : "border border-red-900/60 bg-red-950/40 text-red-300"
            }`}
          >
            {notice.text}
          </p>
        )}
      </form>

      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {documents.length === 0 && (
          <p className="text-xs text-zinc-600">
            Nothing indexed yet — uploaded documents appear here and become
            searchable immediately.
          </p>
        )}

        {documents.map((document) => (
          <div
            key={document.doc_id}
            className="group flex items-start justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5"
          >
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-zinc-200">
                {document.filename}
              </p>
              <p className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-zinc-500">
                {document.description || "No description"}
              </p>
              <p className="mt-1 text-[10px] text-zinc-600">
                {document.num_chunks} chunks · {document.created_at.slice(0, 10)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => remove(document.doc_id)}
              disabled={deletingId === document.doc_id}
              title="Delete document"
              aria-label={`Delete ${document.filename}`}
              className="shrink-0 rounded-md px-1.5 py-1 text-xs text-zinc-500 transition hover:bg-red-950/60 hover:text-red-400 disabled:opacity-40"
            >
              {deletingId === document.doc_id ? "…" : "✕"}
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
