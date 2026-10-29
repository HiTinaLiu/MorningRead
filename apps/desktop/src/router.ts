import { useEffect, useState } from "react";

export type Route = { name: "home" } | { name: "settings" } | { name: "piece"; id: string };

export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#/, "").split("/").filter(Boolean);
  if (parts[0] === "settings") return { name: "settings" };
  if (parts[0] === "piece" && parts[1]) return { name: "piece", id: decodeURIComponent(parts[1]) };
  return { name: "home" };
}

export function navigate(hash: string): void {
  window.location.hash = hash;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
