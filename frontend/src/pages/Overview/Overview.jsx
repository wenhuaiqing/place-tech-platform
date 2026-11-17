// The group at a glance: this financial year against the same days last year.

import { Link } from "react-router-dom";
import { Bar, BarChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useOrb } from "../../context/OrbContext.jsx";
import { fmtDate, fmtInt, fmtMonth, useApi } from "../../lib/api.js";
import { Change, dollars, millions } from "../../lib/place.jsx";
import { Button, Callout, Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

export default function Overview() {
  const { t } = useTheme();
  const ch = useChartParts();
  const orb = useOrb();
  const { data: d, error } = useApi("/api/overview");
  const { data: meta } = useApi("/api/meta");
  if (error) return <ErrorNote error={error} />;
  if (!d || !meta) return <><PageHeader title="Overview" /><Loading /></>;
  const ty = d.sales.this_year;
  const ly = d.sales.last_year;
  const r = d.rentals;
  const monthly = d.monthly.map((m) => ({ month: fmtMonth(m.month), commission: m.commission, sales: m.sales }));
  const offices = [...d.offices].sort((a, b) => (b.commission || 0) - (a.commission || 0));
  const arrearsPct = r.managed ? (r.in_arrears * 100) / r.managed : 0;
  return (
    <>
      <PageHeader
        title="The agency this financial year"
        brief="Our people are already using Claude and Copilot Studio to build tools that make their work easier"
        subtitle={`A reporting site for a 26-office residential agency: sales from appraisal to settlement, the rent roll and arrears, each office's scorecard, vendor-paid marketing - with every figure checked before it is shown, and an assistant that answers questions with the query behind the answer. Financial year to date is 01/07/2026 to ${fmtDate(meta.today)}; each comparison is with the same days a year earlier.`}
      />
      <Callout tone="neutral" title="What this is">
        The kind of tool Place's staff are building, built the way a platform lead would want it built: one source of the numbers, data checks
        before anything reaches a report, tests, and a deployment that costs a few dollars a month. Built with Claude Code for an application to
        Place Estate Agents, and named for it. Not affiliated with or endorsed by Place: the 26 offices are from the advertisement, and every
        office, person, property and figure is invented.
      </Callout>
      <Grid cols={4} min={190}>
        <Stat label="Sales (under contract)" value={fmtInt(ty.sales)} emphasis sub={<Change now={ty.sales} then={ly.sales} />} />
        <Stat label="Commission written" value={millions(ty.commission)} sub={<Change now={ty.commission} then={ly.commission} />} />
        <Stat label="Median days on market" value={`${ty.median_dom} days`} sub={<Change now={ty.median_dom} then={ly.median_dom} lowerIsBetter />} />
        <Stat label="Auction clearance" value={`${ty.clearance_pct}%`} sub={<Change now={ty.clearance_pct} then={ly.clearance_pct} />} />
      </Grid>
      <div style={{ height: 12 }} />
      <Grid cols={4} min={190}>
        <Stat label="Properties managed" value={fmtInt(r.managed)} sub={`${dollars(r.weekly_rent_roll)} rent a week`} />
        <Stat label="In arrears now" value={`${arrearsPct.toFixed(1)}%`} tone={arrearsPct > 8 ? "warning" : undefined}
          sub={`${fmtInt(r.in_arrears)} tenancies; ${fmtInt(r.over_watch)} more than 14 days`} />
        <Stat label="Leases ending in 60 days" value={fmtInt(r.renewals_60d)} sub="renewal conversations to start now" />
        <Stat label="Urgent repairs open over 3 days" value={fmtInt(r.urgent_late)} tone={r.urgent_late ? "critical" : "good"} sub={`${fmtInt(r.open_jobs)} jobs open in all`} />
      </Grid>

      <SectionTitle>Commission written, by month</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={240}>
              <BarChart data={monthly} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                {ch.grid}
                {ch.xAxis({ dataKey: "month", interval: 1 })}
                {ch.yAxis({ tickFormatter: (v) => `$${(v / 1_000_000).toFixed(0)}M`, width: 48 })}
                {ch.tooltip({ formatter: (v, n) => [n === "commission" ? dollars(v) : fmtInt(v), n === "commission" ? "Commission" : "Sales"] })}
                <Bar dataKey="commission" name="commission" fill={t.chart[0]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          )}
          table={<Table rows={monthly} columns={[
            { key: "month", label: "Month" }, { key: "sales", label: "Sales", align: "right", render: (x) => fmtInt(x.sales) },
            { key: "commission", label: "Commission", align: "right", render: (x) => dollars(x.commission) }]} />}
        />
        <p style={{ fontSize: 12, color: t.textMuted, margin: "6px 0 0" }}>A sale counts in the month it went under contract. November is to date.</p>
      </Card>

      <SectionTitle right={<Link to="/offices"><Button>All 26 offices</Button></Link>}>Offices by commission this year</SectionTitle>
      <Grid cols={2} min={320}>
        <Card title="Top five" pad={0}>
          <Table rows={offices.slice(0, 5)} columns={[
            { key: "office", label: "Office", render: (o) => <Link to={`/sales?office=${o.office_code}`} style={{ color: t.accent, fontWeight: 650 }}>{o.office}</Link> },
            { key: "region", label: "Region" },
            { key: "commission", label: "Commission", align: "right", render: (o) => dollars(o.commission) },
            { key: "vs", label: "", render: (o) => <Change now={o.commission} then={o.commission_last_year} /> },
          ]} />
        </Card>
        <Card title="Bottom five" pad={0}>
          <Table rows={offices.slice(-5).reverse()} columns={[
            { key: "office", label: "Office", render: (o) => <Link to={`/sales?office=${o.office_code}`} style={{ color: t.accent, fontWeight: 650 }}>{o.office}</Link> },
            { key: "region", label: "Region" },
            { key: "commission", label: "Commission", align: "right", render: (o) => dollars(o.commission) },
            { key: "vs", label: "", render: (o) => <Change now={o.commission} then={o.commission_last_year} /> },
          ]} />
        </Card>
      </Grid>

      <SectionTitle>Ask instead of looking</SectionTitle>
      <Card hint="The assistant (bottom right, on every page) writes one query, checks it, runs it read-only, and shows the query with the answer.">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Who are the top ten agents by commission this financial year?", "Which offices have the most tenancies more than 14 days in arrears?",
            "How many leases end in the next 60 days, by office?"].map((q) => (
            <Button key={q} tone="ai" onClick={() => orb.openWithPrompt(q, { module: "overview" })}>{q}</Button>
          ))}
        </div>
      </Card>
      <p style={{ fontSize: 12.5, color: t.textMuted, marginTop: 14 }}>
        {fmtInt(d.checks)} records failed a data check and are kept out of these figures - see <Link to="/data-checks" style={{ color: t.accent, fontWeight: 650 }}>Data checks</Link>.
      </p>
    </>
  );
}
