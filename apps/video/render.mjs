import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const [propsPath, outputPath] = process.argv.slice(2);
if (!propsPath || !outputPath) {
  console.error("用法：node render.mjs <props.json> <output.mp4 | cover.png>");
  process.exit(2);
}

const emit = (message) => process.stdout.write(`${JSON.stringify(message)}\n`);
let last = "";
const progress = (stage, value) => {
  const key = `${stage}:${Math.floor(value * 100)}`;
  if (key === last) return;
  last = key;
  emit({ stage, progress: value });
};

const inputProps = JSON.parse(await fs.readFile(propsPath, "utf8"));

await ensureBrowser({
  onBrowserDownload: () => ({
    version: null,
    onProgress: ({ percent }) => progress("browser", percent),
  }),
});

const serveUrl = await bundle({
  entryPoint: path.join(here, "src", "index.ts"),
  onProgress: (percent) => progress("bundle", percent / 100),
});

if (outputPath.toLowerCase().endsWith(".png")) {
  const cover = await selectComposition({ serveUrl, id: "Cover", inputProps });
  await renderStill({ composition: cover, serveUrl, inputProps, output: outputPath, frame: 0 });
  emit({ stage: "done" });
  process.exit(0);
}

const composition = await selectComposition({ serveUrl, id: "Reading", inputProps });
emit({ stage: "meta", seconds: composition.durationInFrames / composition.fps });

await renderMedia({
  composition,
  serveUrl,
  codec: "h264",
  outputLocation: outputPath,
  inputProps,
  onProgress: ({ progress: value }) => progress("render", value),
});

emit({ stage: "done" });
