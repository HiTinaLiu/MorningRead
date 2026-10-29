/// <reference types="vite/client" />

interface DesktopApi {
  showInFolder: (file: string) => Promise<void>;
}

interface Window {
  desktop?: DesktopApi;
}
