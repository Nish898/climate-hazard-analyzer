import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
  build: {
    rollupOptions: {
      // Separate long-lived vendor chunks keep the app chunk small and let the browser cache libraries across deploys.
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["chart.js", "react-chartjs-2"],
          map: ["leaflet", "react-leaflet"],
        },
      },
    },
  },
});
