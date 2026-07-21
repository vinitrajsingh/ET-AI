"use client";

// Raise a permit: the HSE climax. As soon as an asset and permit type are chosen
// the system checks the graph and surfaces safety interventions BEFORE the permit
// can be activated. Critical items (a recalled near-miss, a governing regulation)
// must be acknowledged or the form will not submit.

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  EquipmentListItem,
  InterventionItem,
  InterventionResult,
  PERMIT_TYPES,
  createPermit,
  evaluatePermit,
  fetchEquipmentList,
} from "@/lib/api";

export default function NewPermitPage() {
  const [assets, setAssets] = useState<EquipmentListItem[]>([]);
  const [tag, setTag] = useState("");
  const [permitType, setPermitType] = useState("");
  const [description, setDescription] = useState("");
  const [createdBy, setCreatedBy] = useState("HSE Supervisor");

  const [result, setResult] = useState<InterventionResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquipmentList().then(setAssets).catch(() => setAssets([]));
  }, []);

  // Run the pre-activation safety check whenever the asset or permit type changes.
  useEffect(() => {
    setResult(null);
    setAcknowledged(new Set());
    setCreatedId(null);
    setError(null);
    if (!tag || !permitType) return;

    setChecking(true);
    evaluatePermit({ permit_type: permitType, equipment_tag: tag, description })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setChecking(false));
    // description is intentionally not a dependency: the check keys off asset + type.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tag, permitType]);

  const toggleAck = (id: string) => {
    setAcknowledged((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const blockingUnmet =
    result?.items.some((i) => i.severity === "critical" && i.requires_acknowledgment && !acknowledged.has(i.id)) ??
    false;

  const submit = async () => {
    if (!result || blockingUnmet) return;
    setError(null);
    try {
      const permit = await createPermit({
        permit_type: permitType,
        equipment_tag: tag,
        description,
        created_by: createdBy,
        acknowledged: [...acknowledged],
      });
      setCreatedId(permit.permit_id);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-8">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">Raise a permit</h1>
          <Link href="/permits" className="text-sm text-slate-500 hover:text-slate-800">
            All permits →
          </Link>
        </div>

        <div className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <Field label="Equipment">
            <select value={tag} onChange={(e) => setTag(e.target.value)} className={selectClass}>
              <option value="">Select an asset...</option>
              {assets.map((a) => (
                <option key={a.tag} value={a.tag}>
                  {a.tag} — {a.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Permit type">
            <select value={permitType} onChange={(e) => setPermitType(e.target.value)} className={selectClass}>
              <option value="">Select a permit type...</option>
              {PERMIT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What work is being done?"
              className={`${selectClass} resize-none`}
            />
          </Field>

          <Field label="Raised by">
            <input value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} className={selectClass} />
          </Field>
        </div>

        {checking && <p className="mt-6 text-sm text-slate-500">Checking the knowledge graph for safety history...</p>}

        {result && !createdId && (
          <Interventions
            result={result}
            acknowledged={acknowledged}
            onToggle={toggleAck}
            blockingUnmet={blockingUnmet}
            onSubmit={submit}
          />
        )}

        {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {createdId && (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
            <h2 className="font-semibold text-emerald-800">Permit {createdId} activated</h2>
            <p className="mt-1 text-sm text-emerald-700">
              {acknowledged.size} safety intervention{acknowledged.size === 1 ? "" : "s"} acknowledged and logged as
              audit evidence.
            </p>
            <Link href="/permits" className="mt-3 inline-block text-sm font-medium text-emerald-800 underline">
              View all permits
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}

function Interventions({
  result,
  acknowledged,
  onToggle,
  blockingUnmet,
  onSubmit,
}: {
  result: InterventionResult;
  acknowledged: Set<string>;
  onToggle: (id: string) => void;
  blockingUnmet: boolean;
  onSubmit: () => void;
}) {
  if (result.items.length === 0) {
    return (
      <div className="mt-6">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          No safety interventions found. This permit can proceed.
        </div>
        <SubmitBar disabled={false} onSubmit={onSubmit} label="Activate permit" />
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="mb-2 flex items-center gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          ⚠ SANJEEVANI intervention · {result.items.length} finding{result.items.length === 1 ? "" : "s"}
        </h2>
      </div>
      <div className="space-y-3">
        {result.items.map((item) => (
          <InterventionCard
            key={item.id}
            item={item}
            checked={acknowledged.has(item.id)}
            onToggle={() => onToggle(item.id)}
          />
        ))}
      </div>
      {blockingUnmet && (
        <p className="mt-3 text-sm font-medium text-red-600">
          Acknowledge every critical item before this permit can be activated.
        </p>
      )}
      <SubmitBar disabled={blockingUnmet} onSubmit={onSubmit} label="Acknowledge & activate permit" />
    </div>
  );
}

const SEVERITY_STYLES: Record<string, { box: string; badge: string }> = {
  critical: { box: "border-red-300 bg-red-50", badge: "bg-red-600 text-white" },
  caution: { box: "border-amber-300 bg-amber-50", badge: "bg-amber-500 text-white" },
  info: { box: "border-slate-200 bg-white", badge: "bg-slate-400 text-white" },
};

function InterventionCard({
  item,
  checked,
  onToggle,
}: {
  item: InterventionItem;
  checked: boolean;
  onToggle: () => void;
}) {
  const style = SEVERITY_STYLES[item.severity] ?? SEVERITY_STYLES.info;
  return (
    <div className={`rounded-xl border p-4 ${style.box}`}>
      <div className="flex items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-xs font-bold uppercase ${style.badge}`}>{item.severity}</span>
        <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
      </div>
      <p className="mt-2 text-sm text-slate-700">{item.body}</p>

      {item.citation && (
        <div className="mt-2 text-xs">
          <span className="text-slate-400">Source: </span>
          {item.citation.equipment_tag ? (
            <Link
              href={`/equipment/${item.citation.equipment_tag}`}
              className="font-mono font-medium text-sky-700 underline"
            >
              {item.citation.ref}
            </Link>
          ) : (
            <span className="font-mono">{item.citation.ref}</span>
          )}
        </div>
      )}

      {item.requires_acknowledgment && (
        <label className="mt-3 flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-800">
          <input type="checkbox" checked={checked} onChange={onToggle} className="h-4 w-4" />
          I acknowledge this and will apply the required precautions.
        </label>
      )}
    </div>
  );
}

function SubmitBar({ disabled, onSubmit, label }: { disabled: boolean; onSubmit: () => void; label: string }) {
  return (
    <button
      onClick={onSubmit}
      disabled={disabled}
      className="mt-4 w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
    >
      {label}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  );
}

const selectClass =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500";
