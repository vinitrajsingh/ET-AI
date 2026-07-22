import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
import { RoleProvider } from "@/components/RoleContext";

export const metadata: Metadata = {
  title: "SANJEEVANI",
  description: "Industrial knowledge and safety intelligence for Bharat Petrochem Unit-2",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full">
        <RoleProvider>
          <AppShell>{children}</AppShell>
        </RoleProvider>
      </body>
    </html>
  );
}
