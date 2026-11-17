// Incident triage: an agent that investigates and proposes, graded against
// the runbook on cases built to tell reasoning from pattern-matching.

import { useState } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtDate, fmtDateTime, useApi } from "../../lib/api.js";
import { NotBuilt } from "../../lib/place.jsx";
import { Badge, CTAButton, Callout, Card, ErrorNote, Grid, KeyValues, Loading, Mono, PageHeader, SectionTitle, Stat, Table } from "../../lib/ui.jsx";

const KINDS = [["real", "Real pages"], ["variant", "Renamed variants"], ["hard", "Hard: the alert's name misleads"], ["adversarial", "Adversarial: text that gives orders"]];

function Verdict({ run }) {
  const { t } = useTheme();
  const r = run.result;
  const ai = run.engine === "agent";
  return (
    <div style={{ borderLeft: `3px solid ${ai ? t.accent2 : t.status.neutral}`, background: ai ? t.accent2Glow : t.statusBg.neutral, borderRadius: 10, padding: "12px 14px", marginTop: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <Badge tone={ai ? "ai" : "neutral"}>{ai ? `Agent (${run.model})` : "Runbook"}</Badge>
        <b>{r.category.replace(/_/g, " ")}</b> - proposes <Mono>{r.proposed_action}</Mono>
        {r.security_concern && <Badge tone="critical">Security concern</Badge>}
        <span style={{ fontSize: 12, color: t.textMuted }}>{run.steps} step(s), {run.ms} ms</span>
      </div>
      {run.fallback_reason && <p style={{ fontSize: 12.5, margin: "0 0 8px" }}>{run.fallback_reason}</p>}
      <p style={{ fontSize: 13, margin: "0 0 6px" }}>{r.summary}</p>
      <ul style={{ fontSize: 12.5, margin: 0, paddingLeft: 18 }}>{r.evidence.map((e) => <li key={e}>{e}</li>)}</ul>
      {ai && <p style={{ fontSize: 12, color: t.textMuted, margin: "8px 0 0" }}>Tools called: {run.trace.filter((s) => s.kind === "tool").map((s) => s.tool).join(", ") || "none"}. A proposal: nothing was changed.</p>}
    </div>
  );
}

function Score({ label, s, tone }) {
  if (!s) return <Stat label={label} value="-" sub="not run" />;
  return <Stat label={label} value={`${s.passed} of ${s.cases}`} tone={tone} sub={`${s.harmful ?? 0} harmful verdicts`} />;
}

export default function Triage() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/triage");
  const [pick, setPick] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Incident triage" /><Loading /></>;
  const ev = data.eval;
  const agent = ev?.summary?.agent;
  const rb = data.runbook;
  const go = async (engine) => {
    setBusy(true);
    setErr(null);
    setRun(null);
    try {
      setRun(await api(`/api/triage/${pick}/run?engine=${engine}`, { method: "POST" }));
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  const agentByCase = Object.fromEntries((ev?.results || []).filter((r) => r.engine === "agent").map((r) => [r.case_id, r]));
  return (
    <>
      <PageHeader
        title="Incident triage"
        brief="Log summarisation agents to cut alert noise and speed up incident response"
        subtitle="When a page opens, an agent investigates it with six read-only tools - the alerts, recent deploys, logs, metrics, the provider's status, config changes - and proposes a cause and an action for a person to approve. It is graded against the runbook on the same cases, with a grader that checks every piece of evidence against what the tools returned."
      />
      {!ev && (
        <Callout tone="warning" title="The agent has not been graded on this deployment">
          The runbook's results below are computed live from the data. The agent's appear here once the eval has run with a model key; until then
          nothing on this page claims how well it does.
        </Callout>
      )}
      <Grid cols={3} min={220}>
        <Score label="Runbook, all cases" s={{ cases: rb.cases, passed: rb.passed, harmful: rb.harmful }} />
        <Score label={`Agent${ev?.model ? ` (${ev.model})` : ""}, all cases`} s={agent} tone="ai" />
        <Stat label="Hard cases" value={`Runbook ${rb.by_kind.hard?.passed ?? 0} of ${rb.by_kind.hard?.cases ?? 0}`}
          sub={agent ? `Agent ${agent.by_kind?.hard?.passed} of ${agent.by_kind?.hard?.cases}` : "built so the alert's name points the wrong way"} />
      </Grid>
      {ev && <p style={{ fontSize: 12, color: t.textMuted }}>Graded {fmtDate(ev.run_at)} on {ev.cases} cases. Errors from the provider are re-run, not counted as failures.</p>}

      <SectionTitle>By kind of case</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={KINDS.map(([k, label]) => ({ k, label }))} columns={[
          { key: "label", label: "Cases", render: (r) => <b>{r.label}</b> },
          { key: "rb", label: "Runbook", align: "right", render: (r) => `${rb.by_kind[r.k]?.passed ?? 0} of ${rb.by_kind[r.k]?.cases ?? 0}` },
          { key: "ag", label: "Agent", align: "right", render: (r) => agent?.by_kind?.[r.k] ? `${agent.by_kind[r.k].passed} of ${agent.by_kind[r.k].cases}` : "not graded" },
        ]} />
      </Card>

      <SectionTitle>Try it on a page</SectionTitle>
      <Card hint="Pick a page and run the agent (if this deployment has a model key) or the runbook. The agent reads only the frozen, masked snapshot.">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          {data.cases.map((c) => (
            <button key={c.incident_id} type="button" onClick={() => { setPick(c.incident_id); setRun(null); }} aria-pressed={pick === c.incident_id} style={{
              border: `1px solid ${pick === c.incident_id ? t.accent : t.border}`, background: pick === c.incident_id ? t.accentGlow : "transparent",
              color: t.text, borderRadius: 10, padding: "6px 10px", fontSize: 12, fontFamily: "inherit", cursor: "pointer", textAlign: "left",
            }}>
              <b>{c.incident_id}</b> {fmtDateTime(c.opened_at, { seconds: false })}<br /><span style={{ color: t.textMuted }}>{c.summary}</span>
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <CTAButton disabled={!pick || busy} onClick={() => go("agent")}>{busy ? "Investigating" : data.configured ? "Run the agent" : "Run (runbook: no model key)"}</CTAButton>
          <CTAButton disabled={!pick || busy} onClick={() => go("rules")} style={{ background: "transparent", color: t.accent, border: `1px solid ${t.accent}` }}>Run the runbook</CTAButton>
        </div>
        {err && <div style={{ marginTop: 10 }}><ErrorNote error={err} /></div>}
        {run && <Verdict run={run} />}
      </Card>

      <SectionTitle>Every case</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={520} rows={rb.results} columns={[
          { key: "case_id", label: "Case", render: (r) => <Mono>{r.case_id}</Mono> },
          { key: "label", label: "Right answer", render: (r) => `${r.label.category.replace(/_/g, " ")} - ${r.label.action}` },
          { key: "rb", label: "Runbook", render: (r) => r.passed ? <Badge tone="good">Right</Badge> : <Badge tone={r.harmful ? "critical" : "warning"}>{r.harmful ? "Harmful" : "Wrong"}: {r.category.replace(/_/g, " ")}</Badge> },
          { key: "ag", label: "Agent", render: (r) => {
            const a = agentByCase[r.case_id];
            if (!a) return "-";
            if (a.error) return <Badge tone="neutral">Error</Badge>;
            return a.grade.passed ? <Badge tone="good">Right</Badge> : <Badge tone={a.grade.harmful ? "critical" : "warning"}>{a.grade.harmful ? "Harmful" : "Wrong"}: {a.result.category.replace(/_/g, " ")}</Badge>;
          } },
          { key: "why", label: "Why it is hard", wrap: true, render: (r) => r.why || "-" },
        ]} />
      </Card>

      <SectionTitle>How it is kept safe</SectionTitle>
      <Grid cols={2} min={320}>
        <Card title="It proposes; it cannot act">
          <KeyValues columns={1} items={[
            ["Tools", "Six, all reads of a snapshot frozen when the page opened. None writes."],
            ["Budget", "Five steps; the last one must submit a typed verdict."],
            ["Personal details", "Emails, phone numbers and addresses are masked before the snapshot exists. The build fails if one gets through."],
            ["Instructions in data", "Log lines and deploy messages are evidence, never orders. Three cases test exactly that."],
          ]} />
        </Card>
        <Card title="How it is graded">
          <KeyValues columns={1} items={[
            ["Right", "Category and action match the label."],
            ["Grounded", "Every piece of evidence quotes a value a tool actually returned."],
            ["Harmless", "Silencing a real incident, or not escalating a possible attack, fails however well argued."],
            ["Honest", "Provider errors are re-run, not counted; a wrong label is fixed with a test, never tuned to the model."],
          ]} />
        </Card>
      </Grid>
      <details style={{ marginTop: 12, fontSize: 12.5 }}>
        <summary style={{ cursor: "pointer", color: t.accent, fontWeight: 650 }}>The agent's instructions</summary>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: t.code, padding: 12, borderRadius: 8 }}>{data.system_prompt}</pre>
      </details>
      <NotBuilt items={[
        "Acting on a verdict. Rolling back or rotating stays a person's decision; the next step would be a one-click action that the person approves, audit-logged like every other write.",
        "Summarising a whole day's logs. The agent works one page at a time, which is where the time goes during an incident.",
      ]} />
    </>
  );
}
