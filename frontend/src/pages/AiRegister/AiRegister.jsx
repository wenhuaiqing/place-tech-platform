// The AI tool register: every route to a model in use, from the evidence.

import { Link } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { NotBuilt } from "../../lib/place.jsx";
import { Badge, Callout, Card, ErrorNote, Grid, Loading, Mono, PageHeader, SectionTitle, Stat, Table } from "../../lib/ui.jsx";

export default function AiRegister() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/register/ai");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="AI register" /><Loading /></>;
  const unapproved = data.entries.filter((e) => !e.approved && e.users > 0);
  return (
    <>
      <PageHeader
        title="AI register"
        brief="Put the AI Governance Policy into practice, keep the app and AI tool register current"
        subtitle="Every route to a model that is actually in use, found from the evidence rather than asked about: personal subscriptions on expense claims, model SDKs in each repository's code, and agents in the Copilot Studio export. Each is checked against the policy's approved routes and the data each may carry."
      />
      <Grid cols={3} min={220}>
        <Stat label="Routes in use, not approved" value={fmtInt(unapproved.length)} tone={unapproved.length ? "critical" : "good"}
          sub="personal subscriptions and personal API keys" />
        <Stat label="Tools calling a model on a personal key" value={fmtInt(data.entries.filter((e) => e.route === "called from tool code").reduce((a, e) => a + e.users, 0))}
          sub="found by scanning each repository" />
        <Stat label="Copilot Studio agents" value={fmtInt((data.entries.find((e) => e.entry === "Microsoft Copilot Studio")?.tools || "").split(", ").filter(Boolean).length)}
          sub="inside the tenant: approved, connectors checked by the gate" />
      </Grid>
      <Callout tone="neutral" title="The gateway is an assumption of the design">
        The policy here approves model calls through one AI gateway (<Mono>{data.gateway}</Mono>): one key held by Place, prompts logged with
        personal details masked, spend capped per tool. It is the route the paved road gives every tool. Place's actual AI Governance Policy
        decides the real list; this one is invented to show the mechanism.
      </Callout>
      <SectionTitle>In use</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={520} rows={data.entries} columns={[
          { key: "entry", label: "Route", render: (r) => <b>{r.entry}</b> },
          { key: "approved", label: "Policy", render: (r) => r.approved ? <Badge tone="good">Approved</Badge> : <Badge tone="critical">Not approved</Badge> },
          { key: "users", label: "People or tools", align: "right", render: (r) => fmtInt(r.users) },
          { key: "data_allowed", label: "Data it may carry", wrap: true },
          { key: "tools", label: "Tools", wrap: true, render: (r) => r.tools || "-" },
          { key: "evidence", label: "Evidence", wrap: true },
        ]} />
      </Card>
      <SectionTitle>What happens to an unapproved route</SectionTitle>
      <Grid cols={2} min={320}>
        <Card title="In a tool's code">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            The <Link to="/gate" style={{ color: t.accent, fontWeight: 650 }}>production gate</Link> refuses a tool that sends personal information
            to a model on a personal key, and holds one that sends only public data. The fix branch points the client at the gateway and reads the
            key from the environment.
          </p>
        </Card>
        <Card title="A personal subscription">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            No gate can see a chat window. The answer is a managed plan with admin controls that the policy approves, and the expense claims are
            how to find who needs one. The <Link to="/cost" style={{ color: t.accent, fontWeight: 650 }}>cost page</Link> counts them; no saving is assumed.
          </p>
        </Card>
      </Grid>
      <NotBuilt items={[
        "The gateway itself. In Azure it would be API Management in front of the model providers, with a policy per tool; here it is a hostname the gate recognises.",
        "Microsoft Purview or Defender for Cloud Apps discovery of browser AI use, which would find the subscriptions nobody claims.",
      ]} />
    </>
  );
}
