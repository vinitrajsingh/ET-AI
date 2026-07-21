"use client";

// Permit register: every raised permit with its status and how many safety
// interventions were acknowledged (the beginning of the audit trail).

import Link from "next/link";
import { useEffect, useState } from "react";

import { Permit, fetchPermits, formatDate } from "@/lib/api";

export default function PermitsPage() {
  const [permits, setPermits] = useState<Permit[] | null>(null);

  useEffect(() => {
    fetchPermits()
      .then(setPermits)
      .catch(() => setPermits([]));
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Permits</h1>
            <p className="text-sm text-slate-500">Work permits and their acknowledged safety interventions</p>
          </div>
          <Link
            href="/permits/new"
            className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Raise a permit
          </Link>
        </header>

        {!permits && <p className="text-slate-500">Loading...</p>}
        {permits && permits.length === 0 && (
          <p className="text-slate-500">No permits yet. Raise one to see the intervention flow.</p>
        )}

        <div className="space-y-3">
          {permits?.map((p) => (
            <div key={p.permit_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{p.permit_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{p.permit_type}</span>
                </div>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                  {p.status}
                </span>
              </div>
              <div className="mt-2 text-sm text-slate-600">
                <Link href={`/equipment/${p.equipment_tag}`} className="font-medium text-sky-700 underline">
                  {p.equipment_tag}
                </Link>
                {p.description ? ` — ${p.description}` : ""}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {formatDate(p.created_date)} · {p.created_by ?? "unknown"} ·{" "}
                {p.acknowledged_items.length} intervention{p.acknowledged_items.length === 1 ? "" : "s"} acknowledged
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
