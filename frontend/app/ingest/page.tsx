"use client";

// Admin ingestion. Check that the databases are reachable, upload a single
// document, or seed the whole corpus. This is where the knowledge graph is fed.

import { useEffect, useState } from "react";

import { API_BASE } from "@/lib/api";
import { Button, Card, FileField, Section, StatusPill } from "@/components/ui";

interface Health {
  status?: string;
  neo4j?: string;
  qdrant?: string;
  postgres?: string;
  error?: string;
}

export default function IngestPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  const refreshHealth = () =>
    fetch(`${API_BASE}/health`).then((r) => r.json()).then(setHealth).catch((e) => setHealth({ error: String(e) }));

  useEffect(() => {
    refreshHealth();
  }, []);

  const upload = async () => {
    if (!file) return;
    setBusy("upload");
    setResult(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API_BASE}/ingest`, { method: "POST", body });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setBusy(null);
    }
  };

  const seed = async () => {
    setBusy("seed");
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/ingest/bulk`, { method: "POST" });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setBusy(null);
    }
  };

  const dbs: [string, string | undefined][] = [
    ["Neo4j", health?.neo4j],
    ["Qdrant", health?.qdrant],
    ["Postgres", health?.postgres],
  ];

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Ingestion</h1>
          <p className="mt-1 text-muted">Feed the knowledge graph from the document corpus.</p>
        </div>

        <Section title="System health" action={<Button variant="secondary" onClick={refreshHealth}>Refresh</Button>}>
          <Card className="flex flex-wrap gap-3 p-4">
            {health?.error && <span className="text-sm text-critical">{health.error}</span>}
            {dbs.map(([name, state]) => (
              <div key={name} className="flex items-center gap-2">
                <span className="text-sm font-medium">{name}</span>
                <StatusPill token={state === "ok" ? "good" : "critical"} label={state === "ok" ? "Connected" : state ?? "unknown"} />
              </div>
            ))}
          </Card>
        </Section>

        <Section title="Upload a document">
          <Card className="space-y-3 p-4">
            <FileField label="Choose file" file={file} onChange={setFile} />
            <Button onClick={upload} disabled={!file || busy !== null}>{busy === "upload" ? "Uploading..." : "Upload and ingest"}</Button>
          </Card>
        </Section>

        <Section title="Seed the corpus">
          <Card className="space-y-3 p-4">
            <p className="text-sm text-muted">Ingest every document in the corpus in one pass.</p>
            <Button onClick={seed} disabled={busy !== null}>{busy === "seed" ? "Seeding, this takes a moment..." : "Seed corpus"}</Button>
          </Card>
        </Section>

        {result != null && (
          <Section title="Result">
            <Card className="p-4">
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs text-ink">{JSON.stringify(result, null, 2)}</pre>
            </Card>
          </Section>
        )}
      </div>
    </div>
  );
}
