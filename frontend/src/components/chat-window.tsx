"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = (await response.json()) as {
        content?: string;
        error?: string;
      };
      const reply =
        data.content ??
        data.error ??
        "The assistant returned an empty response.";

      setMessages((previous) => {
        const next = [...previous];
        next[next.length - 1] = {
          role: "assistant",
          content:
            data.content !== undefined
              ? reply
              : `⚠️ ${reply}`,
        };
        return next;
      });
    } catch {
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
              ) : (
                message.content
              )}
            </div>
          </div>
        ))}
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
