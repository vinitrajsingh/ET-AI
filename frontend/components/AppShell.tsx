"use client";

// The app shell: one consistent frame around every page. A top bar with the
// product name and a one-tap role switcher, a left sidebar on desktop, and a
// bottom tab bar on mobile (easier to reach one-handed than a hamburger). The
// visible navigation is tailored to the current role, but every route stays
// reachable by switching roles or typing the URL.

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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

import { ROLE_HOME, ROLE_LABEL, Role, useRole } from "@/components/RoleContext";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV: Record<string, NavItem> = {
  copilot: { href: "/copilot", label: "Copilot", icon: MessageSquareText },
  equipment: { href: "/equipment", label: "Equipment", icon: Boxes },
  permits: { href: "/permits", label: "Permits", icon: ClipboardCheck },
  compliance: { href: "/compliance", label: "Compliance", icon: ShieldCheck },
  audit: { href: "/audit", label: "Audit", icon: FileText },
  guru: { href: "/guru", label: "Guru Mode", icon: Mic2 },
  ingest: { href: "/ingest", label: "Ingestion", icon: Upload },
};

const ROLE_NAV: Record<Role, NavItem[]> = {
  technician: [NAV.copilot, NAV.equipment],
  engineer: [NAV.equipment, NAV.permits, NAV.copilot],
  hse: [NAV.compliance, NAV.permits, NAV.audit],
  admin: [NAV.ingest, NAV.equipment, NAV.guru, NAV.compliance, NAV.copilot],
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const { role } = useRole();
  const pathname = usePathname();
  const items = ROLE_NAV[role];

  const isActive = (href: string) => pathname === href || (href !== "/" && pathname.startsWith(href));

  return (
    <div className="min-h-screen">
      <TopBar />
      <div className="mx-auto flex w-full max-w-6xl">
        {/* Desktop sidebar */}
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-56 shrink-0 border-r border-line px-3 py-4 md:block">
          <nav className="space-y-1">
            {items.map((item) => (
              <SidebarLink key={item.href} item={item} active={isActive(item.href)} />
            ))}
          </nav>
        </aside>

        <main className="min-w-0 flex-1 pb-24 md:pb-10">{children}</main>
      </div>

      {/* Mobile bottom tabs */}
      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-flow-col border-t border-line bg-surface md:hidden">
        {items.slice(0, 5).map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex min-h-[60px] flex-col items-center justify-center gap-1 text-xs font-medium ${active ? "text-primary" : "text-muted"}`}
            >
              <Icon size={22} strokeWidth={active ? 2.5 : 2} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={`flex min-h-[44px] items-center gap-3 rounded-lg px-3 text-sm font-medium ${
        active ? "bg-info-soft text-primary" : "text-ink hover:bg-bg"
      }`}
    >
      <Icon size={19} strokeWidth={active ? 2.5 : 2} />
      {item.label}
    </Link>
  );
}

function TopBar() {
  const { role, setRole } = useRole();
  const router = useRouter();

  const onRoleChange = (next: Role) => {
    setRole(next);
    router.push(ROLE_HOME[next]);
  };

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-line bg-surface px-4">
      <Link href="/" className="flex items-baseline gap-2">
        <span className="text-lg font-bold tracking-tight text-primary">SANJEEVANI</span>
        <span className="hidden text-xs text-muted sm:inline">Bharat Petrochem Unit-2</span>
      </Link>

      <label className="flex items-center gap-2 text-sm">
        <span className="hidden text-muted sm:inline">Viewing as</span>
        <select
          value={role}
          onChange={(e) => onRoleChange(e.target.value as Role)}
          className="min-h-[40px] rounded-lg border border-line bg-surface px-2 font-medium text-ink outline-none focus:border-primary"
          aria-label="Switch role"
        >
          {(Object.keys(ROLE_LABEL) as Role[]).map((r) => (
            <option key={r} value={r}>
              {ROLE_LABEL[r]}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}
