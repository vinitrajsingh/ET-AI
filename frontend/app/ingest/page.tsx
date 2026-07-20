"use client";

// Throwaway dev page to exercise the ingestion API by hand: check /health,
// upload a single file, or seed the whole corpus. No styling effort on purpose;
// this is a wiring test, not the real UI.

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

export default function IngestTestPage() {
  const [health, setHealth] = useState<unknown>(null);
  const [result, setResult] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const refreshHealth = async () => {
    try {
      const res = await fetch(`${API}/health`);
      setHealth(await res.json());
    } catch (e) {
      setHealth({ error: String(e) });
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const uploadFile = async () => {
    if (!file) return;
    setBusy("upload");
    setResult(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API}/ingest`, { method: "POST", body });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setBusy(null);
    }
  };

  const seedCorpus = async () => {
    setBusy("seed");
    setResult(null);
    try {
      const res = await fetch(`${API}/ingest/bulk`, { method: "POST" });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <main style={{ maxWidth: 820, margin: "40px auto", padding: 16, fontFamily: "monospace" }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>SANJEEVANI ingestion test</h1>

      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <strong>/health</strong>
          <button onClick={refreshHealth}>refresh</button>
        </div>
        <pre style={boxStyle}>{JSON.stringify(health, null, 2)}</pre>
      </section>

      <section style={{ marginBottom: 24 }}>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button onClick={uploadFile} disabled={!file || busy !== null}>
          {busy === "upload" ? "uploading..." : "POST /ingest"}
        </button>
      </section>

      <section style={{ marginBottom: 24 }}>
        <button onClick={seedCorpus} disabled={busy !== null}>
          {busy === "seed" ? "seeding (this takes a while)..." : "Seed corpus (POST /ingest/bulk)"}
        </button>
      </section>

      <section>
        <strong>result</strong>
        <pre style={boxStyle}>{result ? JSON.stringify(result, null, 2) : "—"}</pre>
      </section>
    </main>
  );
}

const boxStyle: React.CSSProperties = {
  background: "#111",
  color: "#0f0",
  padding: 12,
  borderRadius: 6,
  overflow: "auto",
  maxHeight: 420,
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};
