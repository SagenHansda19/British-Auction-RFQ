import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  const apiPort = env.API_PORT || "8000";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // forward /api to fastapi so the browser sees one origin
      proxy: { "/api": `http://localhost:${apiPort}` },
    },
  };
});
