// Vendor-paid marketing: spend against the agreed budget, and where enquiries come from.

import { Bar, BarChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { NotBuilt, OfficePicker, dollars, useOffice } from "../../lib/place.jsx";
import { Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

export default function Marketing() {
  const { t } = useTheme();
  const ch = useChartParts();
  const [office, setOffice] = useOffice();
  const { data: d, error } = useApi(`/api/marketing${office ? `?office=${office}` : ""}`);
  if (error) return <ErrorNote error={error} />;
  if (!d) return <><PageHeader title="Marketing" /><Loading /></>;
  const tot = d.totals;
  return (
    <>
      <PageHeader
        title={office ? `Marketing - Office ${office}` : "Marketing - all offices"}
        brief="Good ideas become secure, supported production tools"
        subtitle="Vendor-paid advertising for listings this financial year: what each vendor agreed to spend, what was spent, and the enquiries it brought, by channel. Spend over budget is money a vendor did not agree to."
        right={<OfficePicker office={office} onChange={setOffice} />}
      />
      <Grid cols={4} min={180}>
        <Stat label="Listings with a campaign" value={fmtInt(tot.listings)} />
        <Stat label="Spent against budget" value={dollars(tot.spend)} emphasis sub={`budget ${dollars(tot.budget)}`} />
        <Stat label="Listings over budget" value={fmtInt(tot.over_budget)} tone={tot.over_budget ? "warning" : "good"} sub="each needs the vendor's agreement" />
        <Stat label="Cost per enquiry" value={dollars(tot.cost_per_enquiry, { decimals: 2 })} sub={`${fmtInt(tot.enquiries)} enquiries`} />
      </Grid>
      <SectionTitle>Enquiries by channel</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={220}>
              <BarChart data={d.channels} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                {ch.grid}
                {ch.xAxis({ dataKey: "channel" })}
                {ch.yAxis({ width: 52, tickFormatter: (v) => fmtInt(v) })}
                {ch.tooltip({ formatter: (v) => [fmtInt(v), "Enquiries"] })}
                <Bar dataKey="enquiries" name="Enquiries" fill={t.chart[0]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          )}
          table={<Table rows={d.channels} columns={[{ key: "channel", label: "Channel" }, { key: "enquiries", label: "Enquiries", align: "right", render: (r) => fmtInt(r.enquiries) }]} />}
        />
        <p style={{ fontSize: 12, color: t.textMuted, margin: "6px 0 0" }}>Channel names are generic: the portals and media a real agency uses are its own choice.</p>
      </Card>
      <Grid cols={2} min={340}>
        <div>
          <SectionTitle>Most over budget</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.most_over} maxHeight={420} empty="Nothing over budget." columns={[
              { key: "address", label: "Property", wrap: true }, { key: "office_code", label: "Office" },
              { key: "budget", label: "Budget", align: "right", render: (r) => dollars(r.budget) },
              { key: "over_by", label: "Over by", align: "right", render: (r) => dollars(r.over_by) },
            ]} />
          </Card>
        </div>
        <div>
          <SectionTitle>By office</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={d.by_office} maxHeight={420} columns={[
              { key: "office_code", label: "Office" }, { key: "listings", label: "Listings", align: "right" },
              { key: "spend", label: "Spend", align: "right", render: (r) => dollars(r.spend) },
              { key: "cost_per_enquiry", label: "Per enquiry", align: "right", render: (r) => dollars(r.cost_per_enquiry, { decimals: 2 }) },
              { key: "over_budget", label: "Over budget", align: "right" },
            ]} />
          </Card>
        </div>
      </Grid>
      <NotBuilt items={[
        "The creative itself. Campaigns are the in-house agency's work; this page only counts money and enquiries.",
        "Attribution to a sale. An enquiry is counted where it arrived; which one became the buyer needs the CRM's history.",
      ]} />
    </>
  );
}
