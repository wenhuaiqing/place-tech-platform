// Sales: appraisal to listing to contract to settlement, for the group or one office.

import { Bar, BarChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtDate, fmtInt, fmtMonth, useApi } from "../../lib/api.js";
import { Assumption, Change, NotBuilt, OfficePicker, dollars, millions, useOffice } from "../../lib/place.jsx";
import { Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

export default function Sales() {
  const { t } = useTheme();
  const ch = useChartParts();
  const [office, setOffice] = useOffice();
  const { data: d, error } = useApi(`/api/sales${office ? `?office=${office}` : ""}`);
  if (error) return <ErrorNote error={error} />;
  if (!d) return <><PageHeader title="Sales" /><Loading /></>;
  const ty = d.this_year;
  const ly = d.last_year;
  const f = d.funnel;
  const monthly = d.monthly.map((m) => ({ month: fmtMonth(m.month), listings: m.listings, sales: m.sales }));
  const pct = (a, b) => (b ? `${((a * 100) / b).toFixed(1)}%` : "-");
  return (
    <>
      <PageHeader
        title={office ? `Sales - Office ${office}` : "Sales - all offices"}
        brief="Good ideas become secure, supported production tools"
        subtitle="From appraisal to listing to contract to settlement. A sale counts on the day it goes under contract; commission is the agency's gross commission on the agreed price. Choose an office to see its own figures and agents."
        right={<OfficePicker office={office} onChange={setOffice} />}
      />
      <Grid cols={4} min={180}>
        <Stat label="Appraisals" value={fmtInt(ty.appraisals)} sub={<Change now={ty.appraisals} then={ly.appraisals} />} />
        <Stat label="New listings" value={fmtInt(ty.new_listings)} sub={<Change now={ty.new_listings} then={ly.new_listings} />} />
        <Stat label="Sales" value={fmtInt(ty.sales)} emphasis sub={<Change now={ty.sales} then={ly.sales} />} />
        <Stat label="Commission written" value={millions(ty.commission)} sub={<Change now={ty.commission} then={ly.commission} />} />
        <Stat label="Median price" value={dollars(ty.median_price)} sub={<Change now={ty.median_price} then={ly.median_price} />} />
        <Stat label="Median days on market" value={ty.median_dom ?? "-"} sub={<Change now={ty.median_dom} then={ly.median_dom} lowerIsBetter />} />
        <Stat label="Auction clearance" value={ty.clearance_pct != null ? `${ty.clearance_pct}%` : "-"} sub={<Change now={ty.clearance_pct} then={ly.clearance_pct} />} />
        <Stat label="Settling, not yet settled" value={fmtInt(d.pipeline.pending)} sub={`${dollars(d.pipeline.commission)} commission; ${fmtInt(d.pipeline.next_30_days)} in the next 30 days`} />
      </Grid>

      <SectionTitle>This year's funnel</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={[
          { stage: "Appraisals", n: f.appraisals, rate: "" },
          { stage: "Appraisals that became listings", n: f.became_listings, rate: pct(f.became_listings, f.appraisals) },
          { stage: "Listed this year", n: f.listed, rate: "" },
          { stage: "Of those, sold", n: f.sold, rate: pct(f.sold, f.listed) },
          { stage: "Of those, withdrawn", n: f.withdrawn, rate: pct(f.withdrawn, f.listed) },
          { stage: "On the market today", n: f.on_market, rate: "" },
        ]} columns={[
          { key: "stage", label: "Stage" }, { key: "n", label: "Count", align: "right", render: (r) => fmtInt(r.n) }, { key: "rate", label: "Rate", align: "right" },
        ]} />
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>Listings from the last few weeks have not had time to sell, so this year's sold rate rises as the year goes on.</p>

      <SectionTitle>New listings and sales, by month</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={250}>
              <BarChart data={monthly} margin={{ top: 6, right: 8, left: 0, bottom: 0 }} barGap={2}>
                {ch.grid}
                {ch.xAxis({ dataKey: "month", interval: 1 })}
                {ch.yAxis({ allowDecimals: false, width: 44 })}
                {ch.tooltip({})}
                {ch.legend({})}
                <Bar dataKey="listings" name="New listings" fill={t.chart[0]} radius={[4, 4, 0, 0]} />
                <Bar dataKey="sales" name="Sales" fill={t.chart[1]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          )}
          table={<Table rows={monthly} columns={[{ key: "month", label: "Month" }, { key: "listings", label: "New listings", align: "right" }, { key: "sales", label: "Sales", align: "right" }]} />}
        />
      </Card>

      <Grid cols={2} min={340}>
        <div>
          <SectionTitle>Auction or private treaty</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.by_method} columns={[
              { key: "method", label: "Method" }, { key: "sales", label: "Sales", align: "right", render: (r) => fmtInt(r.sales) },
              { key: "median_dom", label: "Median days", align: "right" }, { key: "median_price", label: "Median price", align: "right", render: (r) => dollars(r.median_price) },
            ]} />
          </Card>
        </div>
        <div>
          <SectionTitle>Settling next</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.settling} maxHeight={300} columns={[
              { key: "settle_on", label: "Settles", render: (r) => fmtDate(r.settle_on) },
              { key: "address", label: "Property", wrap: true },
              { key: "office_code", label: "Office" },
              { key: "commission", label: "Commission", align: "right", render: (r) => dollars(r.commission) },
            ]} />
          </Card>
        </div>
      </Grid>

      <SectionTitle>{office ? `Agents in Office ${office}` : "Top agents across the group"}</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={d.agents} maxHeight={480} columns={[
          { key: "name", label: "Agent" }, { key: "office_code", label: "Office" },
          { key: "appraisals", label: "Appraisals", align: "right" },
          { key: "conversion", label: "Became listings", align: "right", render: (r) => pct(r.listed, r.appraisals) },
          { key: "sales", label: "Sales (share)", align: "right" },
          { key: "commission", label: "Commission share", align: "right", render: (r) => dollars(r.commission) },
        ]} />
      </Card>
      <Assumption>commission rates between 2.00% and 2.75% of the price, and a 50/50 split when a second agent sells another's listing. Sales whose split does not add to 100% are left out of agent figures until fixed.</Assumption>
      <NotBuilt items={[
        "A connection to the sales system. The data here is generated; on the job, the same views would sit over the CRM's export or API.",
        "Agent targets. They belong to each office's principal, and a report should show them only once they are agreed.",
      ]} />
    </>
  );
}
