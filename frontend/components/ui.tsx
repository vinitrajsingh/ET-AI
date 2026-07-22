"use client";

// The SANJEEVANI component kit. A small, consistent set used across every screen
// so nothing is hand-rolled twice. All colours come from the tokens in
// globals.css, all tap targets are comfortable on a phone.

import Link from "next/link";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

import { StatusToken } from "@/lib/status";

// --- Card ---

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <div className={`rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(15,27,45,0.04)] ${className}`}>
      {children}
    </div>
  );
}

// --- Section (heading + optional count, optional collapsible) ---

export function Section({
  title,
  count,
  action,
  children,
}: {
  title: string;
  count?: number;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          {title}
          {typeof count === "number" && <span className="ml-1 text-line">({count})</span>}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

// --- Status pill (semantic, colour + icon + label) ---

const PILL: Record<StatusToken, { cls: string; Icon: typeof Info }> = {
  critical: { cls: "text-critical bg-critical-soft", Icon: AlertTriangle },
  caution: { cls: "text-caution bg-caution-soft", Icon: AlertCircle },
  good: { cls: "text-good bg-good-soft", Icon: CheckCircle2 },
  info: { cls: "text-info bg-info-soft", Icon: Info },
};

export function StatusPill({ token, label, className = "" }: { token: StatusToken; label: string; className?: string }) {
  const { cls, Icon } = PILL[token];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${cls} ${className}`}>
      <Icon size={13} strokeWidth={2.5} aria-hidden />
      {label}
    </span>
  );
}

// --- Chip (small labelled tag) ---

export function Chip({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted ${className}`}>
      {children}
    </span>
  );
}

// --- Button (primary / secondary / danger; renders as button or link) ---

type ButtonProps = {
  variant?: "primary" | "secondary" | "danger";
  size?: "md" | "lg";
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
  children: ReactNode;
};

const VARIANT = {
  primary: "bg-primary text-white hover:bg-primary-hover",
  secondary: "border border-line bg-surface text-ink hover:bg-bg",
  danger: "bg-critical text-white hover:brightness-95",
};

export function Button({
  variant = "primary",
  size = "md",
  href,
  onClick,
  disabled,
  type = "button",
  className = "",
  children,
}: ButtonProps) {
  const sizeCls = size === "lg" ? "min-h-[48px] px-5 text-base" : "min-h-[44px] px-4 text-sm";
  const cls = `inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${VARIANT[variant]} ${sizeCls} ${className}`;
  if (href && !disabled) {
    return (
      <Link href={href} className={cls}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}

// --- File field (styled button, since a raw <input type="file"> ignores our
// design system and shows a plain OS control with no pointer cursor) ---

export function FileField({
  label,
  accept,
  file,
  onChange,
}: {
  label: string;
  accept?: string;
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const inputId = `file-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label
        htmlFor={inputId}
        className="inline-flex min-h-[44px] cursor-pointer items-center justify-center gap-2 rounded-lg border border-line bg-surface px-4 text-sm font-semibold text-ink transition-colors duration-150 hover:bg-bg"
      >
        {label}
      </label>
      <input
        id={inputId}
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        className="sr-only"
      />
      <span className="text-sm text-muted">{file ? file.name : "No file chosen"}</span>
    </div>
  );
}

// --- Modal (focus-trapped enough for a demo: esc + backdrop close) ---

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        className="animate-in w-full max-w-lg rounded-t-2xl bg-surface p-5 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} aria-label="Close" className="grid h-11 w-11 place-items-center rounded-lg text-muted hover:bg-bg">
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// --- Empty state ---

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface px-5 py-8 text-center">
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
      {action && <div className="mt-3 flex justify-center">{action}</div>}
    </div>
  );
}

// --- Skeleton placeholder ---

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-line/60 ${className}`} />;
}

export function SkeletonCard() {
  return (
    <Card className="p-4">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="mt-3 h-3 w-2/3" />
      <Skeleton className="mt-2 h-3 w-1/2" />
    </Card>
  );
}

// --- Error notice ---

export function ErrorNotice({ title, detail }: { title: string; detail?: string }) {
  return (
    <Card className="border-critical/30 bg-critical-soft p-4">
      <p className="font-medium text-critical">{title}</p>
      {detail && <p className="mt-1 text-sm text-muted">{detail}</p>}
    </Card>
  );
}

// Monospace tag used for equipment/work-order/permit ids so they scan cleanly.
export function Tag({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-[0.92em] ${className}`}>{children}</span>;
}
