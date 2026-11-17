// Auto-discovers pages under src/pages/<Section>/<Page>.jsx. The folder name
// becomes the URL slug; MODULE_META fixes the label, icon, group and order.

import {
  Activity, Bot, ClipboardCheck, Compass, FileText, GitPullRequest, Milestone, Network, Route, ShieldCheck, Sparkles, TableProperties, Wallet,
} from "lucide-react";

const PAGE_MODULES = import.meta.glob("./pages/*/*.jsx", { eager: true });

export const MODULE_META = {
  Overview:   { label: "Overview",           icon: Compass,         group: "Start here", order: 0 },
  Register:   { label: "Tool register",      icon: TableProperties, group: "Days 1 to 30: know what exists", order: 1, slug: "register" },
  Discovery:  { label: "How it was found",   icon: Network,         group: "Days 1 to 30: know what exists", order: 2, slug: "discovery" },
  AiRegister: { label: "AI register",        icon: Sparkles,        group: "Days 1 to 30: know what exists", order: 3, slug: "ai-register" },
  Gate:       { label: "Production gate",    icon: ShieldCheck,     group: "Days 31 to 60: bring it in", order: 4, slug: "gate" },
  Changes:    { label: "Changes",            icon: GitPullRequest,  group: "Days 31 to 60: bring it in", order: 5, slug: "changes" },
  PavedRoad:  { label: "Paved road",         icon: Route,           group: "Days 31 to 60: bring it in", order: 6, slug: "paved-road" },
  Monitoring: { label: "Monitoring",         icon: Activity,        group: "Days 61 to 90: run it", order: 7, slug: "monitoring" },
  Triage:     { label: "Incident triage",    icon: Bot,             group: "Days 61 to 90: run it", order: 8, slug: "triage" },
  Cost:       { label: "Cloud cost",         icon: Wallet,          group: "Days 61 to 90: run it", order: 9, slug: "cost" },
  CabReport:  { label: "CAB report",         icon: FileText,        group: "Days 61 to 90: run it", order: 10, slug: "cab-report" },
  FirstDays:  { label: "First 90 days",      icon: Milestone,       group: "The role", order: 11, slug: "first-90-days" },
};

export const AUDIT_ICON = ClipboardCheck;

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

export const GROUP_NOTES = {};
