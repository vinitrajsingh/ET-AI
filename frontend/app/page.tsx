"use client";

// Role-aware landing. Rather than a generic home, each role sees the handful of
// things their job actually starts with, as large, plainly labelled cards.

import Link from "next/link";
import {
  Boxes,
  ClipboardCheck,
  FileText,
  MessageSquareText,
  Mic2,
  ShieldCheck,
  Upload,
  type LucideIcon,
} from "lucide-react";

import { ROLE_LABEL, Role, useRole } from "@/components/RoleContext";
import { Card } from "@/components/ui";

interface Action {
  href: string;
  title: string;
  desc: string;
  icon: LucideIcon;
}

const ACTIONS: Record<Role, Action[]> = {
  technician: [
    { href: "/copilot", title: "Ask the copilot", desc: "Get a cited answer about any equipment or procedure.", icon: MessageSquareText },
    { href: "/equipment", title: "Look up equipment", desc: "See an asset's full history, health, and known issues.", icon: Boxes },
  ],
  engineer: [
    { href: "/equipment", title: "Equipment 360", desc: "Health, predictions, timeline, and documents per asset.", icon: Boxes },
    { href: "/permits/new", title: "Raise a permit", desc: "Safety checks run before the permit is activated.", icon: ClipboardCheck },
    { href: "/copilot", title: "Ask the copilot", desc: "Cited answers from the plant knowledge graph.", icon: MessageSquareText },
  ],
  hse: [
    { href: "/compliance", title: "Compliance board", desc: "Regulatory status across the fleet, before an audit.", icon: ShieldCheck },
    { href: "/permits", title: "Permits", desc: "Active permits and their acknowledged safety warnings.", icon: ClipboardCheck },
    { href: "/audit", title: "Audit package", desc: "Assemble audit-ready evidence in seconds.", icon: FileText },
  ],
  admin: [
    { href: "/ingest", title: "Ingest documents", desc: "Feed the knowledge graph from the document corpus.", icon: Upload },
    { href: "/guru", title: "Guru knowledge", desc: "Capture and approve senior-engineer experience.", icon: Mic2 },
    { href: "/equipment", title: "Equipment 360", desc: "Browse every asset's full profile.", icon: Boxes },
  ],
};

export default function Home() {
  const { role } = useRole();
  const actions = ACTIONS[role];

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm font-medium text-muted">{ROLE_LABEL[role]}</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">What would you like to do?</h1>
        <p className="mt-2 max-w-2xl text-muted">
          SANJEEVANI keeps every drawing, work order, incident, and safety rule for Bharat Petrochem Unit-2 in one
          place, and speaks up before problems happen.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {actions.map((a) => {
            const Icon = a.icon;
            return (
              <Link key={a.href} href={a.href} className="animate-in">
                <Card className="flex h-full items-start gap-4 p-5 transition-colors hover:border-primary">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-info-soft text-primary">
                    <Icon size={22} />
                  </div>
                  <div>
                    <h2 className="font-semibold">{a.title}</h2>
                    <p className="mt-1 text-sm text-muted">{a.desc}</p>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
