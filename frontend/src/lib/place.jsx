// Small pieces every report uses: money, change on last year, the office
// picker, and the "not built here" list.

import { useSearchParams } from "react-router-dom";
import { useTheme } from "../context/ThemeContext.jsx";
import { fmtAud, fmtInt, useApi } from "./api.js";
import { Badge, SectionTitle, Select } from "./ui.jsx";

export function dollars(v, opts) {
  return v == null ? "-" : fmtAud(Number(v), { decimals: 0, ...opts });
}

export function millions(v) {
  return v == null ? "-" : `$${(Number(v) / 1_000_000).toFixed(1)}M`;
}

// Change on the same days last year, in words a reader can trust: up, down,
// or level, with the figure. Colour never carries it alone.
export function Change({ now, then, lowerIsBetter = false, unit = "%" }) {
  if (now == null || then == null || Number(then) === 0) return null;
  const pct = ((Number(now) - Number(then)) / Math.abs(Number(then))) * 100;
  if (Math.abs(pct) < 0.5) return <Badge tone="neutral">level with last year</Badge>;
  const up = pct > 0;
  const good = lowerIsBetter ? !up : up;
  return <Badge tone={good ? "good" : "warning"}>{up ? "up" : "down"} {Math.abs(pct).toFixed(1)}{unit} on last year</Badge>;
}

export function changeText(now, then) {
  if (now == null || then == null || Number(then) === 0) return "";
  const pct = ((Number(now) - Number(then)) / Math.abs(Number(then))) * 100;
  return `${pct >= 0 ? "up" : "down"} ${Math.abs(pct).toFixed(1)}% on the same days last year (${fmtInt(then)})`;
}

export function useOffice() {
  const [params, setParams] = useSearchParams();
  const office = params.get("office") || "";
  const set = (v) => setParams(v ? { office: v } : {});
  return [office, set];
}

export function OfficePicker({ office, onChange }) {
  const { data } = useApi("/api/meta");
  const options = [{ value: "", label: "All 26 offices" }, ...(data?.offices || []).map((o) => ({ value: o.office_code, label: `${o.office} (${o.region})` }))];
  return <Select label="Office" value={office} onChange={onChange} options={options} />;
}

export function NotBuilt({ items }) {
  const { t } = useTheme();
  return (
    <>
      <SectionTitle>Deliberately not built here</SectionTitle>
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.65, color: t.textMuted, maxWidth: 900 }}>
        {items.map((i) => <li key={i}>{i}</li>)}
      </ul>
    </>
  );
}

export function Assumption({ children }) {
  const { t } = useTheme();
  return <p style={{ fontSize: 12, color: t.textMuted, margin: "8px 0 0", maxWidth: 900 }}><b>Assumption:</b> {children}</p>;
}
