// What every tool gets when it moves into the Place GitHub organisation.

import { useState } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useApi } from "../../lib/api.js";
import { NotBuilt } from "../../lib/place.jsx";
import { Callout, Card, ErrorNote, Grid, Loading, PageHeader, SectionTitle, SegmentedControl } from "../../lib/ui.jsx";

export default function PavedRoad() {
  const { t } = useTheme();
  const { data, error } = useApi("/api/paved-road");
  const [path, setPath] = useState("README.md");
  if (error) return <ErrorNote error={error} />;
  if (!data) return <><PageHeader title="Paved road" /><Loading /></>;
  const file = data.files.find((f) => f.path === path) || data.files[0];
  return (
    <>
      <PageHeader
        title="The paved road"
        brief="Integrate agentic tools ... into the software lifecycle ... Help staff move useful tools into Place's GitHub with proper back ends and credentials"
        subtitle="Builders keep building the way they do now, with Claude Code, Copilot or Copilot Studio. Moving into the organisation adds what a pilot skips - review, the gate in CI, dependency updates, protected branches, tagged infrastructure, a register entry - without asking anyone to become a platform engineer. These are the template's actual files, read from the repository."
      />
      <Grid cols={3} min={240}>
        <Card title="For the builder">
          <p style={{ fontSize: 13, marginTop: 0 }}>Open a pull request; the checks tell you what to fix, in a sentence. Claude Code reads the same output and fixes most of it.</p>
        </Card>
        <Card title="For the platform">
          <p style={{ fontSize: 13, marginTop: 0 }}>Every repository has the same checks, the same tags and a register entry, so the inventory, the cost report and CAB read one shape.</p>
        </Card>
        <Card title="For the managed service provider">
          <p style={{ fontSize: 13, marginTop: 0 }}>Identity, licensing and Microsoft 365 stay theirs. The platform asks for groups, not admin rights.</p>
        </Card>
      </Grid>
      <SectionTitle right={<SegmentedControl label="File" value={file.path} onChange={setPath} options={data.files.map((f) => ({ value: f.path, label: f.path.split("/").pop() }))} />}>
        {file.path}
      </SectionTitle>
      <pre style={{ margin: 0, fontSize: 12, lineHeight: 1.55, background: t.surface, border: `1px solid ${t.border}`, padding: 14, borderRadius: 10,
        overflow: "auto", maxHeight: 560, fontFamily: "'JetBrains Mono', ui-monospace, monospace", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {file.content}
      </pre>
      <Callout tone="neutral" title="Names in the template">
        The organisation name in the template is a stand-in; Place's own goes there. The gate is the same code that scans every tool on the
        Production gate page, packaged for CI.
      </Callout>
      <NotBuilt items={[
        "The platform repository the template points at - shared environment, database server, AI gateway. The module shows the shape a tool plugs into.",
        "Copilot Studio's equivalent. Agents stay in the tenant; their road is environment strategy and data loss prevention policies, which the managed service provider administers.",
      ]} />
    </>
  );
}
