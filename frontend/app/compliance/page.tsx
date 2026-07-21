"use client";

// Fleet compliance overview: the HSE manager's answer to "which assets are out of
// compliance, and against which rule?" Overdue and missing items are loud, and the
// Health / Safety / Environment breakdown makes the full HSE coverage visible,
// including the Environment leg most teams skip.

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  COMPLIANCE_STATUS_LABEL,
  ComplianceStatus,
  FleetCompliance,
  fetchFleetCompliance,
  formatDate,
} from "@/lib/api";

const STATUS_PILL: Record<ComplianceStatus, string> = {
  compliant: "bg-emerald-100 text-emerald-700",
  due_soon: "bg-amber-100 text-amber-700",
  overdue: "bg-red-100 text-red-700",
  missing_evidence: "bg-red-100 text-red-700",
};

const CATEGORY_ACCENT: Record<string, string> = {
  Health: "text-blue-700",
  Safety: "text-orange-700",
  Environment: "text-green-700",
};

export default function CompliancePage() {
  const [fleet, setFleet] = useState<FleetCompliance | null>(null);

  useEffect(() => {
    fetchFleetCompliance().then(setFleet).catch(() => setFleet(null));
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-10">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">HSE Compliance</h1>
            <p className="text-sm text-slate-500">Regulatory status across the fleet, before an auditor finds it</p>
          </div>
          <Link href="/equipment" className="text-sm text-slate-500 hover:text-slate-800">
            Equipment →
          </Link>
        </header>

        {!fleet && <p className="text-slate-500">Loading...</p>}

        {fleet && (
          <>
            <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Compliant" value={fleet.totals.compliant} tone="emerald" />
              <Stat label="Due soon" value={fleet.totals.due_soon} tone="amber" />
              <Stat label="Overdue" value={fleet.totals.overdue} tone="red" />
              <Stat label="No record" value={fleet.totals.missing_evidence} tone="red" />
            </div>

            <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Health · Safety · Environment coverage
              </h2>
              <div className="flex flex-wrap gap-6">
                {(["Health", "Safety", "Environment"] as const).map((c) => (
                  <div key={c}>
                    <div className={`text-lg font-semibold ${CATEGORY_ACCENT[c]}`}>
                      {fleet.category_breakdown[c].gaps} / {fleet.category_breakdown[c].total}
                    </div>
                    <div className="text-xs uppercase tracking-wide text-slate-400">{c} gaps</div>
                  </div>
                ))}
              </div>
            </div>

            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Assets</h2>
            <div className="mb-8 space-y-2">
              {fleet.assets.map((a) => (
                <Link
                  key={a.tag}
                  href={`/equipment/${a.tag}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 hover:border-slate-300"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-semibold">{a.tag}</span>
                    <span className="text-sm text-slate-500">{a.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    {a.counts.overdue > 0 && <span className="text-red-600">{a.counts.overdue} overdue</span>}
                    {a.counts.missing_evidence > 0 && <span className="text-red-600">{a.counts.missing_evidence} no-record</span>}
                    {a.counts.compliant > 0 && <span className="text-emerald-600">{a.counts.compliant} ok</span>}
                    <span className={`rounded-full px-2 py-0.5 font-semibold ${STATUS_PILL[a.worst_status]}`}>
                      {COMPLIANCE_STATUS_LABEL[a.worst_status]}
                    </span>
                  </div>
                </Link>
              ))}
            </div>

            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">All findings</h2>
            <div className="space-y-2">
              {fleet.findings.map((f) => (
                <div key={`${f.equipment_tag}-${f.rule_code}`} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_PILL[f.status]}`}>
                      {COMPLIANCE_STATUS_LABEL[f.status]}
                    </span>
                    <span className={`text-xs font-medium ${CATEGORY_ACCENT[f.category]}`}>{f.category}</span>
                    <Link href={`/equipment/${f.equipment_tag}`} className="font-mono text-sky-700 underline">
                      {f.equipment_tag}
                    </Link>
                    <span className="font-medium">{f.title}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {f.regulation}
                    {f.evidence_ref ? ` · ${f.evidence_ref}${f.evidence_date ? ` (${formatDate(f.evidence_date)})` : ""}` : ""}
                  </div>
                  {f.gap && <p className="mt-1 text-xs text-red-600">{f.gap}</p>}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

const STAT_TONES: Record<string, string> = {
  emerald: "border-emerald-200 text-emerald-700",
  amber: "border-amber-200 text-amber-700",
  red: "border-red-200 text-red-700",
};

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className={`rounded-xl border bg-white p-4 ${STAT_TONES[tone]}`}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}
