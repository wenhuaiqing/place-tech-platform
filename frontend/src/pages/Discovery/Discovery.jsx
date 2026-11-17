// How the register was built: the exports, the keys that join them, and
// what was held because the evidence could not decide.

import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { NotBuilt } from "../../lib/place.jsx";
import { Callout, Card, ErrorNote, Grid, Loading, Mono, PageHeader, SectionTitle, Table } from "../../lib/ui.jsx";

export default function Discovery() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/register/discovery");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="How it was found" /><Loading /></>;
  return (
    <>
      <PageHeader
        title="How the register was found"
        brief="Today, those tools sit across pilot and personal accounts ... without a single owner inside Place"
        subtitle="No single system knows what exists. Each export knows a piece: the repository, the site that serves it, the database behind it, the name staff type, the survey answer, the bill and who claims it. The register joins them by the keys they actually share - a site's linked repository, the project named in .firebaserc, a project URL in the code, a DNS target - and never by a name, because names drift."
      />
      <Callout tone="warning" title="Hold, never guess">
        When the evidence conflicts, the register keeps the tool and holds the conflict for a person: two repositories that both deploy one site by
        hand are not resolved by picking the newer. A held item is a question for the builder, and the answer is recorded.
      </Callout>
      <Grid cols={2} min={340}>
        <Card title="The exports" hint="As the first week would have them: files from each platform and from the managed service provider.">
          <Table maxHeight={420} rows={data.exports} columns={[
            { key: "name", label: "Export", wrap: true },
            { key: "rows", label: "Rows", align: "right", render: (r) => fmtInt(r.rows) },
            { key: "gives", label: "Tells us", wrap: true },
          ]} />
        </Card>
        <Card title="What joined them" hint="Each link is a key two exports share. One tool usually needs three or four.">
          <Table maxHeight={420} rows={data.joins} columns={[
            { key: "joined_by", label: "Key", wrap: true },
            { key: "links", label: "Links", align: "right" },
          ]} />
        </Card>
      </Grid>
      <SectionTitle>Held for a person</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={data.holds} columns={[
          { key: "hold_id", label: "Hold" },
          { key: "source", label: "From" },
          { key: "ref", label: "What", render: (r) => <Mono>{r.ref}</Mono> },
          { key: "reason", label: "Why it is held", wrap: true },
        ]} />
      </Card>
      <SectionTitle>Names that point at nothing</SectionTitle>
      {data.dangling.map((d) => <Callout key={d.detail} tone="critical" title="Dangling DNS record">{d.detail} Delete the record, or claim the name.</Callout>)}
      <Grid cols={2} min={340}>
        <Card title="Joined by key, not by name" hint="Sites whose names are nothing like their repositories. A name match would have missed or mismatched them.">
          <Table rows={data.renamed} columns={[
            { key: "name", label: "Tool" },
            { key: "site", label: "Site", render: (r) => <Mono>{r.site}</Mono> },
            { key: "repo", label: "Repository", render: (r) => <Mono>{r.repo}</Mono> },
          ]} />
        </Card>
        <Card title="What builders said, against what was measured" hint="The survey's user estimates against the platforms' own 30-day counts. Ask, then measure.">
          <Table rows={data.survey_vs_measured} columns={[
            { key: "name", label: "Tool", wrap: true },
            { key: "users_estimate", label: "Said", align: "right" },
            { key: "users_30d", label: "Measured", align: "right" },
          ]} />
        </Card>
      </Grid>
      <p style={{ fontSize: 12.5, color: t.textMuted, maxWidth: 900 }}>
        Every export row ends up in a tool or in a hold; the build fails otherwise. Nothing is dropped quietly.
      </p>
      <NotBuilt items={[
        "Entra ID sign-in logs, which would give real usage for every tool behind single sign-on. The platforms' own counts stand in for them here.",
        "A scheduled re-run. Once access is granted the same joins run weekly and the register shows what appeared since.",
      ]} />
    </>
  );
}
