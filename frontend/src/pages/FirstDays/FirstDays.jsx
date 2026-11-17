// The advertisement's own list, and the first ninety days as a plan that starts by listening.

import { Link } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { DISCLAIMER } from "../../config.js";
import { Callout, Card, Grid, PageHeader, SectionTitle, Table } from "../../lib/ui.jsx";

const ASKED = [
  ["Help staff move useful tools into Place's GitHub with proper back ends and credentials.",
   "This site is one such tool, taken the whole way: one repository, CI, data checks, tests in a browser, secrets on the server, Terraform, monitoring and a budget alert.",
   [["How it is run", "/how-it-is-run"]]],
  ["Run guardrails, security checks, code review and data compliance so AI-generated code or commands cannot put vulnerabilities into production.",
   "The data checks stop bad records reaching a report. The assistant's SQL passes a gate before it runs, and it is graded on questions it must refuse.",
   [["Data checks", "/data-checks"], ["Ask the data", "/ask"]]],
  ["Uses AI coding and agent tools ... daily and can show real work done with them.",
   "Built with Claude Code. An assistant that answers in plain English with the query behind every figure, graded against reference answers.",
   [["Ask the data", "/ask"]]],
  ["Monitoring, observability and cloud cost management.",
   "Health probes, capped logs, a run log for the assistant, scale to zero outside business hours, and a monthly budget alert.",
   [["How it is run", "/how-it-is-run"]]],
  ["Reads and writes code (Python, TypeScript or C#) and works confidently with APIs.",
   "FastAPI and DuckDB behind, React in front, an OpenAI-protocol model client that changes provider by configuration.",
   [["Overview", "/overview"]]],
  ["Clear plain English with non-technical staff, executives and vendors.",
   "Every report says what it counts and what it leaves out, and every assumption is labelled where it is used.",
   [["Rentals", "/rentals"], ["Sales", "/sales"]]],
];

const PLAN = [
  {
    when: "Days 1 to 30: listen, then count",
    items: [
      "Fifteen minutes with each person who has built something: what it does, who uses it, what would happen if it stopped tomorrow.",
      "Inventory the tools from what they say and from the platforms themselves - Supabase, Firebase, Netlify, GitHub, Copilot Studio - with an owner for each.",
      "Meet Productivity and the vendors, and agree who owns what before changing anything near their systems.",
      "Fix what is dangerous today: a key in a public repository, personal data readable by anyone.",
    ],
  },
  {
    when: "Days 31 to 60: bring it in",
    items: [
      "One Place GitHub organisation with branch protection, secret scanning and the checks in CI. Move the most-used tool with no personal data first, so the path is proven on something safe.",
      "Give every tool whose builder has left a current owner. Retire what nobody uses.",
      "Stand up the Azure sandbox from Terraform, so anything made by hand is visible from day one.",
    ],
  },
  {
    when: "Days 61 to 90: run it, and report",
    items: [
      "Agree the platform standard and the AI guardrails with CAB: what every tool needs before production, and which data may go to which model.",
      "Monitoring and cost reporting on everything that has moved, by tool.",
      "The first CAB report: what moved, what was refused and why, what is due.",
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
        subtitle="The advertisement's list, mapped to where each point is shown here. Then a plan for the first ninety days that starts with the people who built the tools - the right first move is the one they need, and a demo cannot know that."
      />
      <Callout tone="neutral" title="What this is and is not">
        {DISCLAIMER} The logo and colours are Place's own public ones, used to show the work in Place's context. Nothing here claims to know Place's
        offices, results, systems or tools: the 26 offices are from the advertisement, and everything else is invented.
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
          <li>Where does the AI Governance Policy stand, and which data may go to which model?</li>
          <li>What do Productivity administer in Entra and Copilot Studio, and what would they want the platform to own?</li>
          <li>Which reports do offices still build by hand each month, and from which systems?</li>
        </ul>
      </Card>
    </>
  );
}
