import {
  ArrowsLeftRight,
  ChartPieSlice,
  FileArrowUp,
  Gear,
  House,
  ListBullets,
  PlusCircle,
  TrayArrowDown,
  TrendUp,
  Users,
  type Icon,
} from "@phosphor-icons/react";

export interface NavItem {
  to: string;
  label: string;
  icon: Icon;
  end?: boolean;
  /** Hidden when the instance runs with import disabled (demo mode). */
  requiresImport?: boolean;
}

export const navItems: NavItem[] = [
  { to: "/", label: "Home", icon: House, end: true },
  { to: "/transactions", label: "Transactions", icon: ListBullets },
  { to: "/quick-add", label: "Quick add", icon: PlusCircle },
  { to: "/import", label: "Import", icon: FileArrowUp, requiresImport: true },
  { to: "/review", label: "Review", icon: TrayArrowDown },
  { to: "/transfers", label: "Transfers", icon: ArrowsLeftRight },
  { to: "/budget", label: "Budget", icon: ChartPieSlice },
  { to: "/people", label: "People", icon: Users },
  { to: "/income", label: "Income", icon: TrendUp },
  { to: "/settings", label: "Settings", icon: Gear },
];
