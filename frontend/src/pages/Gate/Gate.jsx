// Days 31 to 60: the production gate - what AI-written code gets wrong,
// checked in the code itself, refused or held, and priced by ablation.

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { actorName } from "../../config.js";
import { api, apiWrite, fmtDateTime, fmtInt, useApi } from "../../lib/api.js";
import { Modal, useToast } from "../../lib/kit.jsx";
import { HomeBadge, NotBuilt, OutcomeBadge, RULE_NAMES, TierBadge } from "../../lib/place.jsx";
import { Badge, Button, CTAButton, Callout, Card, ErrorNote, Grid, Loading, Mono, PageHeader, SectionTitle, SegmentedControl, Stat, Table } from "../../lib/ui.jsx";

const SAMPLE = `import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function handler(event) {
  const visit = JSON.parse(event.body);
  const sql = \`select * from visitors where buyer_email = '\${event.queryStringParameters.q}'\`;
  console.log("lookup", visit.buyer_email);
  return client.messages.create({ model: "claude-haiku-4-5", max_tokens: 400,
    messages: [{ role: "user", content: \`Summarise for \${visit.buyer_name}\` }] });
}`;

function FileView({ toolId, file, onClose }) {
  const { t } = useTheme();
  const { data, error } = useApi(file ? `/api/gate/${toolId}/file?path=${encodeURIComponent(file.path)}&head=${file.in_head}` : null);
  return (
    <Modal open={Boolean(file)} onClose={onClose} title={file ? `${file.path}${file.in_head ? "" : " (history)"}` : ""} width={860}>
      {error && <ErrorNote error={error} />}
      {data && (
        <pre style={{ margin: 0, fontSize: 12, lineHeight: 1.5, background: t.code, padding: 12, borderRadius: 8, overflow: "auto", maxHeight: "60vh",
          fontFamily: "'JetBrains Mono', ui-monospace, monospace", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {data.content || "(empty)"}
        </pre>
      )}
      <p style={{ fontSize: 11.5, color: t.textMuted, marginBottom: 0 }}>Credentials are shown masked. They are synthetic in any case.</p>
    </Modal>
  );
}

function ToolGate({ toolId, onClose, onChanged }) {
  const { t } = useTheme();
  const toast = useToast();
  const { data, error, reload } = useApi(toolId ? `/api/gate/${toolId}` : null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const act = async (path, label) => {
    setBusy(true);
    try {
      const out = await apiWrite(path);
      toast?.(`${label}: the gate now says ${out.gate}.`, { tone: "good" });
      reload();
      onChanged();
    } catch (e) {
      toast?.(`Refused: ${e.message}`, { tone: "critical", ms: 9000 });
    } finally {
      setBusy(false);
    }
  };
  const tool = data?.tool;
  return (
    <Modal open={Boolean(toolId)} onClose={onClose} title={tool ? `Gate - ${tool.name}` : "Gate"} width={940}>
      {error && <ErrorNote error={error} />}
      {!data && !error && <Loading />}
      {data && (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
            <OutcomeBadge outcome={data.result?.outcome} />
            <Badge tone="neutral">{tool.data_classes}</Badge>
            <Badge tone="neutral">{fmtInt(tool.users_30d)} users</Badge>
            <HomeBadge home={tool.home} status={tool.status} />
            <span style={{ fontSize: 12, color: t.textMuted }}>scanned {fmtDateTime(data.result?.scanned_at, { seconds: false })}</span>
          </div>
          {data.findings.length === 0 ? <Callout tone="good" title="Passes">No check finds anything in the code as it stands.</Callout> : (
            <Table rows={data.findings} maxHeight={320} columns={[
              { key: "outcome", label: "Outcome", render: (r) => <OutcomeBadge outcome={r.outcome} /> },
              { key: "rule_id", label: "Check", render: (r) => `${r.rule_id} ${RULE_NAMES[r.rule_id]}` },
              { key: "path", label: "Where", render: (r) => <Mono>{r.path}:{r.line}</Mono> },
              { key: "evidence", label: "Evidence", wrap: true, render: (r) => <Mono dim>{r.evidence}</Mono> },
              { key: "detail", label: "What to do", wrap: true },
            ]} />
          )}
          <SectionTitle>Fix it</SectionTitle>
          <p style={{ fontSize: 13, marginTop: 0 }}>
            The owner's fix branch is ready for each seeded defect. Applying it replaces the files and keeps the old versions as history - which is
            why a removed key still refuses until its rotation is recorded. The gate re-scans the code after each step; nothing is marked fixed by hand.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <CTAButton disabled={busy || !data.fixes.length} onClick={() => act(`/api/gate/${toolId}/fix`, "Fix branch applied")}>
              Apply the fix branch ({data.fixes.length} file{data.fixes.length === 1 ? "" : "s"})
            </CTAButton>
            <Button disabled={busy} onClick={() => act(`/api/gate/${toolId}/rotate`, "Rotation recorded")}>Record the key rotation</Button>
          </div>
          <p style={{ fontSize: 11.5, color: t.textMuted, marginTop: 0 }}>Acting as {actorName()}. Only the platform lead records rotations.</p>
          {data.fixes.length > 0 && (
            <ul style={{ fontSize: 12.5, paddingLeft: 18, margin: "0 0 8px" }}>{data.fixes.map((f) => <li key={f.repo + f.path}><Mono>{f.path}</Mono>: {f.note}</li>)}</ul>
          )}
          <SectionTitle>The code ({data.files.length} files, history included)</SectionTitle>
          <Table rows={data.files} maxHeight={260} onRowClick={(r) => setFile(r)} columns={[
            { key: "path", label: "File", render: (r) => <span style={{ color: t.accent, fontWeight: 650 }}>{r.path}</span> },
            { key: "in_head", label: "Version", render: (r) => r.in_head ? "current" : <Badge tone="neutral">history</Badge> },
            { key: "commit_sha", label: "Commit", render: (r) => <Mono>{r.commit_sha}</Mono> },
            { key: "bytes", label: "Bytes", align: "right" },
          ]} />
          <FileView toolId={toolId} file={file} onClose={() => setFile(null)} />
        </>
      )}
    </Modal>
  );
}

function TryIt() {
  const { t } = useTheme();
  const [code, setCode] = useState(SAMPLE);
  const [path, setPath] = useState("netlify/functions/handler.js");
  const [personal, setPersonal] = useState(true);
  const [out, setOut] = useState(null);
  const [err, setErr] = useState(null);
  const run = async () => {
    setErr(null);
    try {
      setOut(await api("/api/gate/try", { method: "POST", body: { content: code, path, personal } }));
    } catch (e) {
      setErr(e);
    }
  };
  return (
    <Card title="Try it on your own code" hint="Paste a file. The checks run on it and nothing is stored. The sample has three problems.">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <label style={{ fontSize: 12, color: t.textMuted, display: "flex", gap: 6, alignItems: "center" }}>
          Path <input aria-label="Path" value={path} onChange={(e) => setPath(e.target.value)} style={{ fontFamily: "inherit", fontSize: 12.5, padding: "4px 8px",
            border: `1px solid ${t.border}`, borderRadius: 8, background: t.surface, color: t.text, minWidth: 0, width: 240 }} />
        </label>
        <label style={{ fontSize: 12, color: t.textMuted, display: "flex", gap: 6, alignItems: "center" }}>
          <input type="checkbox" checked={personal} onChange={(e) => setPersonal(e.target.checked)} /> The tool holds personal information
        </label>
      </div>
      <textarea aria-label="Code to check" value={code} onChange={(e) => setCode(e.target.value)} rows={12} spellCheck={false} style={{
        width: "100%", fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: 12, padding: 10, borderRadius: 8,
        border: `1px solid ${t.border}`, background: t.code, color: t.text, resize: "vertical" }} />
      <div style={{ marginTop: 8 }}><CTAButton onClick={run}>Run the gate</CTAButton></div>
      {err && <div style={{ marginTop: 10 }}><ErrorNote error={err} /></div>}
      {out && (
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 6 }}><OutcomeBadge outcome={out.outcome} /></div>
          <Table rows={out.findings} empty="No findings." columns={[
            { key: "outcome", label: "Outcome", render: (r) => <OutcomeBadge outcome={r.outcome} /> },
            { key: "name", label: "Check", render: (r) => `${r.rule_id} ${r.name}` },
            { key: "line", label: "Line", align: "right" },
            { key: "detail", label: "What to do", wrap: true },
          ]} />
        </div>
      )}
    </Card>
  );
}

export default function Gate() {
  const { t } = useTheme();
  const { data, error, reload } = useApi("/api/gate");
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState("all");
  const toolId = params.get("tool");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Production gate" /><Loading /></>;
  const count = (o) => data.results.filter((r) => r.outcome === o).length;
  const byRule = Object.fromEntries(data.by_rule.map((r) => [r.rule_id, r]));
  const shown = data.results.filter((r) => view === "all" || r.outcome === view);
  return (
    <>
      <PageHeader
        title="Production gate"
        brief="Run guardrails, security checks, code review and data compliance so AI-generated code or commands cannot put vulnerabilities into production"
        subtitle="Eleven checks, aimed at what AI-written pilot code tends to get wrong, run over every tool's code and configuration - history included. A finding refuses the tool, or holds it for a person; nothing is a warning to scroll past. Each check is priced by switching it off and counting what would then reach production."
      />
      <Grid cols={4} min={170}>
        <Stat label="Refused" value={count("refuse")} tone="critical" sub="cannot reach production until fixed" />
        <Stat label="Held for a person" value={count("hold")} tone="warning" sub="a reviewer decides" />
        <Stat label="Pass" value={count("pass")} tone="good" sub="no check finds anything" />
        <Stat label="Checks" value={data.rules.length} emphasis sub={`registry snapshot of ${data.registry_size} packages, ${data.advisories.length} advisories`} />
      </Grid>
      <SectionTitle right={<SegmentedControl label="Show" value={view} onChange={setView} options={[
        { value: "all", label: "All" }, { value: "refuse", label: "Refused" }, { value: "hold", label: "Held" }, { value: "pass", label: "Pass" }]} />}>
        Every tool, scanned
      </SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={560} rows={shown} onRowClick={(r) => setParams({ tool: r.tool_id })} columns={[
          { key: "name", label: "Tool", render: (r) => <b style={{ color: t.accent }}>{r.name}</b> },
          { key: "outcome", label: "Gate", render: (r) => <OutcomeBadge outcome={r.outcome} /> },
          { key: "rules", label: "Checks that found something", wrap: true, render: (r) => (r.rules || "-").split(", ").map((x) => RULE_NAMES[x] || x).join(", ") },
          { key: "tier", label: "Tier", render: (r) => <TierBadge tier={r.tier} /> },
          { key: "users_30d", label: "Users", align: "right" },
          { key: "fixes", label: "Fix ready", render: (r) => r.fixes ? "yes" : "-" },
        ]} />
      </Card>
      <SectionTitle>The checks</SectionTitle>
      <Card pad={0} rule={false}>
        <Table maxHeight={560} rows={data.rules} columns={[
          { key: "rule_id", label: "Check", render: (r) => <b>{r.rule_id} {r.name}</b> },
          { key: "what", label: "What it catches", wrap: true },
          { key: "tools", label: "Tools", align: "right", render: (r) => byRule[r.rule_id]?.tools ?? 0 },
          { key: "refusals", label: "Refusals", align: "right", render: (r) => byRule[r.rule_id]?.refusals ?? 0 },
          { key: "holds", label: "Holds", align: "right", render: (r) => byRule[r.rule_id]?.holds ?? 0 },
        ]} />
      </Card>
      <SectionTitle>What each check is worth</SectionTitle>
      <p style={{ fontSize: 13, margin: "0 0 10px", maxWidth: 900, lineHeight: 1.55 }}>
        Switch one check off, scan again, and count the tools that would then pass - and what they hold. A tool another check also refuses stays
        caught, which is the point of having more than one. Exposure is kept apart from effort: records and keys, not hours.
      </p>
      <Card pad={0} rule={false}>
        <Table maxHeight={480} rows={data.ablation} columns={[
          { key: "rule_id", label: "Check switched off", render: (r) => `${r.rule_id} ${RULE_NAMES[r.rule_id]}` },
          { key: "tools_through", label: "Tools that would pass", align: "right" },
          { key: "personal_records_exposed", label: "Personal records in them", align: "right", render: (r) => fmtInt(r.personal_records_exposed) },
          { key: "live_secrets", label: "Live keys shipped", align: "right" },
          { key: "users_exposed", label: "Their users", align: "right" },
          { key: "tools", label: "Which", wrap: true, render: (r) => r.tools || "-" },
        ]} />
      </Card>
      <SectionTitle>Refuse or hold</SectionTitle>
      <Grid cols={2} min={320}>
        <Callout tone="critical" title="Refuse">
          A live key in the code or unrotated in history; a privileged key in the browser; personal data readable by anyone; SQL built from input; a
          function that hands personal data to anyone; personal data to a model on a personal key; a package no registry publishes; a critical
          advisory; an agent connected to personal storage.
        </Callout>
        <Callout tone="warning" title="Hold for a person">
          A key-shaped string in a test file; a model call outside the gateway with no personal data; a high or moderate advisory; personal details
          in logs; a function without a caller check on non-personal data. Each needs judgement the check cannot make.
        </Callout>
      </Grid>
      <TryIt />
      <NotBuilt items={[
        "A full static analyser. CodeQL and dependency review run beside the gate on the paved road; the gate's checks are the ones specific to how pilot tools go wrong.",
        "Real advisories: the three here are synthetic, so nothing claims a real package is vulnerable. In CI the advisory feed is GitHub's.",
        "Rotating the key itself. That happens in the provider's console; the platform records that it was done, by whom, and re-scans.",
      ]} />
      <ToolGate toolId={toolId} onClose={() => setParams({})} onChanged={reload} />
    </>
  );
}
