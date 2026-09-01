"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Source {
  filename: string;
  page?: number | null;
  doc_id: string;
  snippet: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

// ---------------------------------------------------------------------------
// Graph node metadata for the stepper bar
// ---------------------------------------------------------------------------

const NODE_META: Record<string, { label: string; icon: string }> = {
  query_analysis: { label: "Analyzing", icon: "🔍" },
  retriever:      { label: "Retrieving", icon: "📚" },
  grade:          { label: "Grading",    icon: "✅" },
  rewrite:        { label: "Rewriting",  icon: "✏️" },
  generate:       { label: "Generating", icon: "⚡" },
  verify:         { label: "Verifying",  icon: "🛡️" },
  web_search:     { label: "Searching",  icon: "🌐" },
  general_llm:    { label: "Thinking",   icon: "💡" },
};

// Ordered pipeline — we'll highlight the active node and show completed ones
const PIPELINE_ORDER = [
  "query_analysis",
  "retriever",
  "grade",
  "generate",
  "verify",
];

// ---------------------------------------------------------------------------
// Stepper component
// ---------------------------------------------------------------------------

function GraphStepper({ visitedNodes, activeNode }: {
  visitedNodes: string[];
  activeNode: string | null;
}) {
  if (visitedNodes.length === 0) return null;

  // Build the ordered list: show pipeline nodes that were visited, plus any
  // non-pipeline nodes (web_search, general_llm, rewrite) in visit order.
  const pipelineVisited = PIPELINE_ORDER.filter((n) => visitedNodes.includes(n));
  const extras = visitedNodes.filter((n) => !PIPELINE_ORDER.includes(n));
  const displayed = [...new Set([...pipelineVisited, ...extras])];

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-1 py-2">
      {displayed.map((node, index) => {
        const meta = NODE_META[node] || { label: node, icon: "⚙️" };
        const isActive = node === activeNode;
        const isCompleted = !isActive && visitedNodes.includes(node);

        return (
          <span key={node} className="flex items-center gap-1">
            {index > 0 && (
              <span className="text-zinc-600 text-[10px] mx-0.5">›</span>
            )}
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium transition-all duration-300 ${
                isActive
                  ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40 animate-pulse"
                  : isCompleted
                    ? "bg-zinc-800 text-zinc-400"
                    : "bg-zinc-900 text-zinc-600"
              }`}
            >
              <span className="text-xs">{meta.icon}</span>
              {meta.label}
            </span>
          </span>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source pills component
// ---------------------------------------------------------------------------

function SourcePills({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-zinc-800 pt-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
        Sources
      </p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source, index) => (
          <div key={`${source.doc_id}-${source.page}-${index}`} className="relative">
            <button
              type="button"
              onClick={() => setExpanded(expanded === index ? null : index)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium transition-colors ${
                expanded === index
                  ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30"
                  : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-700/80 hover:text-zinc-300"
              }`}
            >
              <span className="text-xs">📄</span>
              <span className="max-w-[140px] truncate">{source.filename}</span>
              {source.page != null && (
                <span className="text-zinc-500">p.{source.page}</span>
              )}
            </button>

            {expanded === index && source.snippet && (
              <div className="absolute bottom-full left-0 z-10 mb-1.5 w-72 rounded-lg border border-zinc-700 bg-zinc-800 p-3 text-xs leading-relaxed text-zinc-300 shadow-xl">
                <p className="mb-1 text-[10px] font-semibold text-zinc-500">
                  {source.filename}
                  {source.page != null && ` · Page ${source.page}`}
                </p>
                <p className="text-zinc-400">{source.snippet}…</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main chat window
// ---------------------------------------------------------------------------

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [visitedNodes, setVisitedNodes] = useState<string[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeNode]);

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const query = input.trim();
    if (!query || pending) {
      return;
    }

    setInput("");
    setMessages((previous) => [
      ...previous,
      { role: "user", content: query },
      { role: "assistant", content: "" },
    ]);
    setPending(true);
    setVisitedNodes([]);
    setActiveNode(null);

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Streaming failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();

          if (!data) continue;

          try {
            const event = JSON.parse(data) as {
              content?: string;
              node?: string;
              sources?: Source[];
              code?: string;
              message?: string;
            };

            if (event.node) {
              // Graph node transition — update stepper
              setActiveNode(event.node);
              setVisitedNodes((prev) =>
                prev.includes(event.node!) ? prev : [...prev, event.node!],
              );
            } else if (event.sources) {
              // Source citations from retriever
              setMessages((previous) => {
                const next = [...previous];
                const lastIndex = next.length - 1;
                next[lastIndex] = {
                  ...next[lastIndex],
                  sources: event.sources,
                };
                return next;
              });
            } else if (event.content !== undefined) {
              // Append token to the last message
              setMessages((previous) => {
                const next = [...previous];
                const lastIndex = next.length - 1;
                next[lastIndex] = {
                  ...next[lastIndex],
                  content: next[lastIndex].content + event.content,
                };
                return next;
              });
            } else if (event.code && event.message) {
              // Error event
              setMessages((previous) => {
                const next = [...previous];
                next[next.length - 1] = {
                  role: "assistant",
                  content: `⚠️ ${event.code}: ${event.message}`,
                };
                return next;
              });
              break;
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }
    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((previous) => {
        const next = [...previous];
        next[next.length - 1] = {
          role: "assistant",
          content: "⚠️ Could not reach the assistant. Try again shortly.",
        };
        return next;
      });
    } finally {
      setPending(false);
      setActiveNode(null);
    }
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-zinc-950">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mx-auto mt-24 max-w-md text-center">
            <p className="text-sm font-medium text-zinc-300">
              Ask anything.
            </p>
            <p className="mt-2 text-xs leading-relaxed text-zinc-500">
              Questions matching your uploaded documents are answered from
              them; everything else falls back to model knowledge or live web
              search automatically.
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                message.role === "user"
                  ? "rounded-br-sm bg-emerald-600 text-white"
                  : "rounded-bl-sm border border-zinc-800 bg-zinc-900 text-zinc-100"
              }`}
            >
              {message.role === "assistant" && !message.content && pending ? (
                <span className="flex gap-1 py-1">
                  {[0, 1, 2].map((dot) => (
                    <span
                      key={dot}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500"
                      style={{ animationDelay: `${dot * 150}ms` }}
                    />
                  ))}
                </span>
              ) : message.role === "assistant" ? (
                <>
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => (
                        <p className="mb-2 last:mb-0">{children}</p>
                      ),
                      code: ({ children, className }) =>
                        className?.includes("language-") ? (
                          <code className="block overflow-x-auto rounded-lg bg-zinc-800 p-3 text-xs">
                            {children}
                          </code>
                        ) : (
                          <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs">
                            {children}
                          </code>
                        ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  {message.sources && message.sources.length > 0 && (
                    <SourcePills sources={message.sources} />
                  )}
                </>
              ) : (
                message.content
              )}
            </div>
          </div>
        ))}

        {/* Graph progression stepper — shown while streaming */}
        {pending && visitedNodes.length > 0 && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-zinc-800/60 bg-zinc-900/40 px-3 py-1">
              <GraphStepper
                visitedNodes={visitedNodes}
                activeNode={activeNode}
              />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={sendMessage} className="border-t border-zinc-800 p-4">
        <div className="flex items-end gap-3">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            rows={1}
            placeholder="Ask a question…"
            disabled={pending}
            className="max-h-40 min-h-11 flex-1 resize-none rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-emerald-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={pending || !input.trim()}
            className="h-11 rounded-xl bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
