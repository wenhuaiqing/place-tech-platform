// Maintenance work orders: the one place this site writes, and every rule
// on that write enforced by the server and recorded.

import { useState } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { actorName, setActorName } from "../../config.js";
import { apiWrite, fmtDate, fmtDateTime, useApi } from "../../lib/api.js";
import { Choice, Field, FormGrid, Input, useToast } from "../../lib/kit.jsx";
import { Assumption, NotBuilt, dollars } from "../../lib/place.jsx";
import { Badge, Button, CTAButton, Callout, Card, ErrorNote, Grid, Loading, Mono, PageHeader, SectionTitle, Select, Table } from "../../lib/ui.jsx";

const STATUS = { "awaiting approval": "warning", approved: "good", rejected: "critical", completed: "neutral" };

function cents(text) {
  const n = Number(String(text).replace(/[$,\s]/g, ""));
  return Number.isFinite(n) && n > 0 ? Math.round(n * 100) : 0;
}

function ActingAs({ people }) {
  const [who, setWho] = useState(actorName());
  return (
    <Select label="Acting as" value={who} options={people} onChange={(v) => { setActorName(v); setWho(v); window.location.reload(); }} />
  );
}

function Raise({ data, onDone }) {
  const toast = useToast();
  const [f, setF] = useState({ tenancy_id: data.tenancies[0]?.tenancy_id || "", category: data.categories[0], priority: "routine", description: "", quote: "" });
  const set = (k) => (v) => setF((x) => ({ ...x, [k]: v }));
  const submit = async () => {
    try {
      const out = await apiWrite("/api/work-orders", { tenancy_id: f.tenancy_id, category: f.category, priority: f.priority,
        description: f.description, quote_cents: cents(f.quote) });
      toast?.(`${out.wo_id} raised: ${out.status}.`, { tone: "good" });
      setF((x) => ({ ...x, description: "", quote: "" }));
      onDone();
    } catch (e) {
      toast?.(`Refused: ${e.message}`, { tone: "critical", ms: 9000 });
      onDone();
    }
  };
  return (
    <Card title="Raise a work order" hint={`As ${actorName()}, against a current tenancy in Office ${data.rules.office}.`}>
      <FormGrid min={180}>
        <Field label="Tenancy" hint={`Try ${data.ended_example}: it has ended.`}>
          <Input label="Tenancy" value={f.tenancy_id} onChange={set("tenancy_id")} list="tenancies" />
          <datalist id="tenancies">{data.tenancies.map((t) => <option key={t.tenancy_id} value={t.tenancy_id} />)}</datalist>
        </Field>
        <Field label="Category"><Choice label="Category" value={f.category} onChange={set("category")} options={data.categories} /></Field>
        <Field label="Priority"><Choice label="Priority" value={f.priority} onChange={set("priority")} options={["routine", "urgent"]} /></Field>
        <Field label="Quote (A$)"><Input label="Quote" value={f.quote} onChange={set("quote")} placeholder="e.g. 640" /></Field>
      </FormGrid>
      <div style={{ marginTop: 10 }}>
        <Field label="The job"><Input label="The job" value={f.description} onChange={set("description")} placeholder="What needs doing, in a sentence" /></Field>
      </div>
      <div style={{ marginTop: 10 }}><CTAButton onClick={submit}>Raise</CTAButton></div>
    </Card>
  );
}

function OrderCard({ o, onDone }) {
  const { t } = useTheme();
  const toast = useToast();
  const [note, setNote] = useState("");
  const [cost, setCost] = useState("");
  const go = async (path, body, done) => {
    try {
      await apiWrite(path, body);
      toast?.(done, { tone: "good" });
      setNote("");
      setCost("");
    } catch (e) {
      toast?.(`Refused: ${e.message}`, { tone: "critical", ms: 9000 });
    }
    onDone();
  };
  return (
    <Card title={<span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>{o.wo_id} <Badge tone={STATUS[o.status]}>{o.status}</Badge>
      {o.priority === "urgent" && <Badge tone="serious">urgent</Badge>}</span>}
      hint={`${o.category} - tenancy ${o.tenancy_id} - quote ${dollars(o.quote_cents / 100, { decimals: 2 })}`}>
      <p style={{ fontSize: 13, margin: "0 0 6px" }}>{o.description}</p>
      <p style={{ fontSize: 12, color: t.textMuted, margin: "0 0 8px" }}>Raised by {o.raised_by}, {fmtDate(o.raised_at)}</p>
      {o.decided_by && <p style={{ fontSize: 12.5, margin: "0 0 6px" }}><b>{o.status === "rejected" ? "Rejected" : "Approved"}</b> by {o.decided_by}: "{o.decision_note}"</p>}
      {o.status === "completed" && (
        <p style={{ fontSize: 12.5, margin: "0 0 6px" }}><b>Completed</b> {fmtDate(o.completed_at)} at {dollars(o.completed_cost_cents / 100, { decimals: 2 })}
          {o.completion_note ? `: "${o.completion_note}"` : ""}</p>
      )}
      {o.status === "awaiting approval" && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "1 1 200px" }}><Input label={`Decision note for ${o.wo_id}`} value={note} onChange={setNote} placeholder="The reason for the decision" /></div>
          <Button title={`Approve ${o.wo_id}`} onClick={() => go(`/api/work-orders/${o.wo_id}/decide`, { approve: true, note }, `${o.wo_id} approved.`)}>Approve</Button>
          <Button title={`Reject ${o.wo_id}`} onClick={() => go(`/api/work-orders/${o.wo_id}/decide`, { approve: false, note }, `${o.wo_id} rejected.`)}>Reject</Button>
        </div>
      )}
      {o.status === "approved" && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "0 1 120px" }}><Input label={`Invoiced cost for ${o.wo_id}`} value={cost} onChange={setCost} placeholder="Cost, A$" /></div>
          <div style={{ flex: "1 1 200px" }}><Input label={`Completion note for ${o.wo_id}`} value={note} onChange={setNote} placeholder="Why, if over the quote" /></div>
          <Button title={`Complete ${o.wo_id}`} onClick={() => go(`/api/work-orders/${o.wo_id}/complete`, { cost_cents: cents(cost), note }, `${o.wo_id} completed.`)}>Complete</Button>
        </div>
      )}
    </Card>
  );
}

