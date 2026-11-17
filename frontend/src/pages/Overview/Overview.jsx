// The front door: what is here, why, and where to start.

import { Link } from "react-router-dom";
import { Activity, Bot, FileText, GitPullRequest, ShieldCheck, TableProperties, Wallet } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { audWhole } from "../../lib/place.jsx";
import { Badge, Button, Callout, Card, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat } from "../../lib/ui.jsx";

function Step({ icon: Icon, title, to, days, ask, children }) {
  const { t } = useTheme();
  return (
    <Card>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 6 }}>
        <span style={{ background: t.accentGlow, color: t.accent, borderRadius: 10, padding: 8, display: "flex" }}><Icon size={18} /></span>
        <div>
          <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: t.textMuted }}>{days}</div>
          <Link to={to} style={{ fontSize: 15.5, fontWeight: 750, color: t.text }}>{title}</Link>
        </div>
      </div>
      <p style={{ fontSize: 12, color: t.textMuted, fontStyle: "italic", margin: "0 0 8px" }}>"{ask}"</p>
      <div style={{ fontSize: 13, lineHeight: 1.55 }}>{children}</div>
      <div style={{ marginTop: 10 }}><Link to={to}><Button>Open {title.toLowerCase()}</Button></Link></div>
    </Card>
  );
}

export default function Overview() {
  const { t } = useTheme();
  const { data: d, error } = useApi("/api/overview");
  if (error) return <ErrorNote error={error} />;
  if (!d) return <><PageHeader title="Overview" /><Loading /></>;
  const refused = d.gate.refuse || 0;
  const agent = d.agent?.agent;
  return (
    <>
      <PageHeader
        title="Good ideas into secure, supported tools: the first ninety days, working"
        brief="Lead an AI-native engineering system ... so good ideas become secure, supported production tools"
        subtitle="Staff have built useful tools with Claude and Copilot Studio, on Supabase, Firebase, Netlify and personal GitHub. This is the platform a lead would stand up to bring them in without stopping anyone building: find every tool and who owns it, gate what reaches production, govern each change through CAB, then watch, triage and cost what runs. Every number comes from the data, and the data is synthetic."
      />
      <Callout tone="neutral" title="What this is">
        Built with Claude Code for an application to Place Estate Agents, and named for it. Not affiliated with or endorsed by Place; the tools,
        people, code, bills and alerts are invented, of the kinds the advertisement describes. Nothing here claims to know Place's tools, vendors or
        numbers - finding those out is what days 1 to 30 are for.
      </Callout>
      <Grid cols={4} min={190}>
        <Stat label="Tools found" value={fmtInt(d.tools)} emphasis sub={`${d.tools - d.declared} that nobody declared in the survey`} />
        <Stat label="Refused by the production gate" value={fmtInt(refused)} tone={refused ? "critical" : undefined}
          sub={`${fmtInt(d.personal_records_refused)} personal records in them; ${d.gate.hold || 0} more held`} />
        <Stat label="Alerts to pages" value={`${fmtInt(d.alerts)} to ${d.pages}`} sub={`${d.incidents_paged} of ${d.incidents} real incidents still paged`} />
        <Stat label="Cloud and AI spend last month" value={audWhole(d.monthly_cost)} sub={`${audWhole(d.removable)} a month removable now`} />
      </Grid>

      <SectionTitle>The work, in the order the advertisement gives it</SectionTitle>
      <Grid cols={3} min={300}>
        <Step icon={TableProperties} title="Tool register" to="/register" days="Days 1 to 30"
          ask="Inventory the tools staff have built, where they run and who owns them">
          {d.tools} tools joined from ten exports by the keys they share, never by name. {d.critical_flags} critical flags: owners who
          have left, DNS names pointing at nothing. {d.holds} things the evidence cannot decide are held for a person.
        </Step>
        <Step icon={ShieldCheck} title="Production gate" to="/gate" days="Days 31 to 60"
          ask="Guardrails ... so AI-generated code or commands cannot put vulnerabilities into production">
          Eleven checks aimed at what AI-written pilot code gets wrong, each priced by switching it off. A refusal blocks; a hold waits
          for a person. Fix a tool and watch the gate re-scan the code.
        </Step>
        <Step icon={GitPullRequest} title="Changes" to="/changes" days="Days 31 to 60"
          ask="Set up one Place GitHub organisation and move tools into it">
          Migrate, release, merge, retire, transfer: proposed with evidence the server attaches, decided by a CAB member who did not
          propose it, refused when the gate says no. {d.refusals} refusals in the audit log so far.
        </Step>
        <Step icon={Activity} title="Monitoring" to="/monitoring" days="Days 61 to 90"
          ask="Cut alert noise and speed up incident response for Place-built apps">
          Four weeks of alerts through six noise rules: {fmtInt(d.alerts)} alerts became {d.pages} pages, and every real incident still paged.
          Every alternative tried is kept with what it would have missed.
        </Step>
        <Step icon={Bot} title="Incident triage" to="/triage" days="Days 61 to 90"
          ask="Log summarisation agents to cut alert noise and speed up incident response">
          An agent that investigates a page with six read-only tools over masked logs and proposes a fix, graded against the runbook on
          real, hard and adversarial cases. {agent ? <>Graded: <b>{agent.passed} of {agent.cases}</b>.</> : "Not yet graded on this deployment."}
        </Step>
        <Step icon={Wallet} title="Cloud cost" to="/cost" days="Days 61 to 90"
          ask="Audit billing, track resource drift and reduce cloud spend">
          Bills from five platforms and the expense claims that pay them, matched; idle, oversized, duplicated and drifted resources; and
          the tools billed to a leaver's card.
        </Step>
      </Grid>
      <div style={{ marginTop: 14 }}>
        <Card title={<span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}><FileText size={16} /> CAB report</span>}
          hint="The fortnightly report, assembled from the data on request: decisions wanted, changes made, refusals, risks due, cost.">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <Link to="/cab-report"><Button>Open the CAB report</Button></Link>
            {Object.entries(d.changes).map(([k, v]) => <Badge key={k} tone="neutral">{v} {k}</Badge>)}
          </div>
        </Card>
      </div>

      <SectionTitle>Built the way the platform would be run</SectionTitle>
      <Grid cols={3} min={260}>
        <Card title="The build checks itself">
          <p style={{ fontSize: 13, marginTop: 0 }}>The data is generated from a seed with integer arithmetic, then these must hold or there is no image:</p>
          <ul style={{ fontSize: 12.5, paddingLeft: 18, margin: 0, lineHeight: 1.55 }}>{d.acceptance.map((a) => <li key={a}>{a}</li>)}</ul>
        </Card>
        <Card title="Every write is governed">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            Proposals, decisions, fixes and key rotations are audit-logged and refused - not warned - when a rule says no. Nobody decides
            their own change, only the platform lead implements, and an approved change is checked again when it is implemented.
          </p>
        </Card>
        <Card title="The gate runs on this repository too">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            The same checks run in this demo's own CI, with each exemption listed and reasoned in the repository (the generator that writes the
            seeded defects is one). The <Link to="/paved-road" style={{ color: t.accent, fontWeight: 650 }}>paved road</Link> puts them in every tool's CI.
          </p>
        </Card>
      </Grid>
      <p style={{ fontSize: 12, color: t.textMuted, marginTop: 16 }}>
        An open demo: pick who you are acting as at the top, then propose, decide, fix or implement. The rules still refuse what they should - try
        approving your own change - and each refusal is in the audit log. Changes go back to the built data whenever the site has been idle.
      </p>
    </>
  );
}
