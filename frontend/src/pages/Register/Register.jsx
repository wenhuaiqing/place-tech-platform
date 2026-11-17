// Days 1 to 30: every tool staff have built, where it runs and who owns it.

import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtInt, useApi } from "../../lib/api.js";
import { HomeBadge, NotBuilt, OutcomeBadge, SeverityBadge, TierBadge, aud, useToolDetail } from "../../lib/place.jsx";
import { Badge, Callout, Card, ErrorNote, Grid, Loading, PageHeader, SectionTitle, SegmentedControl, Stat, Table } from "../../lib/ui.jsx";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "tier1", label: "Tier 1" },
  { value: "critical", label: "Critical flags" },
  { value: "refused", label: "Refused by the gate" },
  { value: "undeclared", label: "Not declared" },
  { value: "idle", label: "Idle" },
];

export default function Register() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/register");
  const [params, setParams] = useSearchParams();
  const filter = params.get("filter") || "all";
  const detail = useToolDetail();
  const critical = useMemo(() => new Set((data?.flags || []).filter((f) => f.severity === "critical").map((f) => f.tool_id)), [data]);
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Tool register" /><Loading /></>;
  const tools = data.tools;
  const shown = tools.filter((r) => ({
    all: true, tier1: r.tier === 1, critical: critical.has(r.tool_id), refused: r.gate === "refuse",
    undeclared: !r.declared, idle: r.users_30d === 0,
  })[filter]);
  const live = tools.filter((r) => !["retired", "merged"].includes(r.status));
  const personal = live.filter((r) => r.home === "personal accounts").length;
  const users = live.reduce((a, r) => a + r.users_30d, 0);
  return (
    <>
      <PageHeader
        title="Tool register"
        brief="Days 1 to 30: Inventory the tools staff have built, where they run and who owns them"
        subtitle="One row per tool, joined from the HR feed, the inventory survey, GitHub, Netlify, Firebase, Supabase, Copilot Studio, DNS, billing and expense claims. Tier, data classes and owner status are worked out from the data, not asked for. Click a tool for everything known about it."
      />
      <Grid cols={4} min={180}>
        <Stat label="Tools" value={fmtInt(tools.length)} emphasis sub={`${tools.filter((r) => !r.declared).length} found that nobody declared`} />
        <Stat label="On personal accounts" value={fmtInt(personal)} tone={personal ? "warning" : "good"} sub="the 12-month goal is none in production" />
        <Stat label="People using them" value={fmtInt(users)} sub="sum of 30-day users across tools; one person may use several" />
        <Stat label="Tier 1" value={fmtInt(tools.filter((r) => r.tier === 1).length)} sub="identity documents, financial data, or 60+ users" />
      </Grid>
      <Callout tone="neutral" title="How tier is decided">
        Tier 1: holds identity documents or income, or personal and financial data together, or 60 or more people used it in 30 days. Tier 2: holds
        personal information. Tier 3: public or internal data only. Data classes come from the column names in each database export and from what
        the code sends to a model. An assumption to agree with CAB, not a standard Place has.
      </Callout>
      <SectionTitle right={<SegmentedControl label="Filter" options={FILTERS} value={filter} onChange={(v) => setParams(v === "all" ? {} : { filter: v })} />}>
        {shown.length} tools
      </SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={640} rows={shown} onRowClick={(r) => detail.open(r.tool_id)} columns={[
          { key: "name", label: "Tool", render: (r) => (
            <span style={{ display: "inline-flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
              <b style={{ color: t.accent }}>{r.name}</b>{!r.declared && <Badge tone="warning">Not declared</Badge>}
            </span>) },
          { key: "owner_name", label: "Owner", render: (r) => r.owner_status === "left" ? <span>{r.owner_name} <Badge tone="critical">Left</Badge></span> : (r.owner_name || "Unknown") },
          { key: "process", label: "Process", render: (r) => r.process || "-" },
          { key: "hosting", label: "Runs on", render: (r) => [r.hosting, r.database].filter(Boolean).join(" + ") || (r.kind === "agent" ? "Copilot Studio" : "a laptop") },
          { key: "users_30d", label: "Users", align: "right", render: (r) => fmtInt(r.users_30d) },
          { key: "data_classes", label: "Data", render: (r) => r.data_classes },
          { key: "tier", label: "Tier", render: (r) => <TierBadge tier={r.tier} /> },
          { key: "gate", label: "Gate", render: (r) => <OutcomeBadge outcome={r.gate} /> },
          { key: "monthly_cost_aud_cents", label: "A$ / month", align: "right", render: (r) => aud(r.monthly_cost_aud_cents) },
          { key: "home", label: "Home", render: (r) => <HomeBadge home={r.home} status={r.status} /> },
        ]} />
      </Card>
      <SectionTitle>What the register says needs attention</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={420} rows={data.flags} onRowClick={(r) => r.tool_id && detail.open(r.tool_id)} columns={[
          { key: "severity", label: "Severity", render: (r) => <SeverityBadge severity={r.severity} /> },
          { key: "flag", label: "Flag", render: (r) => r.flag.replace(/_/g, " ") },
          { key: "name", label: "Tool", render: (r) => r.name || "-" },
          { key: "detail", label: "Detail", wrap: true },
        ]} />
      </Card>
      <NotBuilt items={[
        "A live connection to each platform's API: the exports are files here, as they would be in week one, before any access is granted.",
        "The survey itself. In practice it is a fifteen-minute conversation with each builder, and the register is what it fills in.",
        "Ownership of the Copilot Studio environments and Entra app registrations, which the managed service provider administers.",
      ]} />
      {detail.node}
    </>
  );
}
