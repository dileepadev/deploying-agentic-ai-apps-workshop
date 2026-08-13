/**
 * Pull the deck and the demo client into the Astro build.
 *
 * Both live outside website/ on purpose:
 *
 *   ../slides/index.html  is the deck's single source of truth. It still opens
 *                         standalone by double-clicking it, which matters as a
 *                         presentation fallback when a network or a build is
 *                         misbehaving.
 *   ../client/index.html  is the demo client, deployed to /demo/.
 *
 * This script derives the site's copies from those, so there is never a second
 * version to keep in sync. It runs before every build and dev server.
 */
import { mkdir, readFile, writeFile, rm, cp } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const site = path.resolve(here, "..");
const repo = path.resolve(site, "..");

const SLIDES = path.join(repo, "slides");
const CLIENT = path.join(repo, "client");

async function syncDeck() {
  const html = await readFile(path.join(SLIDES, "index.html"), "utf8");

  const body = html.match(/<body>([\s\S]*)<\/body>/);
  if (!body) throw new Error("slides/index.html has no <body> — cannot extract the deck");

  // Drop the <script src> tag; the Astro route imports the runner as a module.
  const markup = body[1].replace(/\s*<script src="[^"]*"><\/script>\s*/g, "\n").trim();

  const slides = (markup.match(/<section\b[^>]*class="[^"]*\bslide\b/g) || []).length;
  if (slides < 2) throw new Error(`only found ${slides} slides — extraction looks wrong`);

  const out = path.join(site, "src", "slides");
  await mkdir(out, { recursive: true });
  await writeFile(path.join(out, "deck.html"), markup + "\n");
  await cp(path.join(SLIDES, "assets", "css", "slides.css"), path.join(out, "slides.css"));
  await cp(path.join(SLIDES, "assets", "js", "slides.js"), path.join(out, "slides.js"));

  // Deck images are referenced relatively (assets/img/...) from /slides/.
  const img = path.join(SLIDES, "assets", "img");
  if (existsSync(img)) {
    const dest = path.join(site, "public", "slides", "assets", "img");
    await rm(dest, { recursive: true, force: true });
    await mkdir(path.dirname(dest), { recursive: true });
    await cp(img, dest, { recursive: true });
  }

  console.log(`  deck:  ${slides} slides -> src/slides/deck.html`);
}

async function syncDemo() {
  const dest = path.join(site, "public", "demo");
  await rm(dest, { recursive: true, force: true });
  await cp(CLIENT, dest, { recursive: true });
  console.log("  demo:  client/ -> public/demo/");
}

await syncDeck();
await syncDemo();
