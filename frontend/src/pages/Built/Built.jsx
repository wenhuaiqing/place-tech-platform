// How this tool is built and run - the path every staff-built tool would take.

import { useTheme } from "../../context/ThemeContext.jsx";
import { useApi } from "../../lib/api.js";
import { Callout, Card, Grid, KeyValues, PageHeader, SectionTitle } from "../../lib/ui.jsx";

const STEPS = [
  ["One repository, reviewed changes", "The code, the data generator, the infrastructure and the checks live together; a change is a pull request that CI must pass."],
  ["Built from nothing on every change", "CI generates the data from a seed, runs the data checks and the acceptance checks, and compares every table with pinned digests. An image that cannot reproduce the pinned output is never published."],
  ["Tested where people use it", "The backend tests, then every page rendered in a real browser on a desktop and a phone, failing on any error, any missing value on screen, any page wider than the phone."],
  ["Secrets never in the code or the browser", "The model key is a Container Apps secret read by the server only. The assistant's SQL passes a gate - read-only, allowlisted views, a row limit - before it runs."],
  ["Deployed by Terraform, into one resource group", "Container Apps on the consumption plan, warm in Brisbane business hours and at zero outside them, public images, no registry, no vault, no database server. Deleting the group removes everything."],
  ["Watched and priced", "A health check the platform probes, logs capped well inside the free allowance, a run log of the assistant (never the visitor's words), and a monthly budget alert on the group."],
];

export default function Built() {
  const { t } = useTheme();
  const { data: meta } = useApi("/api/meta");
  return (
    <>
      <PageHeader
        title="How it is run"
        brief="All Place code in one Place GitHub, and no production tool on a personal account"
        subtitle="This site is the kind of tool the advertisement says staff are building. What makes it safe to rely on is not the reports but the path it took to production - the same path a platform lead would give every tool that moves into Place's GitHub."
      />
      <Callout tone="warning" title="The irony, stated">
        This demo lives on my personal GitHub account and my own Azure subscription, because it is a job application. That is exactly what the
        twelve-month goal says should not be true of anything Place runs - and the first thing I would fix for each tool that is.
      </Callout>
      <SectionTitle>The path to production</SectionTitle>
      <Grid cols={2} min={320}>
        {STEPS.map(([title, body], i) => (
          <Card key={title} title={`${i + 1}. ${title}`}><p style={{ fontSize: 13, margin: 0, lineHeight: 1.55 }}>{body}</p></Card>
        ))}
      </Grid>
      <SectionTitle>This deployment</SectionTitle>
      <Card>
        <KeyValues columns={3} items={[
          ["Version", meta?.version || "-"],
          ["Build", meta?.build_seconds ? `${meta.build_seconds} s from nothing` : "-"],
          ["Assistant", meta?.llm_configured ? meta.llm_model : "no model key: catalogue answers only"],
          ["Hosting", "Azure Container Apps, australiaeast"],
          ["Cost", "a few dollars a month, warm in business hours only"],
          ["Data", "synthetic, regenerated on every build"],
        ]} />
      </Card>
      <SectionTitle>What changes for a real tool</SectionTitle>
      <Card>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
          <li>Sign-in through Entra ID, with offices and roles from groups, so an office sees its own figures and a principal sees the agents'.</li>
          <li>Data from the sales and property management systems through their exports or APIs, landing daily, with the same checks in front of the reports.</li>
          <li>Personal information only where a report needs it - which, for these reports, is nowhere.</li>
          <li>A register entry: who owns it, what data it holds, which AI it uses, and who to call when it breaks.</li>
        </ul>
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted, marginTop: 14 }}>Built with Claude Code. The assistant's agent layer comes from my earlier real estate demo, moved from AWS to Azure and Gemini.</p>
    </>
  );
}
