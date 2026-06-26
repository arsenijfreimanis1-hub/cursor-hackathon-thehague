import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const base = process.env.VITE_BASE_PATH ?? "/";

export default defineConfig({
  base,
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico"],
      manifest: {
        name: "Rekentafel Waiter",
        short_name: "Waiter",
        description: "Rekentafel bedienings-app voor obers",
        theme_color: "#16213e",
        background_color: "#1a1a2e",
        display: "standalone",
        orientation: "portrait",
        start_url: base,
        scope: base,
        lang: "nl",
        icons: [
          {
            src: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'><rect fill='%2316213e' width='512' height='512' rx='96'/><text x='256' y='300' font-size='200' text-anchor='middle' fill='white'>RT</text></svg>",
            sizes: "512x512",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        navigateFallback: `${base}index.html`,
        globPatterns: ["**/*.{js,css,html,ico,svg,woff2}"],
      },
    }),
  ],
  server: { port: 5174, host: true, strictPort: true },
});
