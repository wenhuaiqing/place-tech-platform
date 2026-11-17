// Days 31 to 60: changes to the estate, governed the way CAB would.

import { useState } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { actorName } from "../../config.js";
import { apiWrite, fmtDate, fmtDateTime, useApi } from "../../lib/api.js";
import { Choice, Field, FormGrid, Input, useToast } from "../../lib/kit.jsx";
import { ChangeBadge, NotBuilt, OutcomeBadge, aud } from "../../lib/place.jsx";
import { Badge, Button, CTAButton, Callout, Card, ErrorNote, Grid, KeyValues, Loading, PageHeader, SectionTitle, Table } from "../../lib/ui.jsx";

function Propose({ data, onDone }) {
  const toast = useToast();
  const [form, setForm] = useState({ tool_id: data.tools[0]?.tool_id, kind: "migrate", target: "", reason: "" });
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async () => {
    try {
      const out = await apiWrite("/api/changes", { ...form, target: form.target || null });
      toast?.(`${out.cr_id} proposed: ${out.title}`, { tone: "good" });
      setForm((f) => ({ ...f, reason: "" }));
      onDone();
    } catch (e) {
      toast?.(`Refused: ${e.message}`, { tone: "critical", ms: 9000 });
    }
  };
  return (
    <Card title="Propose a change" hint={`As ${actorName()}. The server attaches the evidence: the gate's result, the register entry, users and cost.`}>
      <FormGrid min={220}>
        <Field label="Tool"><Choice label="Tool" value={form.tool_id} onChange={set("tool_id")} options={data.tools.map((x) => ({ value: x.tool_id, label: `${x.name} (${x.tool_id})` }))} /></Field>
        <Field label="Change"><Choice label="Change" value={form.kind} onChange={set("kind")} options={Object.entries(data.kinds).map(([k, v]) => ({ value: k, label: v }))} /></Field>
        {form.kind === "merge" && (
          <Field label="Merge into"><Choice label="Merge into" value={form.target} onChange={set("target")} options={[{ value: "", label: "Choose a tool" }, ...data.tools.map((x) => ({ value: x.tool_id, label: x.name }))]} /></Field>
        )}
        {form.kind === "transfer_owner" && (
          <Field label="New owner"><Choice label="New owner" value={form.target} onChange={set("target")} options={[{ value: "", label: "Choose a person" }, ...data.staff.map((s) => ({ value: s.upn, label: `${s.display_name}, ${s.role}` }))]} /></Field>
        )}
      </FormGrid>
      <div style={{ marginTop: 10 }}>
        <Field label="Why" hint="CAB decides on the reason as well as the evidence.">
          <Input label="Why" value={form.reason} onChange={set("reason")} placeholder="One sentence" />
        </Field>
      </div>
      <div style={{ marginTop: 10 }}><CTAButton onClick={submit}>Propose</CTAButton></div>
    </Card>
  );
}

function ChangeCard({ c, onDone }) {
  const { t } = useTheme();
  const toast = useToast();
  const [note, setNote] = useState("");
  const ev = c.evidence || {};
  const go = async (path, body, done) => {
    try {
      await apiWrite(path, body);
      toast?.(done, { tone: "good" });
      setNote("");
      onDone();
    } catch (e) {
      toast?.(`Refused: ${e.message}`, { tone: "critical", ms: 9000 });
      onDone();
    }
  };
  return (
    <Card title={<span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>{c.cr_id} <ChangeBadge status={c.status} /></span>}
      hint={c.title}>
      <p style={{ fontSize: 13, margin: "0 0 8px" }}>"{c.reason}" - {c.proposed_by}, {fmtDate(c.proposed_at)}</p>
      <KeyValues columns={3} items={[
        ["Gate", <OutcomeBadge key="g" outcome={ev.gate} />],
        ["Users", ev.users_30d],
        ["Data", ev.data_classes],
        ["Owner", `${ev.owner || "Unknown"}${ev.owner_status === "left" ? " (left)" : ""}`],
        ["Cost a month", aud(ev.monthly_cost_aud_cents)],
        ["Tier", ev.tier],
      ]} />
      <p style={{ fontSize: 12.5, color: t.textMuted, margin: "10px 0" }}><b>Preview:</b> {ev.preview}</p>
      {c.decided_by && <p style={{ fontSize: 12.5, margin: "0 0 8px" }}><b>{c.status === "rejected" ? "Rejected" : "Approved"}</b> by {c.decided_by}, {fmtDate(c.decided_at)}: "{c.decision_note}"</p>}
      {c.implemented_by && <p style={{ fontSize: 12.5, margin: "0 0 8px" }}><b>Implemented</b> by {c.implemented_by}, {fmtDate(c.implemented_at)}.</p>}
      {c.status === "submitted" && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "1 1 220px" }}><Input label={`Decision note for ${c.cr_id}`} value={note} onChange={setNote} placeholder="The reason for the decision" /></div>
          <Button title={`Approve ${c.cr_id}`} onClick={() => go(`/api/changes/${c.cr_id}/decide`, { approve: true, note }, `${c.cr_id} approved.`)}>Approve</Button>
          <Button title={`Reject ${c.cr_id}`} onClick={() => go(`/api/changes/${c.cr_id}/decide`, { approve: false, note }, `${c.cr_id} rejected.`)}>Reject</Button>
        </div>
      )}
      {c.status === "approved" && <CTAButton title={`Implement ${c.cr_id}`} onClick={() => go(`/api/changes/${c.cr_id}/implement`, {}, `${c.cr_id} implemented.`)}>Implement</CTAButton>}
    </Card>
  );
}

