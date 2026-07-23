import { ReactNode } from "react";
import NavigationRail from "./NavigationRail";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen bg-transparent">
      <NavigationRail />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

