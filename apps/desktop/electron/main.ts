import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import { spawn, spawnSync, type ChildProcess } from "child_process";
import fs from "fs";
import http from "http";
import path from "path";

const API = "http://127.0.0.1:8776";

let apiProcess: ChildProcess | null = null;

function repoRoot(): string {
  return path.resolve(__dirname, "..", "..", "..");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function checkHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const request = http.get(`${API}/health`, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.on("error", () => resolve(false));
    request.setTimeout(1500, () => {
      request.destroy();
      resolve(false);
    });
  });
}

function resolvePython(): string {
  const root = repoRoot();
  const venvPython =
    process.platform === "win32"
      ? path.join(root, "services", "api", ".venv", "Scripts", "python.exe")
      : path.join(root, "services", "api", ".venv", "bin", "python");
  if (fs.existsSync(venvPython)) return venvPython;
  const candidates = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];
  for (const command of candidates) {
    const check = spawnSync(command, ["--version"], { encoding: "utf8" });
    if (check.status === 0) return command;
  }
  return "python";
}

async function ensureApi(): Promise<void> {
  if (await checkHealth()) return;
  const python = resolvePython();
  const root = repoRoot();
  const args =
    python === "py"
      ? ["-3", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8776"]
      : ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8776"];
  apiProcess = spawn(python, args, {
    cwd: path.join(root, "services", "api"),
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      MORNINGREAD_ROOT: root,
      MORNINGREAD_DATA_DIR: app.getPath("userData"),
    },
    stdio: "inherit",
  });
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (await checkHealth()) return;
    await sleep(500);
  }
  throw new Error(
    "晨读接口没有启动。请先创建 Python 环境并安装依赖：python -m venv services/api/.venv，然后用该环境执行 pip install -r services/api/requirements.txt",
  );
}

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: "#f6efe4",
    title: "英语晨读",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  if (process.env.ELECTRON_RENDERER_URL) {
    void window.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    void window.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(async () => {
  try {
    await ensureApi();
  } catch (error) {
    dialog.showErrorBox("英语晨读", error instanceof Error ? error.message : "接口启动失败");
  }
  createWindow();
});

app.on("window-all-closed", () => {
  if (apiProcess && !apiProcess.killed) apiProcess.kill();
  app.quit();
});

ipcMain.handle("show-in-folder", (_event, file: string) => {
  if (typeof file === "string" && fs.existsSync(file)) shell.showItemInFolder(file);
});
