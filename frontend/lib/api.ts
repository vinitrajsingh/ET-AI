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
  type: "workorder" | "incident" | "document" | "prediction";
  ref: string;
  title: string | null;
  snippet: string | null;
  equipment_tag: string | null;
}

export interface CopilotAnswer {
  answer: string;
  citations: CopilotCitation[];
  resolved_equipment: string | null;
  context_used: {
    graph_facts?: string | null;
    passages?: { label: string; doc_id: string | null; source: string | null; snippet: string | null }[];
  };
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

// Small display helper shared by both pages: "2021-02-12" -> "12 Feb 2021".
export function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
