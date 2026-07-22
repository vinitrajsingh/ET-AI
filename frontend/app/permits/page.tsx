"use client";

// Permit register: every raised permit, its status, and how many safety
// interventions were acknowledged (the start of the audit trail).

import Link from "next/link";
import { useEffect, useState } from "react";

import { Permit, fetchPermits, formatDate } from "@/lib/api";
import { Button, Card, EmptyState, SkeletonCard, StatusPill, Tag } from "@/components/ui";

export default function PermitsPage() {
  const [permits, setPermits] = useState<Permit[] | null>(null);

  useEffect(() => {
    fetchPermits().then(setPermits).catch(() => setPermits([]));
  }, []);

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Permits</h1>
            <p className="mt-1 text-muted">Work permits and their acknowledged safety interventions.</p>
          </div>
          <Button href="/permits/new">Raise a permit</Button>
        </div>

        <div className="mt-6 space-y-3">
          {!permits && [0, 1].map((i) => <SkeletonCard key={i} />)}
          {permits && permits.length === 0 && (
            <EmptyState
              title="No permits yet"
              hint="Raise one to see the intervention flow and the acknowledgment audit trail."
              action={<Button href="/permits/new">Raise a permit</Button>}
            />
          )}
          {permits?.map((p) => (
            <Card key={p.permit_id} className="animate-in p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Tag className="text-sm font-semibold">{p.permit_id}</Tag>
                  <span className="text-sm text-muted">{p.permit_type}</span>
                </div>
                <StatusPill token={p.status === "closed" ? "good" : "info"} label={p.status} />
              </div>
              <div className="mt-2 text-sm text-muted">
                <Link href={`/equipment/${p.equipment_tag}`} className="font-medium text-primary underline"><Tag>{p.equipment_tag}</Tag></Link>
                {p.description ? ` — ${p.description}` : ""}
              </div>
              <div className="mt-1 text-xs text-muted">
                {formatDate(p.created_date)} · {p.created_by ?? "unknown"} · {p.acknowledged_items.length} intervention{p.acknowledged_items.length === 1 ? "" : "s"} acknowledged
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
