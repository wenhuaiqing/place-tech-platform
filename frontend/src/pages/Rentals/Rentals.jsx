// Property management: the rent roll, arrears, renewals, maintenance and bonds.

import { Line, LineChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtDate, fmtDay, fmtInt, useApi } from "../../lib/api.js";
import { Assumption, NotBuilt, OfficePicker, dollars, useOffice } from "../../lib/place.jsx";
import { Badge, Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

export default function Rentals() {
  const { t } = useTheme();
  const ch = useChartParts();
  const [office, setOffice] = useOffice();
  const { data: d, error } = useApi(`/api/rentals${office ? `?office=${office}` : ""}`);
  if (error) return <ErrorNote error={error} />;
  if (!d) return <><PageHeader title="Rentals" /><Loading /></>;
  const k = d.kpis;
  const trend = d.arrears_trend.map((w) => ({ week: fmtDay(w.week_ending), pct: w.pct, in_arrears: w.in_arrears, over_watch: w.over_watch }));
  const pctNow = k.managed ? ((k.in_arrears * 100) / k.managed).toFixed(1) : "-";
  return (
    <>
      <PageHeader
        title={office ? `Rentals - Office ${office}` : "Rentals - all offices"}
        brief="Good ideas become secure, supported production tools"
        subtitle={`The rent roll and what needs a property manager's attention: arrears as at ${fmtDate(k.arrears_week)}, leases ending in the next 60 days, repairs that are running late and bonds lodged late. Tenancies are shown by number only.`}
        right={<OfficePicker office={office} onChange={setOffice} />}
      />
      <Grid cols={4} min={180}>
        <Stat label="Properties managed" value={fmtInt(k.managed)} emphasis sub={`${dollars(k.weekly_rent_roll)} rent a week`} />
        <Stat label="In arrears" value={`${pctNow}%`} sub={`${fmtInt(k.in_arrears)} tenancies, ${dollars(k.arrears_amount)} owed`} />
        <Stat label="More than 14 days" value={fmtInt(k.over_watch)} tone={k.over_watch ? "warning" : "good"} sub="the watch list below" />
        <Stat label="Average days vacant" value={k.avg_vacant_days ?? "-"} sub="between tenancies re-let this year" />
        <Stat label="Leases ending in 60 days" value={fmtInt(k.renewals_60d)} sub="start the renewal conversation" />
        <Stat label="Maintenance jobs open" value={fmtInt(k.open_jobs)} sub={`${fmtInt(k.urgent_late)} urgent and over 3 days`} tone={k.urgent_late ? "critical" : undefined} />
        <Stat label="Bonds lodged late" value={k.bonds_late_pct != null ? `${k.bonds_late_pct}%` : "-"} sub="of bonds received this year" />
      </Grid>

      <SectionTitle>Share of tenancies in arrears, weekly</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={230}>
              <LineChart data={trend} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                {ch.grid}
                {ch.xAxis({ dataKey: "week", interval: 3 })}
                {ch.yAxis({ tickFormatter: (v) => `${v}%`, width: 44, domain: [0, "auto"] })}
                {ch.tooltip({ formatter: (v) => [`${v}%`, "In arrears"] })}
                <Line dataKey="pct" name="In arrears" stroke={t.chart[0]} strokeWidth={2} dot={false} />
              </LineChart>
            </ChartFrame>
          )}
          table={<Table rows={trend} maxHeight={300} columns={[{ key: "week", label: "Week ending" }, { key: "pct", label: "% in arrears", align: "right" },
            { key: "in_arrears", label: "Tenancies", align: "right" }, { key: "over_watch", label: "Over 14 days", align: "right" }]} />}
        />
      </Card>

      <SectionTitle>The watch list: more than 14 days in arrears</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={d.watch} maxHeight={380} empty="Nobody is more than 14 days behind." columns={[
          { key: "tenancy_id", label: "Tenancy" }, { key: "office_code", label: "Office" }, { key: "property_manager", label: "Property manager" },
          { key: "days", label: "Days", align: "right", render: (r) => <Badge tone={r.days > 28 ? "critical" : "warning"}>{r.days} days</Badge> },
          { key: "amount", label: "Owed", align: "right", render: (r) => dollars(r.amount) },
          { key: "weekly_rent", label: "Rent a week", align: "right", render: (r) => dollars(r.weekly_rent) },
        ]} />
      </Card>

      <Grid cols={2} min={340}>
        <div>
          <SectionTitle>Maintenance by category</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.maintenance} columns={[
              { key: "category", label: "Category" }, { key: "open", label: "Open", align: "right" },
              { key: "reported_fytd", label: "This year", align: "right" },
              { key: "median_days_to_complete", label: "Median days", align: "right" },
              { key: "cost_fytd", label: "Cost this year", align: "right", render: (r) => dollars(r.cost_fytd) },
            ]} />
          </Card>
        </div>
        <div>
          <SectionTitle>Urgent repairs open more than 3 days</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.urgent_late} empty="None: every urgent job is within three days." columns={[
              { key: "job_id", label: "Job" }, { key: "office_code", label: "Office" }, { key: "category", label: "Category" },
              { key: "reported_on", label: "Reported", render: (r) => fmtDate(r.reported_on) },
              { key: "days_open", label: "Days open", align: "right", render: (r) => <Badge tone="critical">{r.days_open} days</Badge> },
            ]} />
          </Card>
          <SectionTitle>Leases ending, by week</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.renewals} columns={[{ key: "week", label: "Week of", render: (r) => fmtDate(r.week) }, { key: "leases", label: "Leases ending", align: "right" }]} />
          </Card>
        </div>
      </Grid>

      <SectionTitle>Bonds lodged late or not yet lodged</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={d.bonds_late} maxHeight={320} empty="Every bond this year was lodged on time." columns={[
          { key: "bond_id", label: "Bond" }, { key: "tenancy_id", label: "Tenancy" }, { key: "office_code", label: "Office" },
          { key: "received_on", label: "Received", render: (r) => fmtDate(r.received_on) },
          { key: "lodged_on", label: "Lodged", render: (r) => (r.lodged_on ? fmtDate(r.lodged_on) : <Badge tone="critical">Not yet</Badge>) },
          { key: "days_to_lodge", label: "Days", align: "right", render: (r) => r.days_to_lodge ?? "-" },
          { key: "amount", label: "Amount", align: "right", render: (r) => dollars(r.amount) },
        ]} />
      </Card>
      <Assumption>a bond counts as lodged on time within 10 days of receipt, and arrears count from one day overdue. Check both against the current rules and Place's own policy before relying on them.</Assumption>
      <NotBuilt items={[
        "Tenant names and contact details. A report that needs no personal information should not hold any; the property manager's own system has them.",
        "Sending arrears notices. A report shows who is behind; the notice is a property manager's decision, made in the trust accounting system.",
      ]} />
    </>
  );
}