export default function WorkOrders() {
  const { t } = useTheme();
  const { data, error, reload } = useApi("/api/work-orders");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Work orders" /><Loading /></>;
  const r = data.rules;
  const open = data.orders.filter((o) => ["awaiting approval", "approved"].includes(o.status));
  const closed = data.orders.filter((o) => !["awaiting approval", "approved"].includes(o.status));
  return (
    <>
      <PageHeader
        title="Maintenance work orders"
        brief="Run guardrails, security checks, code review and data compliance so AI-generated code or commands cannot put vulnerabilities into production"
        subtitle={`The one place this site writes. A property manager raises a work order with a quote; someone else decides it; it is completed against the invoice. Every rule is enforced by the server, not the screen, and every step - refusals included - is in the audit log below. Try it: pick who you are acting as, then try approving your own work order.`}
        right={<ActingAs people={data.people} />}
      />
      <Callout tone="neutral" title="The rules">
        At or under {dollars(r.auto_limit_cents / 100)}: approved within the agreed limit, and recorded. Over it: someone other than the person who raised it
        must decide, with a reason. Over {dollars(r.head_limit_cents / 100)}: only the head of property management may approve. A cost more than {r.variance_pct}%
        over the quote needs a reason before it is paid. A work order against a tenancy that has ended is refused.
      </Callout>
      <Grid cols={2} min={340}>
        <Raise data={data} onDone={reload} />
        <Card title="Why this page exists" hint="A staff-built tool usually has the form. What it needs before production is underneath.">
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6 }}>
            <li>Separation of duties on the server: the button is the same for everyone; the rule decides.</li>
            <li>A refusal is a sentence a person can act on, and it is recorded - who tried what, and why not.</li>
            <li>Each rule is checked again at the moment it applies: a tenancy can end between raising and approving.</li>
            <li>Changes live in a working copy that returns to the build, so a visitor can try anything.</li>
          </ul>
        </Card>
      </Grid>
      <SectionTitle>Open ({open.length})</SectionTitle>
      <Grid cols={2} min={340}>{open.map((o) => <OrderCard key={o.wo_id} o={o} onDone={reload} />)}</Grid>
      <SectionTitle>Closed ({closed.length})</SectionTitle>
      <Grid cols={2} min={340}>{closed.map((o) => <OrderCard key={o.wo_id} o={o} onDone={reload} />)}</Grid>
      <SectionTitle>Audit log</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={data.audit} maxHeight={420} columns={[
          { key: "ts", label: "When", render: (a) => fmtDateTime(a.ts, { seconds: false }) },
          { key: "actor", label: "Who" },
          { key: "project_id", label: "Work order", render: (a) => <Mono>{a.project_id}</Mono> },
          { key: "action", label: "Did" },
          { key: "outcome", label: "Outcome", render: (a) => (a.outcome === "refused" ? <Badge tone="critical">Refused</Badge> : <Badge tone="neutral">Recorded</Badge>) },
          { key: "detail", label: "Detail", wrap: true },
        ]} />
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>Times are Brisbane time (AEST). The demo roles stand in for Entra ID sign-in.</p>
      <Assumption>the approval limits and the {r.variance_pct}% tolerance are invented to show the mechanism; a real agency's come from its management agreements and its owners' instructions.</Assumption>
      <NotBuilt items={[
        "Sending the order to a tradesperson, or the owner's approval by email. Those belong to the property management system; this shows the controls a tool needs before it touches them.",
        "Paying the invoice. Payment is a trust accounting step, with its own controls.",
      ]} />
    </>
  );
}
