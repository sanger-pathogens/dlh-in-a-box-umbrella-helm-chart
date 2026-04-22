import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

import MarkdownIt from "markdown-it";
import markdownItAnchor from "markdown-it-anchor";
import { chromium } from "playwright";

const DOCS_DIR = path.dirname(fileURLToPath(import.meta.url));
const MANUAL_MD = path.join(DOCS_DIR, "umbrella-chart-manual.md");
const MANUAL_PDF = path.join(DOCS_DIR, "umbrella-chart-manual.pdf");
const CSS_FILE = path.join(DOCS_DIR, "manual-print.css");
const MERMAID_BROWSER_BUNDLE = path.join(
  DOCS_DIR,
  "node_modules",
  "mermaid",
  "dist",
  "mermaid.min.js"
);
const CACHE_DIR = path.join(DOCS_DIR, "node_modules", ".cache", "manual-build");
const TEMP_HTML = path.join(CACHE_DIR, "umbrella-chart-manual.html");
const DOCS_BASE_URL = pathToFileURL(`${DOCS_DIR}${path.sep}`).href;

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[`']/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function runCommand(command, args, message) {
  const binary = process.platform === "win32" ? `${command}.cmd` : command;
  const result = spawnSync(binary, args, {
    cwd: DOCS_DIR,
    stdio: "inherit",
    shell: false,
  });

  if (result.status !== 0) {
    throw new Error(`${message} failed with exit code ${result.status ?? "unknown"}.`);
  }
}

async function launchBrowser() {
  try {
    return await chromium.launch({ headless: true });
  } catch (error) {
    const text = String(error?.message || error);
    const needsInstall =
      text.includes("Executable doesn't exist") ||
      text.includes("Please run the following command");

    if (!needsInstall) {
      throw error;
    }

    console.log("Playwright Chromium is not installed yet. Installing it now...");
    runCommand("npx", ["playwright", "install", "chromium"], "Playwright browser install");
    return chromium.launch({ headless: true });
  }
}

function buildMarkdownRenderer() {
  const defaultMd = new MarkdownIt({
    html: true,
    linkify: true,
  });
  const defaultFence = defaultMd.renderer.rules.fence;

  const md = new MarkdownIt({
    html: true,
    linkify: true,
  });

  md.use(markdownItAnchor, {
    slugify,
    permalink: markdownItAnchor.permalink.headerLink(),
  });

  md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    const info = token.info.trim();

    if (info === "mermaid") {
      return `<pre class="mermaid">${md.utils.escapeHtml(token.content)}</pre>\n`;
    }

    return defaultFence(tokens, idx, options, env, self);
  };

  return md;
}

async function renderManualToHtml() {
  const markdown = await fs.readFile(MANUAL_MD, "utf8");
  const css = await fs.readFile(CSS_FILE, "utf8");
  const mermaidUrl = pathToFileURL(MERMAID_BROWSER_BUNDLE).href;
  const md = buildMarkdownRenderer();
  const body = md.render(markdown);
  const mermaidFence = JSON.stringify("```mermaid");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <base href="${DOCS_BASE_URL}" />
    <title>dlh-in-a-box Umbrella Chart Manual</title>
    <style>
${css}
    </style>
    <script src="${mermaidUrl}"></script>
  </head>
  <body>
    <main>
${body}
    </main>
    <script>
      const blocks = [...document.querySelectorAll("pre.mermaid")];
      window.__manualMermaidStatus = {
        state: "starting",
        expected: blocks.length,
      };

      window.addEventListener("load", () => {
        (async () => {
          try {
            if (!window.mermaid) {
              throw new Error("Mermaid browser bundle did not load.");
            }

            window.mermaid.initialize({
              startOnLoad: false,
              securityLevel: "strict",
              theme: "default",
              flowchart: {
                useMaxWidth: true,
                htmlLabels: true
              }
            });

            await window.mermaid.run({
              querySelector: "pre.mermaid"
            });

            const rendered = [...document.querySelectorAll("pre.mermaid svg")].length;
            const hasErrors =
              !!document.querySelector(".mermaid-error") ||
              [...document.querySelectorAll("pre.mermaid")].some((node) => !node.querySelector("svg"));
            const hasRawMermaidFence =
              document.body.innerText.includes(${mermaidFence}) ||
              !!document.querySelector("code.language-mermaid");

            if (hasErrors) {
              throw new Error("At least one Mermaid block failed to render.");
            }

            if (hasRawMermaidFence) {
              throw new Error("Raw Mermaid source is still present in the rendered DOM.");
            }

            if (rendered !== blocks.length) {
              throw new Error("Expected " + blocks.length + " Mermaid blocks but only rendered " + rendered + ".");
            }

            document.body.dataset.mermaidReady = "true";
            window.__manualMermaidStatus = {
              state: "ready",
              expected: blocks.length,
              rendered
            };
          } catch (error) {
            document.body.dataset.mermaidReady = "error";
            window.__manualMermaidStatus = {
              state: "error",
              expected: blocks.length,
              error: String(error && error.stack ? error.stack : error)
            };
            console.error(error);
          }
        })();
      });
    </script>
  </body>
</html>
`;
}

async function main() {
  await fs.mkdir(CACHE_DIR, { recursive: true });
  await fs.writeFile(TEMP_HTML, await renderManualToHtml(), "utf8");

  const browser = await launchBrowser();

  try {
    const page = await browser.newPage();
    page.on("pageerror", (error) => {
      console.error("Page error while building manual:", error);
    });
    page.on("console", (message) => {
      if (message.type() === "error") {
        console.error("Browser console error while building manual:", message.text());
      }
    });
    await page.goto(pathToFileURL(TEMP_HTML).href, {
      waitUntil: "load",
    });
    await page.emulateMedia({ media: "print" });
    await page.waitForFunction(
      () =>
        document.body?.dataset?.mermaidReady === "true" ||
        document.body?.dataset?.mermaidReady === "error",
      undefined,
      {
        timeout: 120000,
      }
    );

    const status = await page.evaluate(() => window.__manualMermaidStatus);

    if (!status || status.state !== "ready") {
      throw new Error(
        `Mermaid rendering did not complete successfully.\n${
          status?.error || "No renderer error details were captured."
        }`
      );
    }

    const domCheck = await page.evaluate(() => ({
      hasRawMermaidFence:
        document.body.innerText.includes("```mermaid") ||
        !!document.querySelector("code.language-mermaid"),
      hasMermaidError: !!document.querySelector(".mermaid-error"),
      renderedBlocks: document.querySelectorAll("pre.mermaid svg").length,
    }));

    if (domCheck.hasRawMermaidFence || domCheck.hasMermaidError) {
      throw new Error(
        `Manual DOM still contains Mermaid errors or raw Mermaid source: ${JSON.stringify(domCheck)}`
      );
    }

    await page.pdf({
      path: MANUAL_PDF,
      format: "Letter",
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: '<div></div>',
      footerTemplate:
        '<div style="width:100%;font-size:8px;color:#52606d;padding:0 0.2in;display:flex;justify-content:space-between;">' +
        '<span>dlh-in-a-box umbrella chart manual</span>' +
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>' +
        "</div>",
      margin: {
        top: "0.6in",
        right: "0.55in",
        bottom: "0.8in",
        left: "0.55in",
      },
    });
  } finally {
    await browser.close();
  }

  const pdfStat = await fs.stat(MANUAL_PDF);

  if (!pdfStat.size) {
    throw new Error("The manual PDF was created but is empty.");
  }

  console.log(`Built Markdown source: ${path.relative(process.cwd(), MANUAL_MD)}`);
  console.log(`Built PDF output: ${path.relative(process.cwd(), MANUAL_PDF)}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack : error);
  process.exitCode = 1;
});
