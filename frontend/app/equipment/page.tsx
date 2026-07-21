"use client";

// Equipment landing grid: the entry point into the 360 views. One card per
// asset with its headline stats. Incidents are surfaced loudly (a red badge) so
// a machine with a safety event, like T-205, is obvious at a glance.

import Link from "next/link";
import { useEffect, useState } from "react";

import { EquipmentListItem, fetchEquipmentList } from "@/lib/api";

export default function EquipmentGridPage() {
  const [items, setItems] = useState<EquipmentListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquipmentList()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-10">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Equipment</h1>
            <p className="text-sm text-slate-500">Bharat Petrochem Unit-2 — asset register</p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/permits/new"
              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
            >
              Raise a permit
            </Link>
            <Link
              href="/copilot"
              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
            >
              Ask Copilot
            </Link>
          </div>
        </header>

        {error && <ErrorBox message={error} />}
        {!items && !error && <p className="text-slate-500">Loading equipment...</p>}
        {items && items.length === 0 && (
          <p className="text-slate-500">No equipment found. Seed the corpus first.</p>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items?.map((e) => (
            <EquipmentCard key={e.tag} item={e} />
          ))}
        </div>
      </div>
    </main>
  );
}

function EquipmentCard({ item }: { item: EquipmentListItem }) {
  return (
    <Link
      href={`/equipment/${item.tag}`}
      className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between">
        <span className="font-mono text-lg font-semibold text-slate-900">{item.tag}</span>
        {item.incidents > 0 && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            ⚠ {item.incidents} incident{item.incidents > 1 ? "s" : ""}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-slate-600">{item.name ?? "-"}</p>
      <div className="mt-4 flex gap-5 text-sm">
        <Stat label="Work orders" value={item.work_orders} />
        <Stat label="Incidents" value={item.incidents} highlight={item.incidents > 0} />
      </div>
    </Link>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div>
      <div className={`text-xl font-semibold ${highlight ? "text-red-600" : "text-slate-900"}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      Could not reach the API. Is the backend running on {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}?
      <div className="mt-1 font-mono text-xs text-red-500">{message}</div>
    </div>
  );
}
