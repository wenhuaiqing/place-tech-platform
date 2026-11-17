// Days 61 to 90: cloud spend understood, reported and reduced.

import { Bar, BarChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, fmtMonth, useApi } from "../../lib/api.js";
import { NotBuilt, aud, audWhole, useToolDetail } from "../../lib/place.jsx";
import { Badge, Callout, Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

const KIND = { idle: "Idle", oversized: "Oversized plan", duplicate: "Duplicate", leaver_billing: "Billed to a leaver", runaway: "Runaway spend",
  drift: "Not in Terraform", personal_ai: "Personal AI subscription" };
const REMOVABLE = new Set(["idle", "oversized", "duplicate", "drift"]);
const PLATFORM = { netlify: "Netlify", supabase: "Supabase", firebase: "Firebase", anthropic: "Anthropic API", openai: "OpenAI API",
  azure: "Azure sandbox", "ai-subscriptions": "AI subscriptions" };

export default function Cost() {
  const { t } = useTheme();
  const ch = useChartParts();
  const detail = useToolDetail();
  const { data, error } = useApi("/api/cost");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Cloud cost" /><Loading /></>;
  const months = data.months.map((m) => {
    const rows = data.by_month.filter((r) => r.month === m);
    return { month: fmtMonth(m), total: rows.reduce((a, r) => a + r.aud_cents, 0) / 100, ...Object.fromEntries(rows.map((r) => [r.platform, r.aud_cents])) };
  });
  const last = months[months.length - 1];
  const prev = months[months.length - 2];
  const removable = data.findings.filter((f) => REMOVABLE.has(f.kind)).reduce((a, f) => a + f.monthly_aud_cents, 0);
  const target = data.target.reduce((a, r) => a + r.aud_cents, 0);
  const comparable = data.by_month.filter((r) => r.month === data.months[data.months.length - 2] && !["ai-subscriptions", "azure"].includes(r.platform))
    .reduce((a, r) => a + r.aud_cents, 0);
  const platforms = Object.keys(PLATFORM).filter((p) => data.by_month.some((r) => r.platform === p));
  return (
    <>
      <PageHeader
        title="Cloud cost"
        brief="Use AI cost tools to audit billing, track resource drift and reduce cloud spend, consolidating hosting platforms over time"
        subtitle="Bills from Netlify, Supabase, Firebase and the model APIs, the Azure sandbox, and the expense claims that pay for them, put in one place and attributed to tools. Then what can go now - idle, oversized, duplicated, drifted - and what is at risk: tools billed to the card of someone who has left."
      />
      <Callout tone="neutral" title="Assumptions">
        The platforms bill in US dollars, converted at one assumed rate of A${data.aud_per_usd.toFixed(2)} per US$ for the whole period; the finance team's
        rate replaces it. Netlify Pro is billed per member, not per site, so it is split evenly across the member's sites, and the basis is written on
        every line. Expense claims are matched to bills by person, platform and month, within 5%.
      </Callout>
      <Grid cols={4} min={170}>
        <Stat label={`Spend, ${last.month}`} value={audWhole(last.total * 100)} emphasis sub="platforms, model APIs, sandbox, subscriptions" />
        <Stat label={`Spend, ${prev.month}`} value={audWhole(prev.total * 100)} sub="the month before; the jump is one runaway function" />
        <Stat label="Removable now" value={`${audWhole(removable)} / month`} tone="good" sub="idle, oversized, duplicate, not in Terraform" />
        <Stat label="On personal cards" value={fmtInt(data.paid_by.filter((p) => p.paid_by.startsWith("personal card") || p.paid_by.startsWith("a leaver")).reduce((a, p) => a + p.tools, 0))}
          tone="warning" sub="tools whose bill a person pays and claims back" />
      </Grid>
      <SectionTitle>Spend by month</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={240}>
              <BarChart data={months} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                {ch.grid}
                {ch.xAxis({ dataKey: "month" })}
                {ch.yAxis({ tickFormatter: (v) => `$${fmtInt(v)}`, width: 56 })}
                {ch.tooltip({ formatter: (v) => [aud(v * 100), "Spend"] })}
                <Bar dataKey="total" name="Spend (A$)" fill={t.chart[0]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          )}
          table={<Table rows={months} columns={[
            { key: "month", label: "Month" },
            ...platforms.map((p) => ({ key: p, label: PLATFORM[p], align: "right", render: (r) => aud(r[p] || 0) })),
            { key: "total", label: "Total", align: "right", render: (r) => aud(r.total * 100) },
          ]} />}
        />
      </Card>
      <SectionTitle>What to do about it</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={520} rows={data.findings} onRowClick={(r) => r.tool_id && detail.open(r.tool_id)} columns={[
          { key: "kind", label: "Finding", render: (r) => <Badge tone={REMOVABLE.has(r.kind) ? "good" : r.kind === "leaver_billing" || r.kind === "runaway" ? "critical" : "warning"}>{KIND[r.kind]}</Badge> },
          { key: "detail", label: "Detail", wrap: true },
          { key: "monthly_aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.monthly_aud_cents) },
          { key: "action", label: "Action", wrap: true },
        ]} />
      </Card>
      <Grid cols={2} min={340}>
        <div>
          <SectionTitle>By tool, {last.month}</SectionTitle>
          <Card pad={0} rule={false}>
            <Table maxHeight={420} rows={data.by_tool} onRowClick={(r) => detail.open(r.tool_id)} columns={[
              { key: "name", label: "Tool", render: (r) => <b style={{ color: t.accent }}>{r.name}</b> },
              { key: "platforms", label: "Billed by" },
              { key: "users_30d", label: "Users", align: "right" },
              { key: "aud_cents", label: "A$", align: "right", render: (r) => aud(r.aud_cents) },
            ]} />
          </Card>
        </div>
        <div>
          <SectionTitle>Who pays</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={data.paid_by} columns={[
              { key: "paid_by", label: "Paid by", wrap: true },
              { key: "tools", label: "Tools", align: "right" },
              { key: "aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.aud_cents) },
            ]} />
          </Card>
          <SectionTitle>Azure sandbox: declared or not</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={data.drift} columns={[
              { key: "name", label: "Resource" },
              { key: "type", label: "Type", wrap: true },
              { key: "in_terraform", label: "Terraform", render: (r) => r.in_terraform ? <Badge tone="good">Declared</Badge> : <Badge tone="warning">By hand</Badge> },
              { key: "monthly_aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.monthly_aud_cents) },
            ]} />
          </Card>
        </div>
      </Grid>
      <SectionTitle>Consolidating hosting: a planning figure</SectionTitle>
      <Callout tone="warning" title="Planning figures, not quotes">
        These are assumptions to size the conversation, to be replaced with the Azure pricing calculator for the design CAB agrees. They do not
        include the time to move each tool, which is the larger cost.
      </Callout>
      <Card pad={0} rule={false}>
        <Table rows={[...data.target, { item: "Total, a month", aud_cents: target }]} columns={[
          { key: "item", label: "Target platform", wrap: true, render: (r) => r.item.startsWith("Total") ? <b>{r.item}</b> : r.item },
          { key: "aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.aud_cents) },
        ]} />
      </Card>
      <p style={{ fontSize: 12.5, color: t.textMuted, maxWidth: 900 }}>
        The same tools cost {audWhole(comparable)} in {prev.month} (platforms and model APIs, before the runaway month), against a planning figure of
        {" "}{audWhole(target)}. Even if that figure is out by half, the stronger case is control: one bill Place owns, tagged by tool, nothing on a
        personal card, and spend caps that stop a runaway function on its first day, not at the end of the month.
      </p>
      <NotBuilt items={[
        "Live billing APIs and Azure Cost Management exports. Here they are files; on the platform they land daily and the same allocation runs.",
        "An AI cost assistant writing the monthly commentary. The numbers and findings above are what it would be given; the commentary is a sentence a person can write from them.",
      ]} />
      {detail.node}
    </>
  );
}
