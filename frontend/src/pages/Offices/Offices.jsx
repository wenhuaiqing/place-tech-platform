// Every office on one page: sales, rentals and data quality side by side.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { Change, NotBuilt, dollars } from "../../lib/place.jsx";
import { Badge, Card, ErrorNote, Loading, PageHeader, SectionTitle, SegmentedControl, Table } from "../../lib/ui.jsx";

const SORTS = { commission: "Commission", arrears_pct: "Arrears", median_dom: "Days on market", region: "Region" };

export default function Offices() {
  const { t } = useTheme();
  const navigate = useNavigate();
  const { data, error } = useApi("/api/offices");
  const [sort, setSort] = useState("commission");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Offices" /><Loading /></>;
  const rows = [...data.offices].sort((a, b) => {
    if (sort === "region") return a.region.localeCompare(b.region) || a.office_code.localeCompare(b.office_code);
    const dir = sort === "commission" ? -1 : -1;
    return dir * ((a[sort] ?? 0) - (b[sort] ?? 0));
  });
  return (
    <>
      <PageHeader
        title="Offices"
        brief="Productivity ... handles day-to-day IT operations for 26 offices and around 700 staff"
        subtitle="All 26 offices on one scorecard: sales and commission this financial year against the same days last year, days on market, the rent roll, arrears, and how many of the office's records failed a data check. Click an office for its sales; its rentals are one click further."
      />
      <SectionTitle right={<SegmentedControl label="Sort by" value={sort} onChange={setSort} options={Object.entries(SORTS).map(([value, label]) => ({ value, label }))} />}>
        Scorecard
      </SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={rows} maxHeight={900} onRowClick={(o) => navigate(`/sales?office=${o.office_code}`)} columns={[
          { key: "office", label: "Office", render: (o) => <b style={{ color: t.accent }}>{o.office}</b> },
          { key: "region", label: "Region" },
          { key: "agents", label: "Agents", align: "right" },
          { key: "sales", label: "Sales", align: "right", render: (o) => fmtInt(o.sales) },
          { key: "commission", label: "Commission", align: "right", render: (o) => dollars(o.commission) },
          { key: "vs", label: "On last year", render: (o) => <Change now={o.commission} then={o.commission_last_year} /> },
          { key: "median_dom", label: "Median days", align: "right" },
          { key: "managed", label: "Managed", align: "right", render: (o) => fmtInt(o.managed) },
          { key: "arrears_pct", label: "Arrears", align: "right", render: (o) => `${o.arrears_pct}%` },
          { key: "over_watch", label: "Over 14 days", align: "right" },
          { key: "data_issues", label: "Data issues", align: "right", render: (o) => (o.data_issues ? <Badge tone="warning">{o.data_issues}</Badge> : "0") },
        ]} />
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>Offices are lettered A to Z and grouped into invented regions; none is a real Place office.</p>
      <NotBuilt items={[
        "League tables of people. Agent figures stay inside each office's Sales view, where the principal can read them in context.",
        "Franchise or ownership splits. How each office's commission is shared is the business's arrangement, not something to guess.",
      ]} />
    </>
  );
}
