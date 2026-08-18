#!/usr/bin/env node
/**
 * Validate Mermaid fenced code blocks by parsing them with mermaid.parse().
 * Usage:
 *   node validate-mermaid.mjs --root . \
 *     --include "README.md" \
 *     --include "docs/**\/*.md" \
 *     --exclude "docs/architecture/**"
 */

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { JSDOM } from 'jsdom';
import { glob } from 'glob';

const FENCE_RE = /^```mermaid[^\n]*\n([\s\S]*?)^```[ \t]*$/gm;

function parseArgs(argv) {
  const args = { root: '.', include: [], exclude: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--root') {
      args.root = argv[++i];
    } else if (arg === '--include') {
      args.include.push(argv[++i]);
    } else if (arg === '--exclude') {
      args.exclude.push(argv[++i]);
    } else {
      throw new Error(`Unrecognised argument: ${arg}`);
    }
  }
  if (args.include.length === 0) {
    throw new Error('At least one --include pattern is required.');
  }
  return args;
}

async function collectFiles(root, includes, excludes) {
  const matched = new Set();
  for (const pattern of includes) {
    const files = await glob(pattern, {
      cwd: root,
      nodir: true,
      ignore: excludes,
    });
    files.forEach((f) => matched.add(f));
  }
  return [...matched].sort();
}

function extractBlocks(content) {
  const blocks = [];
  let match;
  FENCE_RE.lastIndex = 0;
  while ((match = FENCE_RE.exec(content)) !== null) {
    blocks.push(match[1]);
  }
  return blocks;
}

async function setupMermaidDom() {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    pretendToBeVisual: true, // gives window.requestAnimationFrame etc.
  });
  global.window = dom.window;
  global.document = dom.window.document;
  global.navigator = dom.window.navigator;
  global.self = dom.window; // some libs check `self`, not `window`

  // Import mermaid only now, so it (and dompurify) see the real window
  const { default: mermaid } = await import('mermaid');
  mermaid.initialize({ startOnLoad: false });
  return mermaid;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = path.resolve(args.root);

  const mermaid = await setupMermaidDom(); // <-- now returns the module

  const files = await collectFiles(root, args.include, args.exclude);
  const errors = [];

  for (const relPath of files) {
    const absPath = path.join(root, relPath);
    const content = await readFile(absPath, 'utf-8');
    const blocks = extractBlocks(content);

    for (const [index, block] of blocks.entries()) {
      try {
        // eslint-disable-next-line no-await-in-loop
        await mermaid.parse(block);
      } catch (err) {
        errors.push(
          `${relPath} mermaid block ${index + 1}: ${err.message ?? err}`.trim(),
        );
      }
    }
  }

  if (errors.length > 0) {
    console.error(errors.join('\n\n'));
    process.exit(1);
  }

  process.exit(0);
}

main().catch((err) => {
  console.error(err.stack ?? String(err));
  process.exit(1);
});