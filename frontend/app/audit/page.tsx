"use client";

// Audit package: the closing beat. Pick a scope, preview what the package will
// contain (including the permit acknowledgment logs), then generate the PDF. The
// generation shows honest progress and its elapsed time, because that "seconds,
// not weeks" contrast is the point.

import { useEffect, useState } from "react";
import { FileDown } from "lucide-react";

import { AuditPreview, EquipmentListItem, auditPackageUrl, fetchAuditPreview, fetchEquipmentList } from "@/lib/api";
import { Button, Card, Skeleton, Tag } from "@/components/ui";

export default function AuditPage() {
  const [assets, setAssets] = useState<EquipmentListItem[]>([]);
  const [scope, setScope] = useState("fleet");
  const [preview, setPreview] = useState<AuditPreview | null>(null);
  const [generating, setGenerating] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [lastMs, setLastMs] = useState<number | null>(null);

  useEffect(() => {
    fetchEquipmentList().then(setAssets).catch(() => setAssets([]));
  }, []);

  useEffect(() => {
    setPreview(null);
    setLastMs(null);
    fetchAuditPreview(scope).then(setPreview).catch(() => setPreview(null));
  }, [scope]);

  const ackCount = preview?.permits.reduce((n, p) => n + p.acknowledged.length, 0) ?? 0;

  const generate = async () => {
    setGenerating(true);
    setElapsed(0);
    const started = performance.now();
    const timer = setInterval(() => setElapsed((performance.now() - started) / 1000), 200);
    try {
      const res = await fetch(auditPackageUrl(scope));
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_package_${scope}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setLastMs(performance.now() - started);
    } finally {
      clearInterval(timer);
      setGenerating(false);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-bold tracking-tight">Audit package</h1>
        <p className="mt-1 text-muted">Assemble audit-ready compliance evidence in seconds.</p>

        <div className="mt-5 flex items-center gap-3">
          <label className="text-sm font-medium">Scope</label>
          <select value={scope} onChange={(e) => setScope(e.target.value)} className="min-h-[44px] rounded-lg border border-line bg-surface px-3 text-base outline-none focus:border-primary">
            <option value="fleet">Full fleet</option>
            {assets.map((a) => <option key={a.tag} value={a.tag}>{a.tag} — {a.name}</option>)}
          </select>
        </div>

        {!preview ? (
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-20" />)}</div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Count label="Compliance findings" value={preview.compliance.length} />
              <Count label="Incidents" value={preview.incidents.length} />
              <Count label="Permits" value={preview.permits.length} />
              <Count label="Acknowledged interventions" value={ackCount} highlight />
              <Count label="Maintenance records" value={preview.maintenance.length} />
              <Count label="Predictions" value={preview.predictions.length} />
            </div>

            {ackCount > 0 && (
              <Card className="mt-6 p-4">
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Acknowledged safety interventions (audit trail)</h2>
                {preview.permits.map((p) => (
                  <div key={p.permit_id} className="mb-2">
                    <div className="text-sm font-medium"><Tag>{p.permit_id}</Tag> · {p.permit_type} · <Tag>{p.equipment_tag}</Tag></div>
                    <ul className="ml-4 list-disc text-sm text-muted">
                      {p.acknowledged.map((a, i) => (
                        <li key={i}>{a.title} {a.cited ? <Tag className="text-muted">[{a.cited}]</Tag> : null}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </Card>
            )}

            <Card className="mt-6 border-l-4 border-primary p-5">
              <Button size="lg" onClick={generate} disabled={generating}>
                <FileDown size={18} />
                {generating ? `Generating... ${elapsed.toFixed(1)}s` : "Generate audit package (PDF)"}
              </Button>
              <p className="mt-3 text-sm text-muted">
                {lastMs !== null
                  ? `Assembled in ${(lastMs / 1000).toFixed(1)} seconds. An HSE manager spends weeks compiling this before an audit.`
                  : "The package pulls compliance findings, incidents, acknowledged permits, maintenance evidence, and predictions into one document."}
              </p>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}

function Count({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <Card className={`p-4 ${highlight ? "border-l-4 border-caution" : ""}`}>
      <div className={`text-2xl font-semibold ${highlight ? "text-caution" : "text-ink"}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
    </Card>
  );
}
