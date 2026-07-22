"use client";

// Equipment list: scannable cards, one per asset, with the headline stats and an
// unmistakable incident badge so a machine with a safety event stands out.

import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";

import { EquipmentListItem, fetchEquipmentList } from "@/lib/api";
import { Card, ErrorNotice, SkeletonCard, Tag } from "@/components/ui";

export default function EquipmentGridPage() {
  const [items, setItems] = useState<EquipmentListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setItems(null);
    setError(null);
    fetchEquipmentList()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, [reloadKey]);

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold tracking-tight">Equipment</h1>
        <p className="mt-1 text-muted">Bharat Petrochem Unit-2 asset register</p>

        {error && (
          <div className="mt-6 space-y-3">
            <ErrorNotice
              title="Could not load equipment"
              detail={`Backend may be restarting or Neo4j briefly unavailable. ${error}`}
            />
            <button
              type="button"
              onClick={() => setReloadKey((k) => k + 1)}
              className="min-h-[40px] rounded-lg bg-primary px-4 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Retry
            </button>
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {!items && !error && [0, 1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
          {items?.map((e) => (
            <Link key={e.tag} href={`/equipment/${e.tag}`} className="animate-in">
              <Card className="h-full p-5 transition-colors hover:border-primary">
                <div className="flex items-start justify-between gap-2">
                  <Tag className="text-lg font-semibold">{e.tag}</Tag>
                  {e.incidents > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-critical-soft px-2.5 py-1 text-xs font-semibold text-critical">
                      <AlertTriangle size={13} strokeWidth={2.5} />
                      {e.incidents} incident{e.incidents > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-muted">{e.name ?? "-"}</p>
                <div className="mt-4 flex gap-6">
                  <Stat label="Work orders" value={e.work_orders} />
                  <Stat label="Incidents" value={e.incidents} critical={e.incidents > 0} />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, critical }: { label: string; value: number; critical?: boolean }) {
  return (
    <div>
      <div className={`text-xl font-semibold ${critical ? "text-critical" : "text-ink"}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
    </div>
  );
}
