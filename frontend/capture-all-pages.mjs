import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const BASE_URL = "http://localhost:5173";
const OUTPUT_DIR = path.resolve("ui-screenshots");
const MAX_PAGES = 50;

// Add dynamic Wizard routes here if needed.
const EXTRA_ROUTES = [
  "/",
  "/projects",
];

function normalizeUrl(value) {
  try {
    const url = new URL(value, BASE_URL);

    if (url.origin !== new URL(BASE_URL).origin) {
      return null;
    }

    url.hash = "";

    return url.href;
  } catch {
    return null;
  }
}

function createFileName(urlString, index) {
  const url = new URL(urlString);

  let name = decodeURIComponent(url.pathname)
    .replace(/^\/+|\/+$/g, "")
    .replace(/[^a-zA-Z0-9\u0600-\u06FF_-]+/g, "-")
    .replace(/-+/g, "-");

  if (!name) {
    name = "home";
  }

  return `${String(index).padStart(2, "0")}-${name}.png`;
}

async function collectInternalLinks(page) {
  return page.locator("a[href]").evaluateAll(
    (links, baseUrl) => {
      const baseOrigin = new URL(baseUrl).origin;

      return links
        .map((link) => link.href)
        .filter(Boolean)
        .filter((href) => {
          try {
            const url = new URL(href);

            const isInternal = url.origin === baseOrigin;
            const isAsset =
              /\.(png|jpg|jpeg|gif|svg|webp|pdf|zip|mp4|mp3|wav)$/i.test(
                url.pathname,
              );

            return isInternal && !isAsset;
          } catch {
            return false;
          }
        });
    },
    BASE_URL,
  );
}

await fs.rm(OUTPUT_DIR, {
  recursive: true,
  force: true,
});

await fs.mkdir(OUTPUT_DIR, {
  recursive: true,
});

const browser = await chromium.launch({
  headless: true,
});

const context = await browser.newContext({
  viewport: {
    width: 1440,
    height: 1000,
  },
  locale: "ar-SA",
  colorScheme: "light",
});

const page = await context.newPage();

const pendingUrls = EXTRA_ROUTES
  .map((route) => normalizeUrl(route))
  .filter(Boolean);

const visitedUrls = new Set();
const results = [];

while (
  pendingUrls.length > 0 &&
  visitedUrls.size < MAX_PAGES
) {
  const currentUrl = pendingUrls.shift();
  const normalizedUrl = normalizeUrl(currentUrl);

  if (!normalizedUrl || visitedUrls.has(normalizedUrl)) {
    continue;
  }

  visitedUrls.add(normalizedUrl);

  console.log(`Opening: ${normalizedUrl}`);

  try {
    const response = await page.goto(normalizedUrl, {
      waitUntil: "networkidle",
      timeout: 30000,
    });

    await page.evaluate(async () => {
      await document.fonts.ready;
    });

    await page.waitForTimeout(1500);

    const fileName = createFileName(
      normalizedUrl,
      visitedUrls.size,
    );

    await page.screenshot({
      path: path.join(OUTPUT_DIR, fileName),
      fullPage: true,
      animations: "disabled",
    });

    console.log(`Saved: ${fileName}`);

    results.push({
      url: normalizedUrl,
      title: await page.title(),
      status: response?.status() ?? null,
      screenshot: fileName,
    });

    const links = await collectInternalLinks(page);

    for (const link of links) {
      const normalizedLink = normalizeUrl(link);

      if (
        normalizedLink &&
        !visitedUrls.has(normalizedLink) &&
        !pendingUrls.includes(normalizedLink)
      ) {
        pendingUrls.push(normalizedLink);
      }
    }
  } catch (error) {
    console.error(`Failed: ${normalizedUrl}`);
    console.error(error.message);

    results.push({
      url: normalizedUrl,
      error: error.message,
    });
  }
}

await fs.writeFile(
  path.join(OUTPUT_DIR, "report.json"),
  JSON.stringify(results, null, 2),
  "utf8",
);

await browser.close();

console.log("");
console.log(`Finished. Captured ${results.length} pages.`);
console.log(`Screenshots saved in: ${OUTPUT_DIR}`);