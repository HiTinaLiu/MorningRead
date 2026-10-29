import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Home } from "./pages/Home";
import { PiecePage } from "./pages/Piece";
import { SettingsPage } from "./pages/Settings";
import { navigate, useRoute } from "./router";
import "./styles.css";

function App() {
  const route = useRoute();
  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => navigate("#/")}>
          英语晨读
        </button>
        <nav>
          <button className={route.name === "home" ? "active" : ""} onClick={() => navigate("#/")}>
            篇目
          </button>
          <button className={route.name === "settings" ? "active" : ""} onClick={() => navigate("#/settings")}>
            设置
          </button>
        </nav>
      </header>
      {route.name === "home" ? <Home /> : null}
      {route.name === "settings" ? <SettingsPage /> : null}
      {route.name === "piece" ? <PiecePage id={route.id} /> : null}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
