"use client";

// Audit package: the closing beat. Pick a scope, preview what the package will
// contain (findings, permits with acknowledgments, incidents, predictions), and
// generate the PDF. The generation time is shown on purpose: weeks of manual
// compilation collapses to seconds.

import Link from "next/link";
import { useEffect, useState } from "react";

import { AuditPreview, EquipmentListItem, auditPackageUrl, fetchAuditPreview, fetchEquipmentList } from "@/lib/api";

export default function AuditPage() {
  const [assets, setAssets] = useState<EquipmentListItem[]>([]);
  const [scope, setScope] = useState("fleet");
  const [preview, setPreview] = useState<AuditPreview | null>(null);
  const [genMs, setGenMs] = useState<number | null>(null);

  useEffect(() => {
    fetchEquipmentList().then(setAssets).catch(() => setAssets([]));
  }, []);

  useEffect(() => {
    setPreview(null);
    setGenMs(null);
    const started = performance.now();
    fetchAuditPreview(scope)
      .then((p) => {
        setPreview(p);
        setGenMs(Math.round(performance.now() - started));
      })
      .catch(() => setPreview(null));
  }, [scope]);

  const ackCount = preview?.permits.reduce((n, p) => n + p.acknowledged.length, 0) ?? 0;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Audit package</h1>
            <p className="text-sm text-slate-500">Assemble audit-ready compliance evidence in seconds</p>
          </div>
          <Link href="/compliance" className="text-sm text-slate-500 hover:text-slate-800">
            Compliance →
          </Link>
        </header>

        <div className="mb-6 flex items-center gap-3">
          <label className="text-sm font-medium">Scope</label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
          >
            <option value="fleet">Full fleet</option>
            {assets.map((a) => (
              <option key={a.tag} value={a.tag}>
                {a.tag} — {a.name}
              </option>
            ))}
          </select>
        </div>

        {!preview && <p className="text-slate-500">Assembling preview...</p>}

        {preview && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Count label="Compliance findings" value={preview.compliance.length} />
              <Count label="Incidents" value={preview.incidents.length} />
              <Count label="Permits" value={preview.permits.length} />
              <Count label="Acknowledged interventions" value={ackCount} highlight />
              <Count label="Maintenance records" value={preview.maintenance.length} />
              <Count label="Predictions" value={preview.predictions.length} />
            </div>

            {ackCount > 0 && (
              <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Acknowledged safety interventions (audit trail)
                </h2>
                {preview.permits.map((p) => (
                  <div key={p.permit_id} className="mb-2">
                    <div className="text-sm font-medium">
                      {p.permit_id} · {p.permit_type} · {p.equipment_tag}
                    </div>
                    <ul className="ml-4 list-disc text-xs text-slate-600">
                      {p.acknowledged.map((a, i) => (
                        <li key={i}>
                          {a.title} {a.cited ? <span className="font-mono text-slate-400">[{a.cited}]</span> : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}

            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
              <a
                href={auditPackageUrl(scope)}
                className="inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700"
              >
                Generate audit package (PDF)
              </a>
              {genMs !== null && (
                <p className="mt-2 text-sm text-emerald-800">
                  Preview assembled in {(genMs / 1000).toFixed(1)}s. An HSE manager spends weeks compiling this before an audit.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function Count({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border bg-white p-4 ${highlight ? "border-orange-200" : "border-slate-200"}`}>
      <div className={`text-2xl font-semibold ${highlight ? "text-orange-700" : "text-slate-900"}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}
