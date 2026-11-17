// Drive a reader's path in a real browser: filter a report to one office,
// follow an office from the scorecard, and ask the assistant a question -
// which, with no model key, is answered from the catalogue and says so.
//
//   BASE=http://localhost:5271 node evals/flow.mjs

import { chromium } from "playwright";

const BASE = process.env.BASE || "http://localhost:5271";
const CHANNEL = process.env.BROWSER_CHANNEL || undefined;
const OUT = process.env.OUT || "./page-shots";
const browser = await chromium.launch(CHANNEL ? { channel: CHANNEL } : {});
const page = await (await browser.newContext({ viewport: { width: 1500, height: 1000 } })).newPage();
let steps = 0;
const expect = async (name, locator) => {
  await locator.first().waitFor({ timeout: 30_000 });
  steps += 1;
  console.log(`ok   ${name}`);
};

await page.goto(`${BASE}/sales`, { waitUntil: "networkidle" });
await expect("the group's sales", page.getByText("Sales - all offices"));
await page.getByLabel("Office").selectOption("K");
await expect("filtered to one office", page.getByText("Sales - Office K"));
await expect("its own agents", page.getByText("Agents in Office K"));

await page.goto(`${BASE}/offices`, { waitUntil: "networkidle" });
await page.getByText("Office D", { exact: true }).click();
await expect("an office on the scorecard opens its sales", page.getByText("Sales - Office D"));

await page.goto(`${BASE}/rentals`, { waitUntil: "networkidle" });
await expect("the arrears watch list", page.getByText("The watch list: more than 14 days in arrears"));

await page.getByRole("button", { name: "Ask the data" }).last().click({ force: true });
const box = page.getByPlaceholder("Ask about sales, rentals, arrears or marketing...");
await box.fill("Which offices have the most tenancies more than 14 days in arrears?");
await box.press("Enter");
await expect("the assistant answers with a table", page.getByText(/over_14_days|Office D/).last());
await page.screenshot({ path: `${OUT}/flow-assistant.png` });

await page.goto(`${BASE}/ask`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /DELETE FROM listing/ }).click();
await expect("the gate refuses a write", page.getByText("Refused"));

await browser.close();
console.log(`\n${steps} steps passed`);
