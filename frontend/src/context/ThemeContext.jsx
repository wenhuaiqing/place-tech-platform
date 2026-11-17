import { createContext, useContext, useEffect, useState } from "react";

// Place's palette, taken from their public website (eplace.com.au): the logo
// and the site stylesheet. Used for an application demo that is not
// affiliated with them - the sidebar says so on every page.
//
//   navy       #090A39  the logo's colour; chrome - sidebar, hero tiles, primary buttons
//   teal       #128190  the site's section and focus colour; brand accents -
//                       active nav, card rules, tab marks. Chrome only: never
//                       the only signal of a status, and badges carry labels.
//   deep teal  #0F5068  the site's hover colour, 8:1 on white: links, controls, chart series
//   slate      #2E3C48  the site's body text
//   violet     #5847C9  anything the AI agent produced, so "the model said this"
//                       is never confused with "the data says this"

export const light = {
  name: "light",
  bg: "#F3F4F7",
  surface: "#FFFFFF",
  surfaceRaised: "#F8F9FB",
  border: "rgba(9,10,57,0.12)",
  borderBright: "rgba(9,10,57,0.28)",
  accent: "#0F5068",
  accentText: "#FFFFFF",
  accentGlow: "rgba(18,129,144,0.12)",
  accent2: "#5847C9",
  accent2Glow: "rgba(88,71,201,0.10)",
  brand: "#128190",
  text: "#2E3C48",
  textMuted: "rgba(46,60,72,0.72)",
  textDim: "rgba(46,60,72,0.38)",

  sidebarBg: "#090A39",
  sidebarText: "rgba(255,255,255,0.82)",
  sidebarActive: "rgba(18,129,144,0.34)",
  sidebarActiveText: "#FFFFFF",
  sidebarBorder: "rgba(255,255,255,0.12)",
  sidebarMark: "#3FB4C3",
  sidebarMuted: "rgba(255,255,255,0.66)",
  sidebarGroup: "rgba(255,255,255,0.55)",

  headerBg: "#FFFFFF",
  headerText: "#090A39",
  headerMuted: "rgba(46,60,72,0.70)",
  headerBorder: "#EAEBF0",
  headerAccent: "#128190",

  ctaBg: "#090A39",
  ctaText: "#FFFFFF",
  ctaHoverBg: "#128190",
  ctaHoverText: "#FFFFFF",

  cardRule: "#128190",
  tableHead: "#EEF0F4",
  statHeroBg: "#090A39",
  statHeroText: "#FFFFFF",
  statHeroMuted: "rgba(255,255,255,0.76)",
  rowHover: "rgba(18,129,144,0.07)",
  rowDivider: "rgba(9,10,57,0.08)",
  grid: "rgba(9,10,57,0.09)",
  code: "rgba(9,10,57,0.06)",
  labelColBg: "rgba(9,10,57,0.05)",
  series: ["#0F5068", "#090A39", "#8A97A6", "#B4562A", "#128190"],
  // Chart marks: the brand teal lifted to the chroma floor, and an orange.
  // Validated (lightness, chroma, colour-blind separation, contrast) on white.
  chart: ["#008C9E", "#C2662F"],
  status: { good: "#1F7A5A", warning: "#8A6410", serious: "#B4562A", critical: "#B0122B", neutral: "#58646E", ai: "#5847C9" },
  statusBg: {
    good: "rgba(31,122,90,0.10)", warning: "rgba(227,162,59,0.20)", serious: "rgba(180,86,42,0.12)",
    critical: "rgba(176,18,43,0.09)", neutral: "rgba(9,10,57,0.06)", ai: "rgba(88,71,201,0.10)",
  },
};

export const dark = {
  name: "dark",
  bg: "#0A0B1A",
  surface: "#13152A",
  surfaceRaised: "#191B33",
  border: "rgba(226,230,240,0.12)",
  borderBright: "rgba(226,230,240,0.26)",
  accent: "#5CC7D4",
  accentText: "#06111A",
  accentGlow: "rgba(92,199,212,0.16)",
  accent2: "#A99BFF",
  accent2Glow: "rgba(169,155,255,0.14)",
  brand: "#3FB4C3",
  text: "#E6E9F0",
  textMuted: "rgba(230,233,240,0.68)",
  textDim: "rgba(230,233,240,0.34)",

  sidebarBg: "#090A39",
  sidebarText: "rgba(230,233,240,0.80)",
  sidebarActive: "rgba(18,129,144,0.38)",
  sidebarActiveText: "#FFFFFF",
  sidebarBorder: "rgba(230,233,240,0.12)",
  sidebarMark: "#3FB4C3",
  sidebarMuted: "rgba(230,233,240,0.64)",
  sidebarGroup: "rgba(230,233,240,0.52)",

  headerBg: "#0F1124",
  headerText: "#E6E9F0",
  headerMuted: "rgba(230,233,240,0.64)",
  headerBorder: "rgba(230,233,240,0.10)",
  headerAccent: "#5CC7D4",

  ctaBg: "#128190",
  ctaText: "#FFFFFF",
  ctaHoverBg: "#FFFFFF",
  ctaHoverText: "#090A39",

  cardRule: "#3FB4C3",
  tableHead: "#1B1E38",
  statHeroBg: "#1C2160",
  statHeroText: "#FFFFFF",
  statHeroMuted: "rgba(255,255,255,0.76)",
  rowHover: "rgba(92,199,212,0.08)",
  rowDivider: "rgba(230,233,240,0.08)",
  grid: "rgba(230,233,240,0.10)",
  code: "rgba(230,233,240,0.08)",
  labelColBg: "rgba(0,0,0,0.26)",
  series: ["#5CC7D4", "#E6E9F0", "#7E8AA0", "#E0935F", "#3FB4C3"],
  chart: ["#1E9DAE", "#D07A45"],
  status: { good: "#5FCFA4", warning: "#E6B655", serious: "#E0935F", critical: "#F0808F", neutral: "#AEB6C4", ai: "#A99BFF" },
  statusBg: {
    good: "rgba(95,207,164,0.14)", warning: "rgba(230,182,85,0.16)", serious: "rgba(224,147,95,0.16)",
    critical: "rgba(240,128,143,0.14)", neutral: "rgba(230,233,240,0.08)", ai: "rgba(169,155,255,0.16)",
  },
};

const Ctx = createContext(null);
const KEY = "place-demo:theme";

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    try { return localStorage.getItem(KEY) === "dark"; } catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem(KEY, isDark ? "dark" : "light"); } catch { /* storage blocked */ }
    document.body.style.background = (isDark ? dark : light).bg;
  }, [isDark]);
  return (
    <Ctx.Provider value={{ t: isDark ? dark : light, isDark, toggle: () => setIsDark((v) => !v) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useTheme() {
  return useContext(Ctx);
}
