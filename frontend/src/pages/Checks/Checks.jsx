// Data checks: what was wrong in the data, found before it reached a report.

import { useState } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useApi } from "../../lib/api.js";
import { NotBuilt } from "../../lib/place.jsx";
import { Badge, Callout, Card, ErrorNote, Loading, Mono, PageHeader, SectionTitle, SegmentedControl, Table } from "../../lib/ui.jsx";

export default function Checks() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/checks");
  const [pick, setPick] = useState("all");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Data checks" /><Loading /></>;
  const shown = data.findings.filter((f) => pick === "all" || f.check_id === pick);
  return (
    <>
      <PageHeader
        title="Data checks"
        brief="Guardrails and review applied to every tool before it reaches production"
        subtitle="A report is only as good as what goes into it. Every record passes these checks before any page counts it; what fails is listed here with the reason, and kept out of the figures it would distort. Nothing is dropped quietly, and nothing is corrected by guessing."
      />
      <Callout tone="neutral" title="How the checks are tested">
        The data is generated with a known number of each kind of error put in on purpose. The tests check that every one is found from the data
        alone, and the build fails if a quarantined record reaches a report.
      </Callout>
      <SectionTitle>The checks</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={data.checks} columns={[
          { key: "check_id", label: "Check", render: (c) => <b>{c.check_id} {c.name}</b> },
          { key: "found", label: "Found", align: "right", render: (c) => <Badge tone={c.found ? "warning" : "good"}>{c.found}</Badge> },
          { key: "what", label: "What it means, and what happens", wrap: true },
          { key: "reports", label: "Kept out of", wrap: true },
        ]} />
      </Card>
      <SectionTitle right={<SegmentedControl label="Check" value={pick} onChange={setPick}
        options={[{ value: "all", label: "All" }, ...data.checks.map((c) => ({ value: c.check_id, label: c.check_id }))]} />}>
        Every finding ({shown.length})
      </SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={shown} maxHeight={520} columns={[
          { key: "check_id", label: "Check" }, { key: "record_id", label: "Record", render: (f) => <Mono>{f.record_id}</Mono> },
          { key: "office_code", label: "Office" }, { key: "detail", label: "What was found", wrap: true },
        ]} />
      </Card>
      <SectionTitle>What else must hold, or there is no build</SectionTitle>
      <Card>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>{data.acceptance.map((a) => <li key={a}>{a}</li>)}</ul>
      </Card>
      <p style={{ fontSize: 12, color: t.textMuted }}>In practice each finding goes back to the office that keyed it, and the record returns to the figures once it is fixed at source.</p>
      <NotBuilt items={["A workflow for fixing records here. The fix belongs in the system the record came from, so the report and the source never disagree."]} />
    </>
  );
}
