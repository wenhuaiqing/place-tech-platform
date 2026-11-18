// Auto-discovers pages under src/pages/<Section>/<Page>.jsx. The folder name
// becomes the URL slug; MODULE_META fixes the label, icon, group and order.

import { Building2, ClipboardCheck, Compass, FileSearch, Home, KeyRound, Megaphone, MessageSquareText, Milestone, ShieldCheck, Wrench } from "lucide-react";

const PAGE_MODULES = import.meta.glob("./pages/*/*.jsx", { eager: true });

export const MODULE_META = {
  Overview:   { label: "Overview",          icon: Compass,           group: "The business", order: 0 },
  Sales:      { label: "Sales",             icon: Home,              group: "The business", order: 1, slug: "sales" },
  Rentals:    { label: "Rentals",           icon: KeyRound,          group: "The business", order: 2, slug: "rentals" },
  WorkOrders: { label: "Work orders",       icon: ClipboardCheck,    group: "The business", order: 3, slug: "work-orders" },
  Offices:    { label: "Offices",           icon: Building2,         group: "The business", order: 4, slug: "offices" },
  Marketing:  { label: "Marketing",         icon: Megaphone,         group: "The business", order: 4.5, slug: "marketing" },
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
  "Trusting the numbers": "Every figure is checked before it is shown.",
};
