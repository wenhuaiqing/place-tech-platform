// Small pieces every page here uses: money from cents, the gate's outcome,
// tiers, and the tool detail that opens from any table.

import { useState } from "react";
import { useTheme } from "../context/ThemeContext.jsx";
import { fmtAud, fmtDate, fmtInt, useApi } from "./api.js";
import { Modal } from "./kit.jsx";
import { Badge, Callout, KeyValues, Loading, Mono, SectionTitle, Table } from "./ui.jsx";

export function aud(cents, opts) {
  return cents == null ? "-" : fmtAud(Number(cents) / 100, { decimals: 2, ...opts });
}

export function audWhole(cents) {
  return cents == null ? "-" : fmtAud(Number(cents) / 100, { decimals: 0 });
}

const OUTCOME = { refuse: ["critical", "Refused"], hold: ["warning", "Held for a person"], pass: ["good", "Passes"] };

export function OutcomeBadge({ outcome }) {
  if (!outcome) return <Badge tone="neutral">Not scanned</Badge>;
  const [tone, label] = OUTCOME[outcome] || ["neutral", outcome];
  return <Badge tone={tone}>{label}</Badge>;
}

export function TierBadge({ tier }) {
  const tone = tier === 1 ? "serious" : tier === 2 ? "warning" : "neutral";
  return <Badge tone={tone}>Tier {tier}</Badge>;
}

const SEVERITY = { critical: "critical", warning: "warning", info: "neutral" };

export function SeverityBadge({ severity }) {
  return <Badge tone={SEVERITY[severity] || "neutral"}>{severity}</Badge>;
}

const CR_STATUS = { submitted: ["warning", "Awaiting CAB"], approved: ["good", "Approved"], rejected: ["critical", "Rejected"],
  implemented: ["neutral", "Implemented"] };

export function ChangeBadge({ status }) {
  const [tone, label] = CR_STATUS[status] || ["neutral", status];
  return <Badge tone={tone}>{label}</Badge>;
}

export function HomeBadge({ home, status }) {
  if (status === "retired" || status === "merged") return <Badge tone="neutral">{status === "retired" ? "Retired" : "Merged"}</Badge>;
  if (status === "in production on Place platform") return <Badge tone="good">Place platform</Badge>;
  return home === "place-github" ? <Badge tone="good">Place GitHub</Badge> : <Badge tone="warning">Personal accounts</Badge>;
}

export const RULE_NAMES = {
  G01: "Secret in the code", G02: "Secret in the history", G03: "Privileged key in the browser", G04: "Data open to the internet",
  G05: "SQL built from input", G06: "Function answers anyone", G07: "Model called outside the gateway", G08: "Package that does not exist",
  G09: "Dependency under an advisory", G10: "Personal data in logs", G11: "Agent connected to personal storage",
};

export function NotBuilt({ items }) {
  const { t } = useTheme();
  return (
    <>
      <SectionTitle>Deliberately not built here</SectionTitle>
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.65, color: t.textMuted, maxWidth: 900 }}>
        {items.map((i) => <li key={i}>{i}</li>)}
      </ul>
    </>
  );
}

// A tool's register entry, its sources, flags, gate findings and cost.
export function ToolDetail({ toolId, onClose }) {
  const { data, error } = useApi(toolId ? `/api/register/${toolId}` : null);
  const tl = data?.tool;
  return (
    <Modal open={Boolean(toolId)} onClose={onClose} title={tl ? `${tl.tool_id} - ${tl.name}` : "Tool"} width={900}>
      {error && <Callout tone="critical">{error.message}</Callout>}
      {!data && !error && <Loading />}
      {tl && (
        <>
          <p style={{ fontSize: 13, marginTop: 0 }}>{tl.purpose || "Nobody declared this tool in the survey; it was found in the exports and is named after its resource."}</p>
          <KeyValues columns={3} items={[
            ["Owner", `${tl.owner_name || "Unknown"}${tl.owner_role ? `, ${tl.owner_role}` : ""}${tl.owner_status === "left" ? ` (left ${fmtDate(tl.owner_left_on)})` : ""}`],
            ["Office", tl.office || "-"],
            ["Process", tl.process || "Not declared"],
            ["Tier", `Tier ${tl.tier}: ${tl.tier_reason}`],
            ["Data classes", tl.data_classes],
            ["Users in 30 days", fmtInt(tl.users_30d)],
            ["Records held", fmtInt(tl.records)],
            ["Hosting", [tl.hosting, tl.database].filter(Boolean).join(" + ") || (tl.kind === "agent" ? "Copilot Studio" : "A laptop")],
            ["AI route", tl.ai_route || "None"],
            ["Repository", tl.repo || (tl.repo_candidates ? `Unresolved: ${tl.repo_candidates}` : "-")],
            ["Address", tl.hostname || "-"],
            ["Cost last month", aud(tl.monthly_cost_aud_cents)],
            ["Paid by", tl.paid_by],
            ["Home", tl.home === "place-github" ? "Place GitHub organisation" : "Personal accounts"],
            ["Status", tl.status],
          ]} />
          {data.flags.length > 0 && (
            <>
              <SectionTitle>Flags</SectionTitle>
              <Table rows={data.flags} maxHeight={260} columns={[
                { key: "severity", label: "Severity", render: (r) => <SeverityBadge severity={r.severity} /> },
                { key: "flag", label: "Flag" },
                { key: "detail", label: "Detail", wrap: true },
              ]} />
            </>
          )}
          <SectionTitle>Production gate</SectionTitle>
          {data.findings.length === 0 ? <p style={{ fontSize: 13 }}>No findings: the gate passes it.</p> : (
            <Table rows={data.findings} maxHeight={300} columns={[
              { key: "outcome", label: "Outcome", render: (r) => <OutcomeBadge outcome={r.outcome} /> },
              { key: "rule_id", label: "Check", render: (r) => `${r.rule_id} ${RULE_NAMES[r.rule_id]}` },
              { key: "path", label: "Where", render: (r) => <Mono>{r.path}:{r.line}</Mono> },
              { key: "detail", label: "What to do", wrap: true },
            ]} />
          )}
          <SectionTitle>Joined from</SectionTitle>
          <Table rows={data.sources} maxHeight={240} columns={[
            { key: "source", label: "Export" },
            { key: "ref", label: "Key", render: (r) => <Mono>{r.ref}</Mono> },
            { key: "joined_by", label: "Joined by", wrap: true },
          ]} />
          {data.changes.length > 0 && (
            <>
              <SectionTitle>Changes</SectionTitle>
              <Table rows={data.changes} maxHeight={200} columns={[
                { key: "cr_id", label: "Change" }, { key: "title", label: "Title", wrap: true },
                { key: "status", label: "Status", render: (r) => <ChangeBadge status={r.status} /> },
              ]} />
            </>
          )}
        </>
      )}
    </Modal>
  );
}

export function useToolDetail() {
  const [toolId, setToolId] = useState(null);
  return { open: setToolId, node: <ToolDetail toolId={toolId} onClose={() => setToolId(null)} /> };
}
