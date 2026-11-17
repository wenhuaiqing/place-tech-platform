// The advertisement's own list, mapped to where each point is shown working,
// then the first ninety days - as a plan that starts by listening.

import { Link } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { DISCLAIMER } from "../../config.js";
import { Callout, Card, Grid, PageHeader, SectionTitle, Table } from "../../lib/ui.jsx";

const ASKED = [
  ["AI agent and workflow orchestration: integrate agentic tools ... into the software lifecycle. Help staff move useful tools into Place's GitHub with proper back ends and credentials.",
   "The paved road every tool moves onto: the gate in CI, dependency review, CodeQL, CODEOWNERS, a branch ruleset, a register entry and a Terraform module. Each refusal is a sentence Claude Code can act on. This demo was built with Claude Code.",
   [["Paved road", "/paved-road"], ["Changes", "/changes"]]],
  ["Policy and governance: guardrails, security checks, code review and data compliance ... keep the app and AI tool register current, and report to CAB.",
   "Eleven checks over every tool's code and history, refused or held, each priced by ablation; a register of every tool and every AI route, from the evidence; changes decided by CAB with separation of duties enforced; a CAB report assembled from the data.",
   [["Production gate", "/gate"], ["AI register", "/ai-register"], ["CAB report", "/cab-report"]]],
  ["Incident triage and predictive SRE: monitoring and log summarisation agents to cut alert noise and speed up incident response.",
   "Six noise rules take four weeks of alerts to a handful of pages with every incident still paged, and the rejected settings are kept with what they would have missed. A triage agent over masked snapshots, graded against the runbook on hard and adversarial cases. Straight-line forecasts for limits and certificates.",
   [["Monitoring", "/monitoring"], ["Incident triage", "/triage"]]],
  ["Cloud cost optimisation: audit billing, track resource drift and reduce cloud spend, consolidating hosting platforms over time.",
   "Five platforms' bills and the expense claims that pay them, matched and attributed to tools; idle, oversized, duplicate and drifted resources; tools billed to a leaver's card; a labelled planning figure for the consolidated platform.",
   [["Cloud cost", "/cost"]]],
  ["Owns admin access and security ownership for the new platforms (Azure sandbox, GitHub, Supabase).",
   "Only the platform lead implements changes and records key rotations; the Azure sandbox is checked against Terraform for anything made by hand.",
   [["Changes", "/changes"], ["Cloud cost - drift", "/cost"]]],
  ["Days 1 to 30: Inventory the tools staff have built, where they run and who owns them.",
   "Ten exports joined by the keys they share, never by name; owners who have left, tools nobody declared, DNS names that point at nothing; what the evidence cannot decide is held for a person.",
   [["Tool register", "/register"], ["How it was found", "/discovery"]]],
  ["Solid security basics, including secrets management and what AI-written code tends to get wrong.",
   "A key removed from the code still refuses until it is rotated, because it is in the history. A service-role key in the browser, rules opened during testing, SQL from input, a package name a model invented.",
   [["Production gate", "/gate?tool=T-030"]]],
  ["Clear plain English with non-technical staff, executives and vendors.",
   "Every refusal says what to do next in one sentence. The CAB report puts decisions first.",
   [["CAB report", "/cab-report"]]],
];

const PLAN = [
  {
    when: "Days 1 to 30: listen, then count",
    items: [
      "Fifteen minutes with each person who has built something: what it does, who uses it, what would happen if it stopped tomorrow. The survey is the conversation, not a form.",
      "Meet Productivity and agree what they own and what the platform owns: identity, licensing and Microsoft 365 stay theirs.",
      "Ask each platform for the exports this demo starts from, and build the register. First fixes are the ones that are dangerous today: a live key in a public repository, personal data readable by anyone.",
      "Meet NetEngine, Wingman, WMX and PPG to learn how their systems connect to staff-built tools, before changing anything near them.",
    ],
  },
  {
    when: "Days 31 to 60: bring it in",
    items: [
      "One Place GitHub organisation with the paved road, secret scanning and push protection on. Move the most-used tool with no personal data first, so the road is proven on something safe.",
      "Give every orphaned tool a current owner before it moves. Retire what nobody uses, with CAB's agreement.",
      "Stand up the Azure sandbox from Terraform, so drift is visible from day one.",
      "Fix and migrate the tier 1 tools one at a time, with their builders, not for them.",
    ],
  },
  {
    when: "Days 61 to 90: run it, and report",
    items: [
      "Agree the platform standard and the AI guardrails with CAB: the tiers, the gate's refuse and hold lists, the approved AI routes.",
      "Monitoring and the noise rules on everything that has moved; a triage agent graded on Place's own incidents before anyone relies on it.",
      "Cost reporting by tool, with nothing on a personal card.",
      "The first CAB report: decisions wanted, what changed, what the rules refused, what is due.",
    ],
  },
];

export default function FirstDays() {
  const { t } = useTheme();
  return (
    <>
      <PageHeader
        title="First 90 days"
        brief="Your first 90 days"
        subtitle="The advertisement's own list, mapped to where each point is shown working here. Then a plan for the first ninety days that starts with the people who built the tools - because the right first move is the one they need, and a demo cannot know that."
      />
      <Callout tone="neutral" title="What this is and is not">
        {DISCLAIMER} The logo and colours are Place's own public ones, used to show the work in Place's context. Nothing here claims to know
        Place's tools, vendors, policies or numbers: the 26 offices and 700 staff are from the advertisement, and everything else is invented.
      </Callout>
      <SectionTitle>What the role asks for, and where it is shown</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={1200} rows={ASKED} columns={[
          { key: 0, label: "From the advertisement", wrap: true, render: (r) => <i style={{ color: t.textMuted }}>"{r[0]}"</i> },
          { key: 1, label: "Here", wrap: true, render: (r) => r[1] },
          { key: 2, label: "Open", render: (r) => (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {r[2].map(([label, to]) => <Link key={label} to={to} style={{ color: t.accent, fontWeight: 650, fontSize: 12.5 }}>{label}</Link>)}
            </div>
          ) },
        ]} />
      </Card>
      <SectionTitle>The first ninety days</SectionTitle>
      <Grid cols={3} min={280}>
        {PLAN.map((p) => (
          <Card key={p.when} title={p.when}>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6 }}>{p.items.map((i) => <li key={i} style={{ marginBottom: 6 }}>{i}</li>)}</ul>
          </Card>
        ))}
      </Grid>
      <SectionTitle>Questions I would ask first</SectionTitle>
      <Card>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
          <li>Which staff-built tool would hurt most if it stopped on a Saturday morning, and who would notice first?</li>
          <li>Where does the AI Governance Policy stand today, and which data may go to which model?</li>
          <li>What does Productivity administer in Copilot Studio and Entra, and what would they want the platform to own?</li>
          <li>Which of the vendors' systems do staff-built tools read from or write to?</li>
          <li>How does CAB like to receive a change: a form, a meeting, a report?</li>
        </ul>
      </Card>
    </>
  );
}
