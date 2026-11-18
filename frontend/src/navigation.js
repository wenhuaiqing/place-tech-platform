// Auto-discovers pages under src/pages/<Section>/<Page>.jsx. The folder name
// becomes the URL slug; MODULE_META fixes the label, icon, group and order.

import { Building2, ClipboardCheck, Compass, FileSearch, Home, KeyRound, Megaphone, MessageSquareText, Milestone, ShieldCheck, Wrench } from "lucide-react";

const PAGE_MODULES = import.meta.glob("./pages/*/*.jsx", { eager: true });

export const MODULE_META = {
  Overview:   { label: "Overview",          icon: Compass,           group: "Start here", order: 0 },
  WorkOrders: { label: "Work orders",       icon: ClipboardCheck,    group: "Workflow", order: 1, slug: "work-orders" },
  Sales:      { label: "Sales",             icon: Home,              group: "Reports", order: 2, slug: "sales" },
  Rentals:    { label: "Rentals",           icon: KeyRound,          group: "Reports", order: 3, slug: "rentals" },
  Offices:    { label: "Offices",           icon: Building2,         group: "Reports", order: 4, slug: "offices" },
  Marketing:  { label: "Marketing",         icon: Megaphone,         group: "Reports", order: 4.5, slug: "marketing" },
  Checks:     { label: "Data checks",       icon: ShieldCheck,       group: "Trusting the numbers", order: 5, slug: "data-checks" },
  Ask:        { label: "Ask the data",      icon: MessageSquareText, group: "Trusting the numbers", order: 6, slug: "ask" },
  Built:      { label: "How it is run",     icon: Wrench,            group: "The role", order: 7, slug: "how-it-is-run" },
  FirstDays:  { label: "First 90 days",     icon: Milestone,         group: "The role", order: 8, slug: "first-90-days" },
};

export const SEARCH_ICON = FileSearch;

export function getRoutes() {
  const seen = new Map();
  for (const [path, module] of Object.entries(PAGE_MODULES)) {
    const match = path.match(/^\.\/pages\/([^/]+)\/([^/]+)\.jsx$/);
    if (!match || seen.has(match[1]) || !MODULE_META[match[1]]) continue;
    const meta = MODULE_META[match[1]];
    seen.set(match[1], { section: match[1], label: meta.label, icon: meta.icon, group: meta.group, order: meta.order,
      to: `/${meta.slug || match[1].toLowerCase()}`, component: module.default });
  }
  return [...seen.values()].sort((a, b) => a.order - b.order);
}

export const GROUP_NOTES = {
  Workflow: "Try it: approve your own work order. The rules refuse, and say why.",
  "Trusting the numbers": "Every figure is checked before it is shown.",
};
