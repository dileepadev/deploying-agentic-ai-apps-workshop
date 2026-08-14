import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `base` is deliberately not set here. It's passed at build time instead:
//
//   Vercel / any root domain   npm run build                  -> base "/"
//   GitHub Pages sub-path      npm run build -- --base=/x/demo/
//
// The website's sync script passes the second form. Hard-coding a base here
// would break whichever of the two deployments didn't match it.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
