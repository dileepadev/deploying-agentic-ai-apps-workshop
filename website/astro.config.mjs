// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";

// The site is served from a GitHub Pages project page, so everything lives
// under /<repo>/. Override with BASE_PATH="/" when serving from a custom domain.
const base = process.env.BASE_PATH ?? "/deploying-agentic-ai-apps-workshop";

export default defineConfig({
  site: "https://dileepadev.github.io",
  base,
  trailingSlash: "always",
  outDir: "./_site",

  vite: {
    plugins: [tailwindcss()],
  },

  integrations: [
    starlight({
      title: "Deploying Agentic AI",
      description:
        "Ship a multi-step AI agent on a 100% free stack — without it timing out.",

      logo: { src: "./src/assets/logo.svg", replacesTitle: false },
      favicon: "/favicon.svg",

      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/dileepadev/deploying-agentic-ai-apps-workshop",
        },
      ],

      customCss: ["./src/styles/theme.css"],

      // The deck is a full-bleed route outside the docs shell, so it gets a
      // plain link rather than a sidebar entry.
      components: {
        Head: "./src/components/Head.astro",
      },

      sidebar: [
        { label: "Home", link: "/" },
        {
          label: "Learn",
          items: [
            { label: "Overview", slug: "learn" },
            { label: "1 · From chatbot to agent", slug: "learn/agents" },
            { label: "2 · Anatomy of an agent", slug: "learn/anatomy" },
            { label: "3 · Tool calling", slug: "learn/tool-calling" },
            { label: "4 · MCP", slug: "learn/mcp" },
            { label: "5 · Memory and RAG", slug: "learn/memory" },
            { label: "6 · Guardrails", slug: "learn/guardrails" },
            {
              label: "7 · Why deployment is hard",
              slug: "learn/deployment-problem",
            },
          ],
        },
        {
          label: "Build",
          items: [
            { label: "Overview", slug: "build" },
            { label: "Step 1 · Set up", slug: "build/01-setup" },
            { label: "Step 2 · The database", slug: "build/02-database" },
            { label: "Step 3 · Tools over MCP", slug: "build/03-tools" },
            { label: "Step 4 · The loop by hand", slug: "build/04-manual-loop" },
            { label: "Step 5 · With a framework", slug: "build/05-framework" },
            { label: "Step 6 · The wrong way", slug: "build/06-the-wrong-way" },
            { label: "Step 7 · Accept and poll", slug: "build/07-accept-and-poll" },
            { label: "Step 8 · Deploy", slug: "build/08-deploy" },
          ],
        },
        {
          label: "Stack",
          items: [
            { label: "The stack", slug: "stack" },
            { label: "Model providers", slug: "stack/llm-providers" },
            { label: "Architecture", slug: "stack/architecture" },
          ],
        },
        {
          label: "Deploy",
          items: [
            { label: "Overview", slug: "deploy" },
            { label: "Render", slug: "deploy/render" },
            { label: "FastAPI Cloud", slug: "deploy/fastapi-cloud" },
            { label: "Troubleshooting", slug: "deploy/troubleshooting" },
          ],
        },
        {
          label: "Presentation",
          items: [
            { label: "About the deck", slug: "deck" },
            { label: "Open slides ↗", link: "/slides/", attrs: { target: "_blank" } },
            { label: "Open demo ↗", link: "/demo/", attrs: { target: "_blank" } },
          ],
        },
      ],

      lastUpdated: false,
      pagination: true,
      editLink: { baseUrl: undefined },
    }),
  ],
});
