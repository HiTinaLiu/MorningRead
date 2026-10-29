import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const videoSrc = fileURLToPath(new URL("../video/src", import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: "./",
  resolve: {
    alias: { "@reading": videoSrc },
    dedupe: ["react", "react-dom", "remotion", "@remotion/lottie", "lottie-web"],
  },
  server: {
    host: "127.0.0.1",
    port: 6183,
    strictPort: true,
    fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] },
  },
});
