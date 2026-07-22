// One status vocabulary for the whole app. Prediction risk, compliance status,
// intervention severity, and permit state all map to the same four tokens so a
// user learns the colour and word once. Colour is always paired with a label and
// an icon, never colour alone.

export type StatusToken = "critical" | "caution" | "good" | "info";

export interface StatusView {
  token: StatusToken;
  label: string;
}

export function riskStatus(risk: string | null | undefined): StatusView {
  switch (risk) {
    case "High":
      return { token: "critical", label: "High risk" };
    case "Elevated":
      return { token: "caution", label: "Elevated risk" };
    case "Watch":
      return { token: "info", label: "Watch" };
    default:
      return { token: "good", label: "Low risk" };
  }
}

export function complianceStatus(status: string): StatusView {
  switch (status) {
    case "overdue":
      return { token: "critical", label: "Overdue" };
    case "missing_evidence":
      return { token: "critical", label: "No record" };
    case "due_soon":
      return { token: "caution", label: "Due soon" };
    default:
      return { token: "good", label: "Compliant" };
  }
}

export function severityStatus(severity: string): StatusView {
  switch (severity) {
    case "critical":
      return { token: "critical", label: "Critical" };
    case "caution":
      return { token: "caution", label: "Caution" };
    default:
      return { token: "info", label: "Note" };
  }
}

export function workOrderStatus(status: string | null | undefined): StatusView {
  if (!status || status === "Closed") return { token: "good", label: status || "Closed" };
  return { token: "caution", label: status };
}