export default function Changes() {
  const { t } = useTheme();
  const { data, error, reload } = useApi("/api/changes");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Changes" /><Loading /></>;
  const open = data.changes.filter((c) => ["submitted", "approved"].includes(c.status));
  const closed = data.changes.filter((c) => !["submitted", "approved"].includes(c.status));
  return (
    <>
      <PageHeader
        title="Changes"
        brief="Days 31 to 60: Set up one Place GitHub organisation and move tools into it. Consolidate pilot platforms"
        subtitle="Every move - into the Place GitHub organisation, onto the Place platform, a merge, a retirement, a new owner - is a change CAB decides. The server attaches the evidence, a CAB member who did not propose it decides, and the platform lead implements, with every rule checked again at that moment."
      />
      <Callout tone="neutral" title="The rules, enforced on the server">
        Only a CAB member decides, and never their own proposal. A release needs the tool in the Place GitHub organisation and the gate to pass - the
        gate decides, not the vote. A tool moves only with a current owner. A tool with users cannot be retired, only merged. An approved change is
        checked again when it is implemented. Each refusal is recorded below with its reason. You are acting as <b>{actorName()}</b>; change it at the top.
      </Callout>
      <Grid cols={2} min={340}>
        <Propose data={data} onDone={reload} />
        <Card title="Who does what" hint="Roles, not people. In production they come from Entra ID groups.">
          <KeyValues columns={1} items={[
            ["Propose", "Anyone: builders, the platform lead, CAB members"],
            ["Decide", data.cab.join(", ")],
            ["Implement", data.implementers.join(", ")],
          ]} />
        </Card>
      </Grid>
      <SectionTitle>Open ({open.length})</SectionTitle>
      <Grid cols={2} min={340}>{open.map((c) => <ChangeCard key={c.cr_id} c={c} onDone={reload} />)}</Grid>
      <SectionTitle>Decided ({closed.length})</SectionTitle>
      <Grid cols={2} min={340}>{closed.map((c) => <ChangeCard key={c.cr_id} c={c} onDone={reload} />)}</Grid>
      <SectionTitle>Audit log: changes and gate</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={420} rows={data.audit} columns={[
          { key: "ts", label: "When", render: (r) => fmtDateTime(r.ts, { seconds: false }) },
          { key: "actor", label: "Who" },
          { key: "project_id", label: "Change", render: (r) => r.project_id || "-" },
          { key: "action", label: "Did" },
          { key: "outcome", label: "Outcome", render: (r) => r.outcome === "refused" ? <Badge tone="critical">Refused</Badge> : <Badge tone="neutral">Recorded</Badge> },
          { key: "detail", label: "Detail", wrap: true },
        ]} />
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>Times are Brisbane time (AEST).</p>
      <NotBuilt items={[
        "The migration itself: transferring a repository into the organisation, re-pointing DNS, moving data out of Supabase or Firebase. Implementing a change here records it; the runbook for each kind is the real work.",
        "Identity. The acting-as picker stands in for Entra ID; the separation-of-duties rules are the same either way.",
      ]} />
    </>
  );
}
