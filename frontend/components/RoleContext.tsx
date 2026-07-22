"use client";

// Non-authenticated role selector. Four roles from the project brief, stored in
// localStorage so a chosen view survives a refresh during the demo. No backend,
// no auth: roles only change the default navigation and landing page.

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Role = "technician" | "engineer" | "hse" | "admin";

export const ROLE_LABEL: Record<Role, string> = {
  technician: "Field Technician",
  engineer: "Engineer / Supervisor",
  hse: "HSE Officer",
  admin: "Admin",
};

export const ROLE_HOME: Record<Role, string> = {
  technician: "/copilot",
  engineer: "/equipment",
  hse: "/compliance",
  admin: "/ingest",
};

interface RoleState {
  role: Role;
  setRole: (r: Role) => void;
  ready: boolean;
}

const RoleCtx = createContext<RoleState>({ role: "engineer", setRole: () => {}, ready: false });

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>("engineer");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("sanjeevani-role") as Role | null;
    if (saved && saved in ROLE_LABEL) setRoleState(saved);
    setReady(true);
  }, []);

  const setRole = (r: Role) => {
    setRoleState(r);
    localStorage.setItem("sanjeevani-role", r);
  };

  return <RoleCtx.Provider value={{ role, setRole, ready }}>{children}</RoleCtx.Provider>;
}

export function useRole() {
  return useContext(RoleCtx);
}
