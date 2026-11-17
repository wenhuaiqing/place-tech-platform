// Days 61 to 90: monitoring for the tools staff use - less noise, nothing hidden.

import { useSearchParams } from "react-router-dom";
import { Bar, BarChart } from "recharts";
import { useTheme } from "../../context/ThemeContext.jsx";
import { fmtDate, fmtDateTime, fmtDay, fmtInt, useApi } from "../../lib/api.js";
import { Modal } from "../../lib/kit.jsx";
import { NotBuilt } from "../../lib/place.jsx";
import { Badge, Callout, Card, ChartFrame, ChartOrTable, ErrorNote, Grid, Loading, Mono, PageHeader, SectionTitle, Stat, Table, useChartParts } from "../../lib/ui.jsx";

const RULE_WHY = {
  "maintenance window": "The nightly deploy restarts every app between 02:00 and 02:20. Probe, 5xx and latency alerts in that window are expected.",
  "one probe region only": "An uptime or TLS failure counts when two probe regions agree within ten minutes. One region failing alone is the probe, not the site.",
  "single slow minute": "A latency alert pages when a second follows within fifteen minutes. One slow request is not a page.",
  "first request after idle": "Apps that scale to zero are slow on the first request of the morning. Expected, and a cost choice, not a fault.",
  "duplicate from a second monitor": "The same check configured in two monitors. Each copy pairs with one original.",
  "grouped into an open page": "Alerts on a tool within 30 minutes of each other join the open page, for up to two hours.",
  paged: "A person was told.",
};

function PageDetail({ pageId, onClose }) {
  const { t } = useTheme();
  const { data, error } = useApi(pageId ? `/api/monitoring/pages/${pageId}` : null);
  const w = data?.world;
  return (
    <Modal open={Boolean(pageId)} onClose={onClose} title={data ? `${data.page.page_id} - ${data.page.tool_key}` : "Page"} width={900}>
      {error && <ErrorNote error={error} />}
      {!data && !error && <Loading />}
      {data && (
        <>
          <p style={{ fontSize: 13, marginTop: 0 }}>
            Opened {fmtDateTime(data.page.opened_at, { seconds: false })}, last alert {fmtDateTime(data.page.closed_at, { seconds: false })}: {data.page.signals}.
            {data.case_id && <> Triage case <b>{data.case_id}</b>.</>}
          </p>
          <SectionTitle>What the triage agent would see</SectionTitle>
          <p style={{ fontSize: 12.5, color: t.textMuted, marginTop: 0 }}>A snapshot frozen when the page opened, personal details masked before it was taken.</p>
          <Grid cols={2} min={300}>
            <Card title="Logs">
              {(w.get_error_logs || []).length === 0 ? <p style={{ fontSize: 12.5 }}>No log lines in the window.</p> :
                w.get_error_logs.map((l, i) => <div key={i} style={{ fontSize: 12, marginBottom: 6 }}><Mono dim>{l.at.slice(11, 16)}</Mono> {l.line}</div>)}
            </Card>
            <Card title="Deploys, config and provider">
              {(w.get_recent_deploys || []).map((d) => <div key={d.commit} style={{ fontSize: 12.5, marginBottom: 6 }}>Deploy <Mono>{d.commit}</Mono> {fmtDateTime(d.at, { seconds: false })}: {d.message} ({d.files.join(", ")})</div>)}
              {(w.get_config_changes || []).map((c, i) => <div key={i} style={{ fontSize: 12.5, marginBottom: 6 }}>Config {fmtDateTime(c.at, { seconds: false })}: {c.change}</div>)}
              {(w.get_provider_status?.incidents || []).map((p, i) => <div key={i} style={{ fontSize: 12.5, marginBottom: 6 }}>{p.provider} {p.status}: {p.note}</div>)}
              {!(w.get_recent_deploys || []).length && !(w.get_config_changes || []).length && !(w.get_provider_status?.incidents || []).length &&
                <p style={{ fontSize: 12.5 }}>No deploy, config change or provider incident in the window.</p>}
            </Card>
          </Grid>
          <SectionTitle>Alerts on this page</SectionTitle>
          <Table rows={data.alerts} maxHeight={260} columns={[
            { key: "ts", label: "When", render: (r) => fmtDateTime(r.ts) },
            { key: "signal", label: "Signal" },
            { key: "monitor", label: "Monitor" },
            { key: "region", label: "Region", render: (r) => r.region || "-" },
            { key: "value", label: "Value / threshold", align: "right", render: (r) => `${fmtInt(r.value)} / ${fmtInt(r.threshold)}` },
          ]} />
        </>
      )}
    </Modal>
  );
}

