// Single source of truth for talking to the SANJEEVANI backend.
// Base URL comes from NEXT_PUBLIC_API_URL so it can change per environment,
// defaulting to the local FastAPI dev server. Types mirror the backend's
// pydantic response models so the pages stay honest about the shape of the data.

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface EquipmentListItem {
  tag: string;
  name: string | null;
  work_orders: number;
  incidents: number;
}

export interface TimelineItem {
  kind: "workorder" | "incident";
  id: string;
  date: string | null;
  title: string | null;
  description: string | null;
  status: string | null;
  extra: {
    wo_type?: string | null;
    cost?: number | null;
    parts_used?: string | null;
    technician?: string | null;
  };
}

export interface DocumentLink {
  doc_id: string;
  title: string | null;
  type: string | null;
  relationship: "HAS_MANUAL" | "GOVERNED_BY" | "MENTIONS";
  label: string;
}

export interface PersonWork {
  name: string;
  role: string | null;
  jobs: number;
}

export interface HealthSnapshot {
  total_work_orders: number;
  corrective_count: number;
  preventive_count: number;
  open_work_orders: number;
  last_work_order_date: string | null;
  incident_count: number;
}

export interface EquipmentSummary {
  tag: string;
  name: string | null;
  type: string | null;
  location: string | null;
}

export interface Equipment360 {
  summary: EquipmentSummary;
  timeline: TimelineItem[];
  documents: DocumentLink[];
  people: PersonWork[];
  health: HealthSnapshot;
}

export interface PredictionEvidence {
  wo_id: string;
  date: string | null;
  description: string | null;
}

export interface PredictionResult {
  equipment_tag: string;
  failure_type: string;
  failure_label: string;
  status: "predicted" | "insufficient_history";
  cycles: number;
  reference_date: string;
  mean_interval_months: number | null;
  current_age_months: number | null;
  interval_min_days: number | null;
  interval_max_days: number | null;
  last_failure_date: string | null;
  predicted_window_start: string | null;
  predicted_center: string | null;
  predicted_window_end: string | null;
  days_until_window_start: number | null;
  days_until_center: number | null;
  risk_level: "Low" | "Watch" | "Elevated" | "High" | null;
  risk_ratio: number | null;
  confidence: number | null;
  confidence_note: string;
  explanation: string;
  message: string;
  evidence: PredictionEvidence[];
  supporting_signals: string[];
}

export interface CopilotCitation {
  type: "workorder" | "incident" | "document" | "prediction" | "guru";
  ref: string;
  title: string | null;
  snippet: string | null;
  equipment_tag: string | null;
  score: number | null;
}

export interface CopilotAnswer {
  answer: string;
  citations: CopilotCitation[];
  resolved_equipment: string | null;
  context_used: {
    graph_facts?: string | null;
    passages?: { label: string; doc_id: string | null; source: string | null; score: number | null; snippet: string | null }[];
  };
  usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new ApiError(res.status, `Request failed (${res.status}) for ${path}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Request failed (${res.status}) for ${path}`);
  }
  return res.json() as Promise<T>;
}

export function fetchEquipmentList(): Promise<EquipmentListItem[]> {
  return getJson<EquipmentListItem[]>("/equipment");
}

export function fetchEquipment360(tag: string): Promise<Equipment360> {
  return getJson<Equipment360>(`/equipment/${encodeURIComponent(tag)}`);
}

export function fetchEquipmentPrediction(tag: string): Promise<PredictionResult[]> {
  return getJson<PredictionResult[]>(`/equipment/${encodeURIComponent(tag)}/prediction`);
}

export function askCopilot(query: string, history: ChatTurn[]): Promise<CopilotAnswer> {
  return postJson<CopilotAnswer>("/copilot/ask", { query, history });
}

// --- Permits / Intervention engine ---

// Kept in step with intervention_service.PERMIT_TYPES on the backend.
export const PERMIT_TYPES = ["Hot Work", "Confined Space Entry", "Working at Height", "General Maintenance"];

export interface InterventionCitation {
  type: string;
  ref: string;
  equipment_tag: string | null;
  title: string | null;
}

export interface InterventionItem {
  id: string;
  severity: "info" | "caution" | "critical";
  title: string;
  body: string;
  citation: InterventionCitation | null;
  requires_acknowledgment: boolean;
}

