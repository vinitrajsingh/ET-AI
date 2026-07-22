"use client";

// Equipment 360: one asset's whole life on a single screen. Header identity and
// health, then prediction, compliance, tribal knowledge, timeline, documents, and
// people. Everything is wired to the real API. A prediction can be turned into a
// work-order draft that, once approved, appears highlighted in the timeline.

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ApiError,
  ComplianceFinding,
  DocumentLink,
  Equipment360,
  GuruNote,
  HealthSnapshot,
  PersonWork,
  PredictionResult,
  TimelineItem,
  WorkOrderDraft,
  approveWorkOrderDraft,
  createWorkOrderDraft,
  fetchEquipment360,
  fetchEquipmentCompliance,
  fetchEquipmentPrediction,
  fetchGuruNotes,
  formatDate,
} from "@/lib/api";
import { complianceStatus, riskStatus } from "@/lib/status";
import { Button, Card, Chip, EmptyState, ErrorNotice, Modal, Section, Skeleton, StatusPill, Tag } from "@/components/ui";

export default function Equipment360Page() {
  const params = useParams<{ tag: string }>();
  const tag = decodeURIComponent(params.tag);

  const [data, setData] = useState<Equipment360 | null>(null);
  const [predictions, setPredictions] = useState<PredictionResult[] | null>(null);
  const [guruNotes, setGuruNotes] = useState<GuruNote[]>([]);
  const [compliance, setCompliance] = useState<ComplianceFinding[]>([]);
  const [error, setError] = useState<{ notFound: boolean; message: string } | null>(null);
  const [highlightWo, setHighlightWo] = useState<string | null>(null);

  const reload360 = (highlight?: string) => {
    fetchEquipment360(tag)
      .then((d) => {
        setData(d);
        if (highlight) setHighlightWo(highlight);
      })
      .catch(() => {});
  };

  useEffect(() => {
    setData(null);
    setPredictions(null);
    setGuruNotes([]);
    setCompliance([]);
    setError(null);
    setHighlightWo(null);
    fetchEquipment360(tag)
      .then(setData)
      .catch((e) => setError({ notFound: e instanceof ApiError && e.status === 404, message: String(e) }));
    fetchEquipmentPrediction(tag).then(setPredictions).catch(() => setPredictions([]));
    fetchGuruNotes(tag).then(setGuruNotes).catch(() => setGuruNotes([]));
    fetchEquipmentCompliance(tag).then(setCompliance).catch(() => setCompliance([]));
  }, [tag]);

  return (
    <div className="px-4 py-4 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <Link href="/equipment" className="inline-flex min-h-[44px] items-center gap-1 text-sm font-medium text-muted hover:text-ink">
          <ChevronLeft size={18} /> All equipment
        </Link>

        {error?.notFound && <div className="mt-4"><ErrorNotice title={`No equipment "${tag}"`} detail="This tag does not exist in the graph." /></div>}
        {error && !error.notFound && <div className="mt-4"><ErrorNotice title="Could not load this equipment" detail={error.message} /></div>}
        {!data && !error && <LoadingBody />}

        {data && (
          <div className="mt-3 space-y-8">
            <Header summary={data.summary} health={data.health} />
            <Prediction predictions={predictions} onWorkOrderCreated={(wo) => reload360(wo)} />
            <Compliance findings={compliance} />
            <TribalKnowledge notes={guruNotes} />
            <Timeline items={data.timeline} highlightWo={highlightWo} />
            <Documents documents={data.documents} />
            <People people={data.people} />
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingBody() {
  return (
    <div className="mt-4 space-y-4">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-32 w-full" />
    </div>
  );
}

function Header({ summary, health }: { summary: Equipment360["summary"]; health: HealthSnapshot }) {
  return (
    <section>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Tag className="text-3xl font-bold">{summary.tag}</Tag>
        <span className="text-lg text-muted">{summary.name}</span>
        {summary.type && <Chip>{summary.type}</Chip>}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatChip label="Work orders" value={health.total_work_orders} />
        <StatChip label="Open" value={health.open_work_orders} tone={health.open_work_orders > 0 ? "caution" : "plain"} />
        <StatChip label="Incidents" value={health.incident_count} tone={health.incident_count > 0 ? "critical" : "plain"} />
        <StatChip label="Last activity" value={formatDate(health.last_work_order_date)} />
      </div>
      <p className="mt-2 text-sm text-muted">
        {health.corrective_count} corrective, {health.preventive_count} preventive
      </p>
    </section>
  );
}

const STAT_TONE = {
  plain: "bg-surface border-line text-ink",
  caution: "bg-caution-soft border-caution/25 text-caution",
  critical: "bg-critical-soft border-critical/25 text-critical",
} as const;

function StatChip({ label, value, tone = "plain" }: { label: string; value: string | number; tone?: keyof typeof STAT_TONE }) {
  return (
    <div className={`rounded-lg border p-3 ${STAT_TONE[tone]}`}>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
    </div>
  );
}

// --- Prediction ---

function Prediction({ predictions, onWorkOrderCreated }: { predictions: PredictionResult[] | null; onWorkOrderCreated: (wo: string) => void }) {
  if (predictions === null) return <Skeleton className="h-28 w-full" />;
  const predicted = predictions.filter((p) => p.status === "predicted");
  if (predicted.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface px-4 py-3 text-sm text-muted">
        No recurring failure pattern detected yet.
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {predicted.map((p) => (
        <PredictionCard key={p.failure_type} p={p} onWorkOrderCreated={onWorkOrderCreated} />
      ))}
    </div>
  );
}

function PredictionCard({ p, onWorkOrderCreated }: { p: PredictionResult; onWorkOrderCreated: (wo: string) => void }) {
  const risk = riskStatus(p.risk_level);
  const [draft, setDraft] = useState<WorkOrderDraft | null>(null);
  const [showDraft, setShowDraft] = useState(false);
  const [busy, setBusy] = useState(false);
  const [createdWo, setCreatedWo] = useState<string | null>(null);

  const makeDraft = async () => {
    setBusy(true);
    try {
      setDraft(await createWorkOrderDraft(p.equipment_tag, p.failure_type));
      setShowDraft(true);
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!draft) return;
    setBusy(true);
    try {
      const approved = await approveWorkOrderDraft(draft.draft_id);
      setCreatedWo(approved.approved_wo_id);
      setShowDraft(false);
      if (approved.approved_wo_id) onWorkOrderCreated(approved.approved_wo_id);
    } finally {
      setBusy(false);
    }
  };

  const accent = risk.token === "critical" ? "border-critical" : risk.token === "caution" ? "border-caution" : "border-good";

  return (
    <Card className={`overflow-hidden border-l-4 ${accent}`}>
      <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Prediction: {p.failure_label}</h2>
        <div className="flex items-center gap-2">
          {typeof p.confidence === "number" && <Chip>{p.confidence}% confidence</Chip>}
          <StatusPill token={risk.token} label={risk.label} />
        </div>
      </div>

      <div className="p-4">
        <p className="text-lg font-semibold">
          Next {p.failure_label.toLowerCase()} expected around {formatDate(p.predicted_center)}
          {typeof p.days_until_center === "number" && <span className="text-muted"> ({p.days_until_center} days)</span>}
        </p>
        <p className="mt-2 rounded-lg bg-bg p-3 text-sm leading-relaxed text-ink">{p.explanation}</p>

        <details className="mt-3 rounded-lg bg-bg p-3">
          <summary className="cursor-pointer text-sm font-medium">Evidence: {p.evidence.length} work orders</summary>
          <ul className="mt-2 space-y-2">
            {p.evidence.map((e) => (
              <li key={e.wo_id} className="border-l-2 border-line pl-3 text-sm">
                <Tag className="text-xs text-muted">{e.wo_id}</Tag> <span className="text-xs text-muted">{formatDate(e.date)}</span>
                <p className="text-ink">{e.description}</p>
              </li>
            ))}
          </ul>
        </details>

        <div className="mt-4 border-t border-line pt-3">
          {createdWo ? (
            <p className="text-sm font-medium text-good">Work order <Tag>{createdWo}</Tag> created and added to the timeline below.</p>
          ) : (
            <Button variant="secondary" onClick={makeDraft} disabled={busy}>
              {busy ? "Drafting..." : "Create work order draft"}
            </Button>
          )}
        </div>
      </div>

      {showDraft && draft && (
        <Modal title="Draft work order" onClose={() => setShowDraft(false)}>
          <dl className="space-y-2 text-sm">
            <Row label="Equipment"><Tag>{draft.equipment_tag}</Tag></Row>
            <Row label="Task">{draft.task}</Row>
            <Row label="Priority">{draft.priority}</Row>
            <Row label="Trade">{draft.trade ?? "-"}</Row>
            <Row label="Target date">{formatDate(draft.target_date)}</Row>
            {draft.parts_suggested && <Row label="Parts">{draft.parts_suggested}</Row>}
            <Row label="Justification">Predicted from {draft.justification.evidence_work_orders?.join(", ")}</Row>
          </dl>
          <div className="mt-5 flex gap-3">
            <Button onClick={approve} disabled={busy}>{busy ? "Approving..." : "Approve and create"}</Button>
            <Button variant="secondary" onClick={() => setShowDraft(false)}>Cancel</Button>
          </div>
        </Modal>
      )}
    </Card>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="w-28 shrink-0 font-medium text-muted">{label}</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}

// --- Compliance ---

const CATEGORY_TONE: Record<string, string> = {
  Health: "text-info bg-info-soft",
  Safety: "text-caution bg-caution-soft",
  Environment: "text-good bg-good-soft",
};

function Compliance({ findings }: { findings: ComplianceFinding[] }) {
  if (findings.length === 0) return null;
  return (
    <Section title="Compliance" count={findings.length}>
      <div className="space-y-3">
        {findings.map((f) => {
          const s = complianceStatus(f.status);
          return (
            <Card key={f.rule_code} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill token={s.token} label={s.label} />
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_TONE[f.category]}`}>{f.category}</span>
                <h3 className="text-sm font-semibold">{f.title}</h3>
              </div>
              <p className="mt-2 text-sm text-ink">{f.requires}</p>
              <p className="mt-2 text-xs text-muted">
                Regulation: {f.regulation}
                {f.evidence_ref ? <> · Evidence: <Tag>{f.evidence_ref}</Tag>{f.evidence_date ? ` (${formatDate(f.evidence_date)})` : ""}</> : null}
                {f.due_date ? ` · next due ${formatDate(f.due_date)}` : ""}
              </p>
              {f.gap && <p className="mt-1 text-xs font-medium text-critical">{f.gap}</p>}
            </Card>
          );
        })}
      </div>
    </Section>
  );
}

// --- Tribal knowledge ---

function TribalKnowledge({ notes }: { notes: GuruNote[] }) {
  if (notes.length === 0) return null;
  return (
    <Section title="Tribal knowledge" count={notes.length}>
      <div className="space-y-3">
        {notes.map((n) => (
          <Card key={n.note_id} className="border-l-4 border-primary p-4">
            <div className="text-sm font-semibold">{n.engineer_name}</div>
            <p className="mt-1 text-sm text-ink">{n.summary || n.symptom}</p>
            {n.recommended_action && <p className="mt-1 text-xs text-muted">Action: {n.recommended_action}</p>}
          </Card>
        ))}
      </div>
    </Section>
  );
}

// --- Timeline ---

function accentFor(item: TimelineItem): string {
  if (item.kind === "incident") return "border-critical bg-critical-soft";
  switch (item.extra.wo_type) {
    case "Corrective":
      return "border-caution";
    case "Preventive":
      return "border-good";
    case "Inspection":
      return "border-info";
    default:
      return "border-line";
  }
}

function Timeline({ items, highlightWo }: { items: TimelineItem[]; highlightWo: string | null }) {
  return (
    <Section title="Timeline" count={items.length}>
      {items.length === 0 ? (
        <EmptyState title="No work orders or incidents yet." />
      ) : (
        <ol className="space-y-3">
          {items.map((item) => (
            <li
              key={`${item.kind}-${item.id}`}
              className={`rounded-r-lg border-l-4 bg-surface px-4 py-3 shadow-[0_1px_2px_rgba(15,27,45,0.04)] ${accentFor(item)} ${item.id === highlightWo ? "animate-highlight" : ""}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted">{formatDate(item.date)}</span>
                {item.kind === "incident" ? (
                  <StatusPill token="critical" label="Near-miss" />
                ) : (
                  <Chip>{item.extra.wo_type ?? "Work order"}</Chip>
                )}
                {item.status && item.status !== "Closed" && <StatusPill token="caution" label={item.status} />}
                <Tag className="text-xs text-muted">{item.id}</Tag>
              </div>
              <p className="mt-1 text-sm text-ink">{item.description}</p>
              {item.kind === "workorder" && (item.extra.technician || item.extra.parts_used) && (
                <p className="mt-1 text-xs text-muted">
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

// --- Documents ---

const DOC_ORDER = ["Manual", "Governing regulation", "Referenced in"];

function Documents({ documents }: { documents: DocumentLink[] }) {
  const groups = new Map<string, DocumentLink[]>();
  for (const d of documents) {
    const list = groups.get(d.label) ?? [];
    list.push(d);
    groups.set(d.label, list);
  }
  const labels = [...groups.keys()].sort((a, b) => (DOC_ORDER.indexOf(a) + 9) - (DOC_ORDER.indexOf(b) + 9));

  return (
    <Section title="Documents" count={documents.length}>
      {documents.length === 0 ? (
        <EmptyState title="No linked documents." />
      ) : (
        <div className="space-y-4">
          {labels.map((label) => (
            <div key={label}>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{label}</h3>
              <ul className="space-y-1">
                {groups.get(label)!.map((d) => (
                  <li key={`${d.relationship}-${d.doc_id}`} className="rounded-lg border border-line bg-surface px-3 py-2 text-sm">
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

// --- People ---

function People({ people }: { people: PersonWork[] }) {
  if (people.length === 0) return null;
  return (
    <Section title="People" count={people.length}>
      <ul className="flex flex-wrap gap-2">
        {people.map((p) => (
          <Chip key={p.name}>
            {p.name} <span className="text-line">·</span> {p.jobs} job{p.jobs === 1 ? "" : "s"}
          </Chip>
        ))}
      </ul>
    </Section>
  );
}