export default function Monitoring() {
  const { t } = useTheme();
  const ch = useChartParts();
  const { data, error } = useApi("/api/monitoring");
  const [params, setParams] = useSearchParams();
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Monitoring" /><Loading /></>;
  const all = data.ablation.find((a) => a.rule === "All rules");
  const none = data.ablation.find((a) => a.rule === "Every alert pages");
  const daily = data.daily.map((d) => ({ day: fmtDay(d.day), paged: d.pages, removed: d.alerts - d.pages }));
  const total = data.daily.reduce((a, d) => a + d.alerts, 0);
  return (
    <>
      <PageHeader
        title="Monitoring"
        brief="Use machine learning monitoring ... and log summarisation agents to cut alert noise and speed up incident response for Place-built apps"
        subtitle={`Four weeks of alerts from ${data.tools.length} tools, from ${fmtDate(data.window.from)}, through six noise rules. The rules are judged on two numbers kept apart: pages to a person, and real incidents still paged. Every alternative setting tried is kept with what it would have missed.`}
      />
      <Grid cols={4} min={170}>
        <Stat label="Alerts" value={fmtInt(total)} sub="what reached a person before the rules" />
        <Stat label="Pages" value={fmtInt(all.pages)} emphasis sub="what reaches a person now" />
        <Stat label="Real incidents paged" value={`${all.incidents_paged} of ${data.pages.filter((p) => p.incident_id).map((p) => p.incident_id).filter((v, i, a) => a.indexOf(v) === i).length}`}
          tone="good" sub="none hidden by a rule" />
        <Stat label="Slowest page" value={`${all.minutes_to_page_max} min`} sub="after the incident's first alert" />
      </Grid>
      <SectionTitle>Every day: what was removed, what paged</SectionTitle>
      <Card>
        <ChartOrTable
          chart={(
            <ChartFrame height={260}>
              <BarChart data={daily} margin={{ top: 6, right: 8, left: 0, bottom: 0 }} barCategoryGap={3}>
                {ch.grid}
                {ch.xAxis({ dataKey: "day", interval: 3 })}
                {ch.yAxis({ allowDecimals: false, width: 40 })}
                {ch.tooltip({})}
                {ch.legend({})}
                <Bar dataKey="removed" name="Removed by a rule" stackId="a" fill={t.chart[0]} stroke={t.surface} strokeWidth={1} />
                <Bar dataKey="paged" name="Paged a person" stackId="a" fill={t.chart[1]} stroke={t.surface} strokeWidth={1} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          )}
          table={<Table rows={daily} maxHeight={300} columns={[
            { key: "day", label: "Day" }, { key: "removed", label: "Removed", align: "right" }, { key: "paged", label: "Paged", align: "right" }]} />}
        />
        <p style={{ fontSize: 12, color: t.textMuted, margin: "6px 0 0" }}>The two-day spike is one probe region flapping every ten minutes.</p>
      </Card>
      <Grid cols={2} min={340}>
        <div>
          <SectionTitle>What each rule removed</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={data.decisions} maxHeight={400} columns={[
              { key: "rule", label: "Rule", render: (r) => <b>{r.rule}</b> },
              { key: "alerts", label: "Alerts", align: "right" },
              { key: "why", label: "Why", wrap: true, render: (r) => RULE_WHY[r.rule] || "" },
            ]} />
          </Card>
        </div>
        <div>
          <SectionTitle>Each rule off, and what was tried instead</SectionTitle>
          <Card pad={0} rule={false}>
            <Table rows={data.ablation} maxHeight={400} columns={[
              { key: "rule", label: "Setting", wrap: true, render: (r) => <b>{r.rule}</b> },
              { key: "setting", label: "", render: (r) => r.setting === "tried and rejected" ? <Badge tone="warning">Rejected</Badge> : r.setting === "as configured" ? <Badge tone="good">Running</Badge> : <Badge tone="neutral">{r.setting}</Badge> },
              { key: "pages", label: "Pages", align: "right" },
              { key: "incidents_paged", label: "Incidents paged", align: "right", render: (r) => `${r.incidents_paged}${r.incidents_missed ? ` (missed ${r.incidents_missed})` : ""}` },
              { key: "minutes_to_page_max", label: "Slowest (min)", align: "right" },
            ]} />
          </Card>
        </div>
      </Grid>
      <Callout tone="warning" title="Why the cheaper settings were rejected">
        Dropping latency alerts altogether gives almost the same page count, but the database incident would have paged 25 minutes later, when its
        connection errors began rather than when it slowed. Requiring all three probe regions misses the provider outage that two regions saw.
      </Callout>
      <SectionTitle>The pages</SectionTitle>
      <Card pad={0} rule={false}>
        <Table rows={data.pages} onRowClick={(r) => setParams({ page: r.page_id })} columns={[
          { key: "page_id", label: "Page", render: (r) => <b style={{ color: t.accent }}>{r.page_id}</b> },
          { key: "opened_at", label: "Opened", render: (r) => fmtDateTime(r.opened_at, { seconds: false }) },
          { key: "tool_name", label: "Tool" },
          { key: "signals", label: "Signals", wrap: true },
          { key: "incident_id", label: "Incident", render: (r) => r.incident_id ? <Badge tone="critical">{r.incident_id}</Badge> : <Badge tone="neutral">noise</Badge> },
        ]} />
      </Card>
      <SectionTitle>Before it pages: limits and certificates</SectionTitle>
      <p style={{ fontSize: 13, margin: "0 0 10px", maxWidth: 900 }}>
        Straight-line trends over the last fourteen days, in whole numbers. Simple on purpose: it says when, and why, and it would have warned about
        the certificate that expired on 08/11.
      </p>
      <Card pad={0} rule={false}>
        <Table rows={data.forecasts} maxHeight={380} columns={[
          { key: "resource", label: "Resource", render: (r) => <Mono>{r.resource}</Mono> },
          { key: "kind", label: "What" },
          { key: "now", label: "Now", align: "right", render: (r) => r.kind.startsWith("database") ? `${r.now_value} of ${r.limit_value} MB` : "-" },
          { key: "days_left", label: "Days left", align: "right", render: (r) => r.days_left == null ? "not growing" : r.days_left },
          { key: "due_on", label: "Due", render: (r) => (r.due_on ? fmtDate(r.due_on) : "-") },
          { key: "flag", label: "", render: (r) => r.days_left != null && r.days_left < 0 ? <Badge tone="critical">Expired</Badge> : r.days_left != null && r.days_left <= 45 ? <Badge tone="warning">Act now</Badge> : null },
        ]} />
      </Card>
      <NotBuilt items={[
        "Machine-learned anomaly detection. With four weeks of history for ten small apps, a model would learn the noise; persistence, region agreement and known windows do better and can be explained to CAB. Azure Monitor's dynamic thresholds are the next step once there is a year of data.",
        "The alert sources themselves. In production these come from Azure Monitor, Application Insights and the platforms' own notifications into one action group.",
      ]} />
      <PageDetail pageId={params.get("page")} onClose={() => setParams({})} />
    </>
  );
}
