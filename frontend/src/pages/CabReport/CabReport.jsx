// The fortnightly CAB report, assembled from the data when it is opened.

import { Printer } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtDate, fmtDateTime, fmtInt, useApi } from "../../lib/api.js";
import { ChangeBadge, RULE_NAMES, aud, audWhole } from "../../lib/place.jsx";
import { Badge, Button, Callout, Card, ErrorNote, KeyValues, Loading, PageHeader, SectionTitle, Table } from "../../lib/ui.jsx";

function Section({ n, title, children }) {
  const { t } = useTheme();
  return (
    <section style={{ breakInside: "avoid", marginBottom: 6 }}>
      <SectionTitle><span style={{ color: t.brand, marginRight: 8 }}>{n}</span>{title}</SectionTitle>
      {children}
    </section>
  );
}

export default function CabReport() {
  const { t } = useTheme();
  const { data: d, error } = useApi("/api/cab");
  if (error) return <ErrorNote error={error} />;
  if (!d) return <><PageHeader title="CAB report" /><Loading /></>;
  const waiting = d.changes.filter((c) => c.status === "submitted");
  const decided = d.changes.filter((c) => c.status !== "submitted");
  const p = (s) => <p style={{ fontSize: 13, lineHeight: 1.6, margin: "0 0 8px", maxWidth: 900 }}>{s}</p>;
  return (
    <>
      <PageHeader
        title="CAB report"
        brief="Agree a platform standard and AI guardrails with CAB, put monitoring and cost reporting in place, and deliver a first CAB report"
        subtitle={`For the fortnight ${fmtDate(d.period.from)} to ${fmtDate(d.period.to)}. Assembled from the data when this page is opened, so it is never out of date and never typed up. Written for a board that meets for an hour: decisions first, then what changed, then risks.`}
        right={<Button icon={Printer} onClick={() => window.print()}>Print</Button>}
      />
      <Card>
        <Section n="1" title={`Decisions wanted (${waiting.length})`}>
          {waiting.length === 0 ? p("Nothing is waiting for CAB.") : (
            <Table rows={waiting} columns={[
              { key: "cr_id", label: "Change" },
              { key: "title", label: "What", wrap: true },
              { key: "proposed_by", label: "Proposed by" },
              { key: "proposed_at", label: "On", render: (r) => fmtDate(r.proposed_at) },
            ]} />
          )}
        </Section>

        <Section n="2" title="Changes decided">
          <Table rows={decided} columns={[
            { key: "cr_id", label: "Change" },
            { key: "title", label: "What", wrap: true },
            { key: "status", label: "Outcome", render: (r) => <ChangeBadge status={r.status} /> },
            { key: "decided_by", label: "Decided by", render: (r) => r.decided_by || "-" },
            { key: "decision_note", label: "Note", wrap: true, render: (r) => r.decision_note || "-" },
          ]} />
        </Section>

        <Section n="3" title={`Refused by the rules (${d.refusals.length})`}>
          {p("Every attempt the rules refused, with the reason given. A refusal is the controls working; a pattern of them is a conversation.")}
          <Table rows={d.refusals} empty="No refusals this fortnight." columns={[
            { key: "ts", label: "When", render: (r) => fmtDateTime(r.ts, { seconds: false }) },
            { key: "actor", label: "Who" },
            { key: "action", label: "Tried to" },
            { key: "detail", label: "Refused because", wrap: true },
          ]} />
        </Section>

        <Section n="4" title="The estate">
          <KeyValues columns={3} items={[
            ["Tools in the register", fmtInt(d.register.tools)],
            ["Found, not declared", fmtInt(d.register.undeclared)],
            ["Tier 1", fmtInt(d.register.tier1)],
            ["Owner has left, still in use", fmtInt(d.register.orphaned)],
            ["On personal accounts", fmtInt(d.register.personal_accounts)],
            ["In the Place GitHub organisation", fmtInt(d.register.place_github)],
          ]} />
          {d.register.holds.length > 0 && <div style={{ marginTop: 10 }}>{p(`Held for a person: ${d.register.holds.map((h) => `${h.hold_id} (${h.ref})`).join("; ")}.`)}</div>}
        </Section>

        <Section n="5" title="The production gate">
          {p(`Refused ${d.gate.by_outcome.find((r) => r.outcome === "refuse")?.tools ?? 0}, held ${d.gate.by_outcome.find((r) => r.outcome === "hold")?.tools ?? 0}, passing ${d.gate.by_outcome.find((r) => r.outcome === "pass")?.tools ?? 0}. The checks finding most:`)}
          <Table rows={d.gate.top_rules} columns={[
            { key: "rule_id", label: "Check", render: (r) => `${r.rule_id} ${RULE_NAMES[r.rule_id]}` },
            { key: "tools", label: "Tools", align: "right" },
          ]} />
        </Section>

        <Section n="6" title="Operations">
          {p(`${fmtInt(d.operations.alerts)} alerts became ${d.operations.pages} pages over four weeks. Incidents:`)}
          <Table rows={d.operations.incidents} columns={[
            { key: "incident_id", label: "Incident" },
            { key: "opened_at", label: "Opened", render: (r) => fmtDateTime(r.opened_at, { seconds: false }) },
            { key: "tool_key", label: "Tool" },
            { key: "first_signal", label: "Signal" },
          ]} />
          <div style={{ marginTop: 10 }}>
            <Callout tone="warning" title="Due within 45 days">
              {d.operations.forecasts.map((f) => (
                <div key={f.resource}>{f.resource}: {f.kind}, {f.days_left < 0 ? `expired ${fmtDate(f.due_on)}` : `${f.days_left} days (${fmtDate(f.due_on)})`}</div>
              ))}
            </Callout>
          </div>
        </Section>

        <Section n="7" title="Cost">
          {p(`${d.cost.month}: ${audWhole(d.cost.total)}, against ${audWhole(d.cost.previous)} the month before (excluding the sandbox). ${audWhole(d.cost.removable)} a month can go now.`)}
          <Table rows={d.cost.findings} columns={[
            { key: "kind", label: "Finding", render: (r) => r.kind.replace(/_/g, " ") },
            { key: "resource", label: "What" },
            { key: "monthly_aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.monthly_aud_cents) },
            { key: "action", label: "Action", wrap: true },
          ]} />
        </Section>

        <Section n="8" title="AI routes not approved">
          <Table rows={d.ai} columns={[
            { key: "entry", label: "Route", render: (r) => <span>{r.entry} <Badge tone="critical">Not approved</Badge></span> },
            { key: "users", label: "People or tools", align: "right" },
            { key: "tools", label: "Tools", wrap: true, render: (r) => r.tools || "-" },
          ]} />
        </Section>
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>Synthetic data. A real report would be exported to the CAB's own format; the structure is the point.</p>
    </>
  );
}
