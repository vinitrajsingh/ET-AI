"use client";

// Equipment 360: one asset's whole life on a single screen. Header stats, a
// merged work-order + incident timeline (colour-coded, incidents flagged),
// documents grouped by how they relate to the asset, and the people who worked
// on it. Everything is wired to the real API; nothing is hardcoded.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ApiError,
  DocumentLink,
  Equipment360,
  HealthSnapshot,
  PersonWork,
  TimelineItem,
  fetchEquipment360,
  formatDate,
} from "@/lib/api";

export default function Equipment360Page() {
  const params = useParams<{ tag: string }>();
  const tag = decodeURIComponent(params.tag);

  const [data, setData] = useState<Equipment360 | null>(null);
  const [error, setError] = useState<{ notFound: boolean; message: string } | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    fetchEquipment360(tag)
      .then(setData)
      .catch((e) =>
        setError({ notFound: e instanceof ApiError && e.status === 404, message: String(e) })
      );
  }, [tag]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-8">
      <div className="mx-auto max-w-4xl">
        <Link href="/equipment" className="text-sm text-slate-500 hover:text-slate-800">
          ← All equipment
        </Link>

        {error?.notFound && <Notice title={`No equipment "${tag}"`} body="This tag does not exist in the graph." />}
        {error && !error.notFound && (
          <Notice title="Could not load this equipment" body={error.message} tone="error" />
        )}
        {!data && !error && <p className="mt-6 text-slate-500">Loading {tag}...</p>}

        {data && (
          <div className="mt-4 space-y-8">
            <Header summary={data.summary} health={data.health} />
            <Timeline items={data.timeline} />
            <Documents documents={data.documents} />
            <People people={data.people} />
          </div>
        )}
      </div>
    </main>
  );
}

function Header({ summary, health }: { summary: Equipment360["summary"]; health: HealthSnapshot }) {
  return (
    <section>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="font-mono text-3xl font-bold">{summary.tag}</h1>
        <span className="text-lg text-slate-700">{summary.name}</span>
        {summary.type && (
          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600">{summary.type}</span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Chip label="Work orders" value={health.total_work_orders} />
        <Chip label="Open" value={health.open_work_orders} tone={health.open_work_orders > 0 ? "amber" : "plain"} />
        <Chip label="Incidents" value={health.incident_count} tone={health.incident_count > 0 ? "red" : "plain"} />
        <Chip label="Last activity" value={formatDate(health.last_work_order_date)} />
      </div>
      <div className="mt-2 text-xs text-slate-500">
        {health.corrective_count} corrective · {health.preventive_count} preventive
      </div>
    </section>
  );
}

const CHIP_TONES = {
  plain: "bg-white border-slate-200 text-slate-900",
  amber: "bg-amber-50 border-amber-200 text-amber-800",
  red: "bg-red-50 border-red-200 text-red-800",
} as const;

function Chip({ label, value, tone = "plain" }: { label: string; value: string | number; tone?: keyof typeof CHIP_TONES }) {
  return (
    <div className={`rounded-lg border p-3 ${CHIP_TONES[tone]}`}>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}

// Left-border colour tells the kind of event apart at a glance.
function accentFor(item: TimelineItem): string {
  if (item.kind === "incident") return "border-red-500 bg-red-50";
  switch (item.extra.wo_type) {
    case "Corrective":
      return "border-orange-400";
    case "Preventive":
      return "border-emerald-400";
    case "Inspection":
      return "border-sky-400";
    default:
      return "border-slate-300";
  }
}

function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <Section title="Timeline" count={items.length}>
      {items.length === 0 ? (
        <Empty text="No work orders or incidents yet." />
      ) : (
        <ol className="space-y-3">
          {items.map((item) => (
            <li
              key={`${item.kind}-${item.id}`}
              className={`rounded-r-lg border-l-4 bg-white px-4 py-3 shadow-sm ${accentFor(item)}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500">{formatDate(item.date)}</span>
                {item.kind === "incident" ? (
                  <span className="rounded bg-red-600 px-1.5 py-0.5 text-xs font-semibold text-white">
                    ⚠ NEAR-MISS
                  </span>
                ) : (
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                    {item.extra.wo_type ?? "Work order"}
                  </span>
                )}
                {item.status && item.status !== "Closed" && (
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800">
                    {item.status}
                  </span>
                )}
                <span className="font-mono text-xs text-slate-400">{item.id}</span>
              </div>
              <p className="mt-1 text-sm text-slate-800">{item.description}</p>
              {item.kind === "workorder" && (item.extra.technician || item.extra.parts_used) && (
                <p className="mt-1 text-xs text-slate-500">
                  {item.extra.technician && <>Technician: {item.extra.technician}. </>}
                  {item.extra.parts_used && <>Parts: {item.extra.parts_used}.</>}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </Section>
  );
}

const DOC_GROUP_ORDER = ["Manual", "Governing regulation", "Referenced in"];

function Documents({ documents }: { documents: DocumentLink[] }) {
  // Group by the friendly label the backend already assigned.
  const groups = new Map<string, DocumentLink[]>();
  for (const d of documents) {
    const list = groups.get(d.label) ?? [];
    list.push(d);
    groups.set(d.label, list);
  }
  const orderedLabels = [...groups.keys()].sort(
    (a, b) => (DOC_GROUP_ORDER.indexOf(a) + 99) - (DOC_GROUP_ORDER.indexOf(b) + 99)
  );

  return (
    <Section title="Documents" count={documents.length}>
      {documents.length === 0 ? (
        <Empty text="No linked documents." />
      ) : (
        <div className="space-y-4">
          {orderedLabels.map((label) => (
            <div key={label}>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</h3>
              <ul className="space-y-1">
                {groups.get(label)!.map((d) => (
                  <li key={`${d.relationship}-${d.doc_id}`} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
                    {d.title ?? d.doc_id}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function People({ people }: { people: PersonWork[] }) {
  return (
    <Section title="People" count={people.length}>
      {people.length === 0 ? (
        <Empty text="No recorded technicians." />
      ) : (
        <ul className="flex flex-wrap gap-2">
          {people.map((p) => (
            <li key={p.name} className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm">
              {p.name} <span className="text-slate-400">· {p.jobs} job{p.jobs === 1 ? "" : "s"}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function Section({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title} <span className="text-slate-300">({count})</span>
      </h2>
      {children}
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-400">{text}</p>;
}

function Notice({ title, body, tone = "plain" }: { title: string; body: string; tone?: "plain" | "error" }) {
  const style = tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-slate-200 bg-white text-slate-700";
  return (
    <div className={`mt-6 rounded-lg border p-4 ${style}`}>
      <div className="font-medium">{title}</div>
      <div className="mt-1 text-sm text-slate-500">{body}</div>
    </div>
  );
}
