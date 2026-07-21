"use client";

// Expert Copilot chat. Built mobile-first because the real user is a technician
// on a phone in the field. Every assistant answer shows its sources, and any
// source tied to an asset links straight into that asset's Equipment 360 page.

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CopilotAnswer, CopilotCitation, askCopilot } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: CopilotCitation[];
  debug?: Pick<CopilotAnswer, "resolved_equipment" | "context_used" | "usage">;
}

const STARTERS = [
  "What should I check on P-101?",
  "Why is P-101's bearing a concern?",
  "What happened at T-205?",
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
      const res: CopilotAnswer = await askCopilot(query, history);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          debug: { resolved_equipment: res.resolved_equipment, context_used: res.context_used, usage: res.usage },
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Could not reach the copilot. ${String(e)}` },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col bg-slate-50 text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">SANJEEVANI Copilot</h1>
          <p className="text-xs text-slate-500">Grounded in the plant knowledge graph and documents</p>
        </div>
        <Link href="/equipment" className="text-sm text-slate-500 hover:text-slate-800">
          Equipment →
        </Link>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
        {messages.length === 0 && <Starters onPick={send} />}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && <div className="text-sm text-slate-400">Thinking...</div>}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-slate-200 bg-white p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about equipment, maintenance, or safety..."
          className="flex-1 rounded-full border border-slate-300 px-4 py-2 text-sm outline-none focus:border-slate-500"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-full bg-slate-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </main>
  );
}

function Starters({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mt-6">
      <p className="mb-3 text-sm text-slate-500">Try asking:</p>
      <div className="flex flex-wrap gap-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-slate-900 px-4 py-2 text-sm text-white">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-3">
        <div className="rounded-2xl bg-white px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm">
          {message.content}
        </div>
        {message.citations && message.citations.length > 0 && <Sources citations={message.citations} />}
        {message.debug && <DebugPanel debug={message.debug} />}
      </div>
    </div>
  );
}

const CITATION_STYLES: Record<string, string> = {
  workorder: "border-slate-300 text-slate-700",
  incident: "border-red-300 bg-red-50 text-red-700",
  prediction: "border-orange-300 bg-orange-50 text-orange-700",
  document: "border-sky-300 bg-sky-50 text-sky-700",
  guru: "border-violet-300 bg-violet-50 text-violet-700",
};

// Split citations into the two halves of hybrid GraphRAG so the mix is obvious:
// structured facts from the graph vs passages from documents.
function Sources({ citations }: { citations: CopilotCitation[] }) {
  const graph = citations.filter((c) => c.type !== "document");
  const documents = citations.filter((c) => c.type === "document");

  return (
    <div className="space-y-2">
      {graph.length > 0 && <SourceGroup label="📊 Graph evidence" citations={graph} />}
      {documents.length > 0 && <SourceGroup label="📄 Document evidence" citations={documents} />}
    </div>
  );
}

function SourceGroup({ label, citations }: { label: string; citations: CopilotCitation[] }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="flex flex-wrap gap-2">
        {citations.map((c, i) => (
          <CitationChip key={`${c.type}-${c.ref}-${i}`} c={c} />
        ))}
      </div>
    </div>
  );
}

function DebugPanel({ debug }: { debug: NonNullable<ChatMessage["debug"]> }) {
  const passages = debug.context_used.passages ?? [];
  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
      <summary className="cursor-pointer font-medium text-slate-500">How did I arrive at this?</summary>
      <div className="mt-2 space-y-2">
        <div>
          <span className="font-semibold">Detected equipment:</span> {debug.resolved_equipment ?? "none"}
        </div>
        <div>
          <span className="font-semibold">Tokens:</span> {debug.usage.prompt_tokens ?? "?"} prompt +{" "}
          {debug.usage.completion_tokens ?? "?"} completion = {debug.usage.total_tokens ?? "?"}
        </div>
        {debug.context_used.graph_facts && (
          <div>
            <div className="font-semibold">Graph facts retrieved:</div>
            <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-2">
              {debug.context_used.graph_facts}
            </pre>
          </div>
        )}
        <div>
          <div className="font-semibold">Vector chunks retrieved ({passages.length}):</div>
          <ul className="mt-1 space-y-1">
            {passages.map((p) => (
              <li key={p.label} className="rounded bg-white p-2">
                <span className="font-mono">{p.label}</span> · {p.source}
                {typeof p.score === "number" && <span className="text-slate-400"> · score {p.score}</span>}
                <div className="text-slate-500">{p.snippet}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}

function CitationChip({ c }: { c: CopilotCitation }) {
  const label =
    c.type === "guru"
      ? `👤 ${c.title ?? c.ref}`
      : c.type === "prediction"
        ? `Prediction · ${c.ref}`
        : c.type === "document"
          ? c.title ?? c.ref
          : c.ref;
  const style = CITATION_STYLES[c.type] ?? CITATION_STYLES.workorder;
  const chip = (
    <span
      title={c.snippet ?? undefined}
      className={`inline-block rounded-full border bg-white px-2.5 py-1 text-xs font-medium ${style}`}
    >
      {label}
    </span>
  );

  // Anything tied to an asset jumps into its Equipment 360 page.
  return c.equipment_tag ? <Link href={`/equipment/${c.equipment_tag}`}>{chip}</Link> : chip;
}
