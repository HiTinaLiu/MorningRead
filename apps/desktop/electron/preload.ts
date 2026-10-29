import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("desktop", {
  showInFolder: (file: string) => ipcRenderer.invoke("show-in-folder", file),
});
