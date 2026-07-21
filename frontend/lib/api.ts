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

export function fetchEquipmentList(): Promise<EquipmentListItem[]> {
  return getJson<EquipmentListItem[]>("/equipment");
}

export function fetchEquipment360(tag: string): Promise<Equipment360> {
  return getJson<Equipment360>(`/equipment/${encodeURIComponent(tag)}`);
}

// Small display helper shared by both pages: "2021-02-12" -> "12 Feb 2021".
export function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
