// Drive a visitor's path in a real browser - no token: approving your own
// change refused, a second CAB member's approval recorded, implementation
// refused to anyone but the platform lead, then a fix branch that still
// refuses until the key's rotation is recorded. The token is used only for
// the reset at the end, which visitors cannot do.
//
//   BASE=http://localhost:5271 TOKEN=<DEMO_WRITE_TOKEN> node evals/flow.mjs

import { chromium } from "playwright";

const BASE = process.env.BASE || "http://localhost:5271";
const TOKEN = process.env.TOKEN || "";
const CHANNEL = process.env.BROWSER_CHANNEL || undefined;
const OUT = process.env.OUT || "./page-shots";
const browser = await chromium.launch(CHANNEL ? { channel: CHANNEL } : {});
const page = await (await browser.newContext({ viewport: { width: 1500, height: 1000 } })).newPage();
let steps = 0;
const expect = async (name, locator) => {
  await locator.first().waitFor({ timeout: 25_000 });
  steps += 1;
  console.log(`ok   ${name}`);
};
const actAs = async (who, url) => {
  await page.evaluate((w) => sessionStorage.setItem("place_demo_actor", w), who);
  await page.goto(url, { waitUntil: "networkidle" });
};

await page.goto(`${BASE}/changes`, { waitUntil: "networkidle" });
await expect("a visitor gets the open demo, no token", page.getByText("Open demo: changes reset when idle"));

await actAs("CAB - Head of Innovation", `${BASE}/changes`);
await page.getByLabel("Decision note for CR-006").fill("Approving my own again.");
await page.getByTitle("Approve CR-006").click();
await expect("the proposer cannot decide their own change", page.getByText(/You proposed this change, so you cannot decide it/));

await actAs("CAB - Business Systems", `${BASE}/changes`);
await page.getByLabel("Decision note for CR-006").fill("Nobody uses it; the owner has left.");
await page.getByTitle("Approve CR-006").click();
await expect("another CAB member approves it", page.getByText("CR-006 approved."));

await actAs("Builder - Mia K.", `${BASE}/changes`);
await page.getByTitle("Implement CR-006").click();
await expect("only the platform lead implements", page.getByText(/The platform lead implements approved changes/));

await actAs("Platform lead", `${BASE}/changes`);
await page.getByTitle("Implement CR-006").click();
await expect("the platform lead implements it", page.getByText("CR-006 implemented."));

await page.goto(`${BASE}/gate?tool=T-030`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /Apply the fix branch/ }).click();
await expect("the fix branch removes the key, but the gate still refuses", page.getByText("Fix branch applied: the gate now says refuse."));
await page.getByRole("button", { name: "Record the key rotation" }).click();
await expect("recording the rotation lets it pass", page.getByText("Rotation recorded: the gate now says pass."));
await page.screenshot({ path: `${OUT}/flow-gate.png`, fullPage: false });

await page.goto(`${BASE}/changes`, { waitUntil: "networkidle" });
await expect("both refusals are in the audit log", page.getByText(/You proposed this change/).first());

const reset = await page.evaluate(async (tok) => (await fetch("/api/reset", { method: "POST", headers: { "X-Write-Token": tok } })).status, TOKEN);
if (reset !== 200) throw new Error(`reset returned ${reset}`);
await browser.close();
console.log(`\n${steps} steps passed`);