export interface InterventionResult {
  equipment_tag: string;
  permit_type: string;
  items: InterventionItem[];
  has_blocking: boolean;
}

export interface Permit {
  permit_id: string;
  permit_type: string;
  equipment_tag: string;
  description: string | null;
  status: string;
  created_by: string | null;
  created_date: string;
  acknowledged_items: InterventionItem[];
}

export function evaluatePermit(body: {
  permit_type: string;
  equipment_tag: string;
  description: string;
}): Promise<InterventionResult> {
  return postJson<InterventionResult>("/permits/evaluate", body);
}

export function createPermit(body: {
  permit_type: string;
  equipment_tag: string;
  description: string;
  created_by: string;
  acknowledged: string[];
}): Promise<Permit> {
  return postJson<Permit>("/permits", body);
}

export function fetchPermits(): Promise<Permit[]> {
  return getJson<Permit[]>("/permits");
}

// --- Guru Mode ---

export interface GuruNote {
  note_id: string;
  equipment_tag: string;
  engineer_name: string;
  symptom: string;
  meaning: string;
  recommended_action: string;
  summary: string;
  transcript: string;
  language: string;
  approved: boolean;
}

// Sends multipart so it can carry an optional audio file alongside the fields.
export async function createGuruNote(form: {
  equipment_tag: string;
  engineer_name: string;
  transcript?: string;
  approved: boolean;
  audio?: File | null;
}): Promise<GuruNote> {
  const body = new FormData();
  body.append("equipment_tag", form.equipment_tag);
  body.append("engineer_name", form.engineer_name);
  body.append("approved", String(form.approved));
  if (form.transcript) body.append("transcript", form.transcript);
  if (form.audio) body.append("audio", form.audio);

  const res = await fetch(`${API_BASE}/guru/notes`, { method: "POST", body });
  if (!res.ok) {
    throw new ApiError(res.status, `Note capture failed (${res.status})`);
  }
  return res.json() as Promise<GuruNote>;
}

export function fetchGuruNotes(equipmentTag?: string, includeUnapproved = false): Promise<GuruNote[]> {
  const params = new URLSearchParams();
  if (equipmentTag) params.set("equipment_tag", equipmentTag);
  if (includeUnapproved) params.set("include_unapproved", "true");
  return getJson<GuruNote[]>(`/guru/notes?${params.toString()}`);
}

export function approveGuruNote(noteId: string): Promise<{ note_id: string; approved: boolean }> {
  return postJson(`/guru/notes/${noteId}/approve`, {});
}

// --- HSE Compliance ---

export type ComplianceStatus = "compliant" | "due_soon" | "overdue" | "missing_evidence";
export type HSECategory = "Health" | "Safety" | "Environment";

export interface ComplianceFinding {
  equipment_tag: string;
  rule_code: string;
  title: string;
  category: HSECategory;
  severity: string;
  regulation: string;
  regulation_doc_id: string | null;
  requires: string;
  status: ComplianceStatus;
  evidence_ref: string | null;
  evidence_type: string | null;
  evidence_date: string | null;
  due_date: string | null;
  gap: string | null;
}

export interface AssetCompliance {
  tag: string;
  name: string | null;
  counts: Record<ComplianceStatus, number>;
  worst_status: ComplianceStatus;
}

export interface FleetCompliance {
  assets: AssetCompliance[];
  totals: Record<ComplianceStatus, number>;
  category_breakdown: Record<HSECategory, { total: number; gaps: number }>;
  findings: ComplianceFinding[];
}

export function fetchEquipmentCompliance(tag: string): Promise<ComplianceFinding[]> {
  return getJson<ComplianceFinding[]>(`/equipment/${encodeURIComponent(tag)}/compliance`);
}

export function fetchFleetCompliance(): Promise<FleetCompliance> {
  return getJson<FleetCompliance>("/compliance");
}

// Shared status styling for compliance pills (used on both the asset and fleet pages).
export const COMPLIANCE_STATUS_LABEL: Record<ComplianceStatus, string> = {
  compliant: "Compliant",
  due_soon: "Due soon",
  overdue: "Overdue",
  missing_evidence: "No record",
};

// Small display helper shared by both pages: "2021-02-12" -> "12 Feb 2021".
export function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
