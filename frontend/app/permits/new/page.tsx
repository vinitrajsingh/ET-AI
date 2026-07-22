"use client";

// Raise a permit: the safety climax. When an asset and permit type are chosen,
// the system checks the graph and surfaces interventions before the permit can be
// activated. Critical warnings are loud and readable, the acknowledgment
// checkboxes are large, and the submit button explains plainly why it is disabled
// until every critical item is acknowledged.

import { useEffect, useState } from "react";
import { Check } from "lucide-react";

import {
  EquipmentListItem,
  InterventionItem,
  InterventionResult,
  PERMIT_TYPES,
  createPermit,
  evaluatePermit,
  fetchEquipmentList,
} from "@/lib/api";
import { severityStatus } from "@/lib/status";
import { Button, Card, Modal, Skeleton, StatusPill, Tag } from "@/components/ui";

export default function NewPermitPage() {
  const [assets, setAssets] = useState<EquipmentListItem[]>([]);
  const [tag, setTag] = useState("");
  const [permitType, setPermitType] = useState("");
  const [description, setDescription] = useState("");
  const [createdBy, setCreatedBy] = useState("HSE Supervisor");

  const [result, setResult] = useState<InterventionResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());
  const [confirmation, setConfirmation] = useState<{ id: string; count: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquipmentList().then(setAssets).catch(() => setAssets([]));
  }, []);

  useEffect(() => {
    setResult(null);
    setAcknowledged(new Set());
    setError(null);
    if (!tag || !permitType) return;
    setChecking(true);
    evaluatePermit({ permit_type: permitType, equipment_tag: tag, description })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setChecking(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tag, permitType]);

  const toggleAck = (id: string) =>
    setAcknowledged((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const blockingUnmet =
    result?.items.some((i) => i.severity === "critical" && i.requires_acknowledgment && !acknowledged.has(i.id)) ?? false;

  const submit = async () => {
    if (!result || blockingUnmet) return;
    setError(null);
    try {
      const permit = await createPermit({ permit_type: permitType, equipment_tag: tag, description, created_by: createdBy, acknowledged: [...acknowledged] });
      setConfirmation({ id: permit.permit_id, count: acknowledged.size });
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold tracking-tight">Raise a permit</h1>
        <p className="mt-1 text-muted">Safety checks run against the knowledge graph before the permit is activated.</p>

        <Card className="mt-5 space-y-4 p-5">
          <Field label="Equipment">
            <select value={tag} onChange={(e) => setTag(e.target.value)} className={selectCls}>
              <option value="">Select an asset</option>
              {assets.map((a) => (
                <option key={a.tag} value={a.tag}>{a.tag} — {a.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Permit type">
            <select value={permitType} onChange={(e) => setPermitType(e.target.value)} className={selectCls}>
              <option value="">Select a permit type</option>
              {PERMIT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="What work is being done?" className={`${selectCls} resize-none`} />
          </Field>
          <Field label="Raised by">
            <input value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} className={selectCls} />
          </Field>
        </Card>

        {checking && <div className="mt-6 space-y-3"><Skeleton className="h-6 w-64" /><Skeleton className="h-24 w-full" /></div>}
        {error && <p className="mt-4 rounded-lg bg-critical-soft p-3 text-sm text-critical">{error}</p>}

        {result && (
          <div className="mt-6">
            {result.items.length === 0 ? (
              <Card className="border-good/30 bg-good-soft p-4 text-sm font-medium text-good">
                No safety interventions found. This permit can proceed.
              </Card>
            ) : (
              <>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
                  Safety intervention: {result.items.length} finding{result.items.length === 1 ? "" : "s"}
                </h2>
                <div className="space-y-3">
                  {result.items.map((item) => (
                    <InterventionCard key={item.id} item={item} checked={acknowledged.has(item.id)} onToggle={() => toggleAck(item.id)} />
                  ))}
                </div>
              </>
            )}

            {blockingUnmet && (
              <p className="mt-4 flex items-center gap-2 text-sm font-medium text-critical">
                Acknowledge every critical item before this permit can be activated.
              </p>
            )}
            <div className="mt-4">
              <Button size="lg" onClick={submit} disabled={blockingUnmet} className="w-full">
                {result.items.length === 0 ? "Activate permit" : "Acknowledge and activate permit"}
              </Button>
            </div>
          </div>
        )}
      </div>

      {confirmation && (
        <Modal title={`Permit ${confirmation.id} activated`} onClose={() => setConfirmation(null)}>
          <p className="text-sm text-ink">
            {confirmation.count} safety intervention{confirmation.count === 1 ? "" : "s"} acknowledged and logged as audit evidence.
          </p>
          <div className="mt-5 flex gap-3">
            <Button href="/permits">View all permits</Button>
            <Button variant="secondary" onClick={() => setConfirmation(null)}>Close</Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function InterventionCard({ item, checked, onToggle }: { item: InterventionItem; checked: boolean; onToggle: () => void }) {
  const s = severityStatus(item.severity);
  const border = item.severity === "critical" ? "border-critical" : item.severity === "caution" ? "border-caution" : "border-line";
  const bg = item.severity === "critical" ? "bg-critical-soft" : "bg-surface";

  return (
    <Card className={`border-l-4 p-4 ${border} ${bg}`}>
      <div className="flex items-center gap-2">
        <StatusPill token={s.token} label={s.label} />
        <h3 className="text-sm font-semibold">{item.title}</h3>
      </div>
      <p className="mt-2 text-[15px] leading-relaxed text-ink">{item.body}</p>
      {item.citation && (
        <p className="mt-2 text-xs text-muted">
          Source:{" "}
          {item.citation.equipment_tag ? (
            <a href={`/equipment/${item.citation.equipment_tag}`} className="font-medium text-primary underline"><Tag>{item.citation.ref}</Tag></a>
          ) : (
            <Tag>{item.citation.ref}</Tag>
          )}
        </p>
      )}
      {item.requires_acknowledgment && (
        <button
          onClick={onToggle}
          className={`mt-3 flex min-h-[48px] w-full items-center gap-3 rounded-lg border px-3 text-left text-sm font-medium ${checked ? "border-good bg-good-soft text-good" : "border-line bg-surface text-ink"}`}
        >
          <span className={`grid h-6 w-6 shrink-0 place-items-center rounded border-2 ${checked ? "border-good bg-good text-white" : "border-muted"}`}>
            {checked && <Check size={16} strokeWidth={3} />}
          </span>
          I acknowledge this and will apply the required precautions.
        </button>
      )}
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

const selectCls = "w-full min-h-[48px] rounded-lg border border-line bg-surface px-3 text-base outline-none focus:border-primary";
