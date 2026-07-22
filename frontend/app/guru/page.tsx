"use client";

// Guru Mode: capture a senior engineer's experience before it retires with them.
// The form is deliberately simple and welcoming, because the user may be a
// long-serving veteran who dislikes software. Record a voice note or just type it;
// the system structures and stores it, credited to them by name.

import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";

import { EquipmentListItem, GuruNote, approveGuruNote, createGuruNote, fetchEquipmentList, fetchGuruNotes } from "@/lib/api";
import { Button, Card, Section, StatusPill, Tag } from "@/components/ui";

export default function GuruPage() {
  const [assets, setAssets] = useState<EquipmentListItem[]>([]);
  const [tag, setTag] = useState("P-101");
  const [engineer, setEngineer] = useState("");
  const [transcript, setTranscript] = useState("");
  const [audio, setAudio] = useState<File | null>(null);
  const [approved, setApproved] = useState(true);

  const [busy, setBusy] = useState(false);
  const [captured, setCaptured] = useState<GuruNote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<GuruNote[]>([]);

  const loadNotes = () => fetchGuruNotes(undefined, true).then(setNotes).catch(() => setNotes([]));

  useEffect(() => {
    fetchEquipmentList().then(setAssets).catch(() => setAssets([]));
    loadNotes();
  }, []);

  const submit = async () => {
    if (!tag || !engineer || (!transcript && !audio)) return;
    setBusy(true);
    setError(null);
    setCaptured(null);
    try {
      const note = await createGuruNote({ equipment_tag: tag, engineer_name: engineer, transcript, approved, audio });
      setCaptured(note);
      setTranscript("");
      setAudio(null);
      loadNotes();
    } catch (e) {
      setError(`${String(e)}. If the voice note failed, type the note instead.`);
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: string) => {
    await approveGuruNote(id);
    loadNotes();
  };

  return (
    <div className="px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold tracking-tight">Guru Mode</h1>
        <p className="mt-1 text-muted">Capture your experience so it stays with the plant.</p>

        <Card className="mt-5 space-y-4 p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Equipment">
              <select value={tag} onChange={(e) => setTag(e.target.value)} className={inputCls}>
                {assets.map((a) => <option key={a.tag} value={a.tag}>{a.tag}</option>)}
              </select>
            </Field>
            <Field label="Your name">
              <input value={engineer} onChange={(e) => setEngineer(e.target.value)} placeholder="e.g. Rajesh Kumar" className={inputCls} />
            </Field>
          </div>

          <Field label="Voice note (optional, Hindi or English)">
            <input type="file" accept="audio/*" onChange={(e) => setAudio(e.target.files?.[0] ?? null)} className="text-sm" />
          </Field>

          <Field label="Or type the note">
            <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={3} placeholder="What have you noticed about this equipment over the years?" className={`${inputCls} resize-none`} />
          </Field>

          <label className="flex min-h-[44px] items-center gap-3 text-sm">
            <input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)} className="h-5 w-5" />
            Senior engineer (approve immediately). Uncheck to hold for admin review.
          </label>

          <Button size="lg" onClick={submit} disabled={busy || !engineer || (!transcript && !audio)} className="w-full">
            {busy ? "Capturing..." : "Capture knowledge"}
          </Button>
          {error && <p className="text-sm text-critical">{error}</p>}
        </Card>

        {captured && (
          <Card className="mt-4 border-l-4 border-good bg-good-soft p-4">
            <div className="flex items-center gap-2 font-semibold text-good">
              <CheckCircle2 size={18} /> Captured, credited to {captured.engineer_name}
            </div>
            <dl className="mt-2 space-y-1 text-sm text-ink">
              {captured.symptom && <div><span className="font-medium">Symptom:</span> {captured.symptom}</div>}
              {captured.meaning && <div><span className="font-medium">Meaning:</span> {captured.meaning}</div>}
              {captured.recommended_action && <div><span className="font-medium">Action:</span> {captured.recommended_action}</div>}
            </dl>
            <p className="mt-2 text-xs italic text-muted">Transcript: {captured.transcript}</p>
          </Card>
        )}

        <div className="mt-8">
          <Section title="Captured knowledge" count={notes.length}>
            <div className="space-y-3">
              {notes.map((n) => (
                <Card key={n.note_id} className="p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm">
                      <span className="font-semibold">{n.engineer_name}</span>
                      <span className="text-muted"> on </span>
                      <Link href={`/equipment/${n.equipment_tag}`} className="text-primary underline"><Tag>{n.equipment_tag}</Tag></Link>
                    </div>
                    {n.approved ? (
                      <StatusPill token="good" label="Approved" />
                    ) : (
                      <Button variant="secondary" onClick={() => approve(n.note_id)}>Approve</Button>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-ink">{n.summary || n.symptom}</p>
                </Card>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputCls = "w-full min-h-[48px] rounded-lg border border-line bg-surface px-3 text-base outline-none focus:border-primary";
