"use client";

// Expert Copilot chat, built mobile-first for a technician on a phone. Comfortable
// bubbles, readable answers, sources grouped into graph evidence and document
// evidence, and a reasoning panel tucked behind a plain toggle. The input floats
// just above the bottom tab bar so the keyboard never hides it.

import Link from "next/link";
import { SendHorizontal, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { CopilotAnswer, CopilotCitation, askCopilot } from "@/lib/api";
import { Chip } from "@/components/ui";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: CopilotCitation[];
  debug?: Pick<CopilotAnswer, "resolved_equipment" | "context_used" | "usage">;
}

const STARTERS = [
  "What should I check on P-101?",
  "Why is P-101's bearing a concern?",
  "What does the whistling sound on P-101 mean?",
  "Which regulation covers hot work on T-205?",
];

export default function CopilotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text: string) => {
    const query = text.trim();
    if (!query || busy) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setBusy(true);
    try {
      const res = await askCopilot(query, history);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, citations: res.citations, debug: { resolved_equipment: res.resolved_equipment, context_used: res.context_used, usage: res.usage } }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Could not reach the copilot. ${String(e)}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-3.5rem)] max-w-2xl flex-col px-4">
      <div className="flex-1 space-y-4 py-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Copilot</h1>
          <p className="text-sm text-muted">Grounded in the plant knowledge graph and documents. Every answer is cited.</p>
        </div>

        {messages.length === 0 && (
          <div className="pt-2">
            <p className="mb-2 text-sm text-muted">Try asking</p>
            <div className="flex flex-wrap gap-2">
              {STARTERS.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="min-h-[44px] rounded-full border border-line bg-surface px-4 text-sm font-medium text-ink hover:border-primary"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && <div className="text-sm text-muted">Thinking...</div>}
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-[76px] z-30 -mx-4 border-t border-line bg-bg px-4 py-3 md:bottom-4 md:mx-0 md:rounded-xl md:border">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about equipment, maintenance, or safety"
            className="min-h-[48px] flex-1 rounded-full border border-line bg-surface px-4 text-base outline-none focus:border-primary"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-primary text-white hover:bg-primary-hover disabled:opacity-40"
          >
            <SendHorizontal size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-base text-white">{message.content}</div>
      </div>
    );
  }
  return (
    <div className="animate-in flex justify-start">
      <div className="max-w-[92%] space-y-3">
        <div className="rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3 text-base leading-relaxed">{message.content}</div>
        {message.citations && message.citations.length > 0 && <Sources citations={message.citations} />}
        {message.debug && <DebugPanel debug={message.debug} />}
      </div>
    </div>
  );
}

function Sources({ citations }: { citations: CopilotCitation[] }) {
  const graph = citations.filter((c) => c.type !== "document");
  const documents = citations.filter((c) => c.type === "document");
  return (
    <div className="space-y-2">
      {graph.length > 0 && <SourceGroup label="Graph evidence" citations={graph} />}
      {documents.length > 0 && <SourceGroup label="Document evidence" citations={documents} />}
    </div>
  );
}

function SourceGroup({ label, citations }: { label: string; citations: CopilotCitation[] }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className="flex flex-wrap gap-2">
        {citations.map((c, i) => (
          <CitationChip key={`${c.type}-${c.ref}-${i}`} c={c} />
        ))}
      </div>
    </div>
  );
}

function CitationChip({ c }: { c: CopilotCitation }) {
  const label = c.type === "guru" ? c.title ?? c.ref : c.type === "prediction" ? `Prediction ${c.ref}` : c.type === "document" ? c.title ?? c.ref : c.ref;
  const chip = (
    <span title={c.snippet ?? undefined} className="inline-flex min-h-[36px] items-center gap-1 rounded-full border border-line bg-surface px-3 text-xs font-medium text-ink">
      {c.type === "guru" && <User size={13} />}
      {label}
    </span>
  );
  return c.equipment_tag ? <Link href={`/equipment/${c.equipment_tag}`}>{chip}</Link> : chip;
}

function DebugPanel({ debug }: { debug: NonNullable<ChatMessage["debug"]> }) {
  const passages = debug.context_used.passages ?? [];
  return (
    <details className="rounded-lg border border-line bg-surface px-3 py-2 text-xs text-muted">
      <summary className="min-h-[36px] cursor-pointer content-center font-medium">How did I get this answer?</summary>
      <div className="mt-2 space-y-2">
        <div><span className="font-semibold">Detected equipment:</span> {debug.resolved_equipment ?? "none"}</div>
        <div><span className="font-semibold">Tokens:</span> {debug.usage.prompt_tokens ?? "?"} prompt + {debug.usage.completion_tokens ?? "?"} completion</div>
        {debug.context_used.graph_facts && (
          <div>
            <div className="font-semibold">Graph facts retrieved</div>
            <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-bg p-2">{debug.context_used.graph_facts}</pre>
          </div>
        )}
        <div>
          <div className="font-semibold">Vector chunks retrieved ({passages.length})</div>
          <ul className="mt-1 space-y-1">
            {passages.map((p) => (
              <li key={p.label} className="rounded bg-bg p-2">
                <span className="font-mono">{p.label}</span> · {p.source}
                {typeof p.score === "number" && <span> · score {p.score}</span>}
                <div>{p.snippet}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
