import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import puppeteer from "puppeteer-core";

const SITE = process.env.E2E_SITE ?? "http://localhost:3001";
const API = process.env.E2E_API ?? "http://localhost:8001";
const CHROME =
  process.env.CHROME_PATH ??
  [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
  ].find(existsSync);
const COMMAND = "Create a landing page for Maria's Bakery with a hero and an FAQ";
const CHAT = '[aria-label="Ask for a page, or answer the question"]';
const ADDRESS = '[aria-label="Page address"]';

function log(step) {
  console.log(`• ${step}`);
}

async function waitForApi() {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`${API}/health`);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`orchestrator not reachable at ${API}`);
}

async function publicPage(url) {
  const res = await fetch(`${SITE}${url}`, { redirect: "manual" });
  return { status: res.status, body: res.ok ? await res.text() : "" };
}

async function clickButton(page, text, { timeout = 30_000 } = {}) {
  const handle = await page.waitForFunction(
    (label) =>
      [...document.querySelectorAll("button")].find(
        (b) => b.textContent?.trim() === label && !b.disabled,
      ) ?? null,
    { timeout },
    text,
  );
  const button = handle.asElement();
  assert.ok(button, `no enabled button labelled ${text}`);
  await button.click();
}

async function buttonGone(page, text, { timeout = 30_000 } = {}) {
  await page.waitForFunction(
    (label) =>
      ![...document.querySelectorAll("button")].some(
        (b) => b.textContent?.trim() === label,
      ),
    { timeout },
    text,
  );
}

async function setBusiness(page, value) {
  await clickButton(page, "Brief");
  const input = await page.waitForSelector("section.panel label input");
  await input.evaluate((el) => el.select());
  await input.type(value);
}

async function main() {
  assert.ok(CHROME, "set CHROME_PATH to a Chrome/Chromium binary");
  await waitForApi();
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--no-sandbox"],
  });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(60_000);
    await page.setViewport({ width: 1440, height: 1000 });
    await page.goto(SITE, { waitUntil: "networkidle2" });

    log("create a page from the chat");
    await page.waitForSelector(CHAT);
    await page.type(CHAT, COMMAND);
    await page.click('[aria-label="Send"]');
    const address = await page.waitForSelector(ADDRESS);
    const url = await address.evaluate((el) => el.value);
    assert.match(url, /^\/maria-s-bakery/);
    assert.equal((await publicPage(url)).status, 404, "a draft is not public");

    log("edit the business name and save");
    await setBusiness(page, "Maria's Bakery Co");
    await clickButton(page, "Save");
    await buttonGone(page, "Save");
    await page.waitForFunction(
      () => document.querySelector("main")?.textContent?.includes("Maria's Bakery Co"),
    );

    log("publish");
    await clickButton(page, "Publish");
    await page.waitForFunction(() =>
      [...document.querySelectorAll("button")].some(
        (b) => b.textContent?.trim() === "Published",
      ),
    );
    const live = await publicPage(url);
    assert.equal(live.status, 200, "published pages are public");
    assert.ok(live.body.includes("Maria&#x27;s Bakery Co") || live.body.includes("Maria's Bakery Co"));

    log("save another draft without publishing");
    await setBusiness(page, "Maria's Bakery Ltd");
    await clickButton(page, "Save");
    await buttonGone(page, "Save");
    await page.waitForFunction(
      () => document.querySelector("main")?.textContent?.includes("Maria's Bakery Ltd"),
    );
    const still = await publicPage(url);
    assert.ok(
      still.body.includes("Bakery Co") && !still.body.includes("Bakery Ltd"),
      "a saved draft must not change the published page",
    );

    log("reopen the build from the menu");
    await page.goto(SITE, { waitUntil: "networkidle2" });
    await page.click('header button[aria-haspopup="menu"]');
    const entry = await page.waitForFunction(
      (wanted) =>
        [...document.querySelectorAll("button")].find((b) =>
          b.textContent?.includes(wanted),
        ) ?? null,
      {},
      url,
    );
    await entry.asElement().click();
    await page.waitForSelector(ADDRESS);
    await page.waitForFunction(
      () => document.querySelector("main")?.textContent?.includes("Maria's Bakery Ltd"),
    );
    const reopened = await page.$eval(ADDRESS, (el) => el.value);
    assert.equal(reopened, url);

    log("restore the first version");
    await clickButton(page, "History");
    await page.waitForFunction(() =>
      [...document.querySelectorAll("button")].some((b) =>
        b.textContent?.includes("Initial draft"),
      ),
    );
    await page.evaluate(() =>
      [...document.querySelectorAll("button")]
        .find((b) => b.textContent?.includes("Initial draft"))
        ?.click(),
    );
    await clickButton(page, "Restore");
    await page.waitForFunction(
      () => {
        const text = document.querySelector("main")?.textContent ?? "";
        return text.includes("Restored version 1");
      },
    );
    const afterRestore = await publicPage(url);
    assert.ok(
      afterRestore.body.includes("Bakery Co"),
      "restoring a draft leaves the published page alone",
    );

    console.log("\nlifecycle ok:", url);
  } finally {
    await browser.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
