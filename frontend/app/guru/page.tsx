"use client";

// Guru Mode: capture a senior engineer's experience before it retires with them.
// Record or type a note about an asset; the system transcribes, structures, and
// stores it, credited to the engineer by name forever. A typed transcript is a
// first-class path (demo insurance: live audio is the flakiest thing on stage).

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  EquipmentListItem,
  GuruNote,
  approveGuruNote,
  createGuruNote,
  fetchEquipmentList,
  fetchGuruNotes,
} from "@/lib/api";

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
      setError(`${String(e)} — if audio failed, type the note instead (text fallback).`);
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: string) => {
    await approveGuruNote(id);
    loadNotes();
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 px-5 py-8">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Guru Mode</h1>
            <p className="text-sm text-slate-500">Capture experience before it walks out the door</p>
          </div>
          <Link href="/copilot" className="text-sm text-slate-500 hover:text-slate-800">
            Ask Copilot →
          </Link>
        </div>

        <div className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold">Share your experience</h2>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Equipment">
              <select value={tag} onChange={(e) => setTag(e.target.value)} className={inputClass}>
                {assets.map((a) => (
                  <option key={a.tag} value={a.tag}>
                    {a.tag}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Your name">
              <input
                value={engineer}
                onChange={(e) => setEngineer(e.target.value)}
                placeholder="e.g. Rajesh Kumar"
                className={inputClass}
              />
            </Field>
          </div>

          <Field label="Voice note (optional, Hindi or English)">
            <input type="file" accept="audio/*" onChange={(e) => setAudio(e.target.files?.[0] ?? null)} />
          </Field>

          <Field label="Or type the note (text fallback)">
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={3}
              placeholder="What have you noticed about this equipment over the years?"
              className={`${inputClass} resize-none`}
            />
          </Field>

          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)} />
            Senior engineer (auto-approve). Uncheck to hold for admin review.
          </label>

          <button
            onClick={submit}
            disabled={busy || !engineer || (!transcript && !audio)}
            className="w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy ? "Capturing..." : "Capture knowledge"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        {captured && <CapturedCard note={captured} />}

        <h2 className="mt-8 mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Captured knowledge ({notes.length})
        </h2>
        <div className="space-y-3">
          {notes.map((n) => (
            <NoteCard key={n.note_id} note={n} onApprove={() => approve(n.note_id)} />
          ))}
        </div>
      </div>
    </main>
  );
}

function CapturedCard({ note }: { note: GuruNote }) {
  return (
    <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
      <h3 className="font-semibold text-emerald-800">Captured, credited to {note.engineer_name}</h3>
      <dl className="mt-2 space-y-1 text-sm text-emerald-900">
        <Row label="Symptom" value={note.symptom} />
        <Row label="Meaning" value={note.meaning} />
        <Row label="Action" value={note.recommended_action} />
      </dl>
      <p className="mt-2 text-xs italic text-emerald-700">Transcript: {note.transcript}</p>
    </div>
  );
}

function NoteCard({ note, onApprove }: { note: GuruNote; onApprove: () => void }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="text-sm">
          <span className="font-semibold">{note.engineer_name}</span>
          <span className="text-slate-400"> on </span>
          <Link href={`/equipment/${note.equipment_tag}`} className="font-mono text-sky-700 underline">
            {note.equipment_tag}
          </Link>
        </div>
        {note.approved ? (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">approved</span>
        ) : (
          <button onClick={onApprove} className="rounded-full bg-amber-500 px-3 py-0.5 text-xs font-medium text-white">
            Approve
          </button>
        )}
      </div>
      <p className="mt-2 text-sm text-slate-700">{note.summary || note.symptom}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <span className="font-semibold">{label}:</span> {value}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  );
}

const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500";
