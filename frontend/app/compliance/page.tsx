"use client";

// Fleet compliance board: the HSE manager's glance. Overdue and missing items are
// loud, the Health / Safety / Environment coverage is visible, and each asset
// drills into its full profile.

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { FleetCompliance, HSECategory, fetchFleetCompliance, formatDate } from "@/lib/api";
import { complianceStatus } from "@/lib/status";
import { Card, Section, Skeleton, StatusPill, Tag } from "@/components/ui";

const CATEGORY_TONE: Record<HSECategory, string> = {
  Health: "text-info",
  Safety: "text-caution",
  Environment: "text-good",
};

export default function CompliancePage() {
  const [fleet, setFleet] = useState<FleetCompliance | null>(null);

  useEffect(() => {
    fetchFleetCompliance().then(setFleet).catch(() => setFleet(null));
  }, []);

  if (!fleet) {
    return (
      <div className="px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">HSE Compliance</h1>
          <p className="mt-1 text-muted">Regulatory status across the fleet, before an auditor finds it.</p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Compliant" value={fleet.totals.compliant} token="good" />
          <Stat label="Due soon" value={fleet.totals.due_soon} token="caution" />
          <Stat label="Overdue" value={fleet.totals.overdue} token="critical" />
          <Stat label="No record" value={fleet.totals.missing_evidence} token="critical" />
        </div>

        <Card className="p-4">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Health, Safety, Environment coverage</h2>
          <div className="flex flex-wrap gap-8">
            {(["Health", "Safety", "Environment"] as const).map((c) => (
              <div key={c}>
                <div className={`text-xl font-semibold ${CATEGORY_TONE[c]}`}>
                  {fleet.category_breakdown[c].gaps} / {fleet.category_breakdown[c].total}
                </div>
                <div className="text-xs uppercase tracking-wide text-muted">{c} gaps</div>
              </div>
            ))}
          </div>
        </Card>

        <Section title="Assets">
          <div className="space-y-2">
            {fleet.assets.map((a) => {
              const worst = complianceStatus(a.worst_status);
              return (
                <Link key={a.tag} href={`/equipment/${a.tag}`}>
                  <Card className="flex items-center justify-between p-4 transition-colors hover:border-primary">
                    <div>
                      <Tag className="text-sm font-semibold">{a.tag}</Tag>
                      <span className="ml-2 text-sm text-muted">{a.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusPill token={worst.token} label={worst.label} />
                      <ChevronRight size={18} className="text-muted" />
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        </Section>

        <Section title="All findings" count={fleet.findings.length}>
          <div className="space-y-2">
            {fleet.findings.map((f) => {
              const s = complianceStatus(f.status);
              return (
                <Card key={`${f.equipment_tag}-${f.rule_code}`} className="p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill token={s.token} label={s.label} />
                    <span className={`text-xs font-semibold ${CATEGORY_TONE[f.category]}`}>{f.category}</span>
                    <Link href={`/equipment/${f.equipment_tag}`} className="text-primary underline"><Tag>{f.equipment_tag}</Tag></Link>
                    <span className="text-sm font-medium">{f.title}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {f.regulation}
                    {f.evidence_ref ? <> · <Tag>{f.evidence_ref}</Tag>{f.evidence_date ? ` (${formatDate(f.evidence_date)})` : ""}</> : null}
                  </p>
                  {f.gap && <p className="mt-1 text-xs text-critical">{f.gap}</p>}
                </Card>
              );
            })}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Stat({ label, value, token }: { label: string; value: number; token: "good" | "caution" | "critical" }) {
  const tone = token === "good" ? "text-good" : token === "caution" ? "text-caution" : "text-critical";
  return (
    <Card className="p-4">
      <div className={`text-2xl font-semibold ${tone}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
    </Card>
  );
}
