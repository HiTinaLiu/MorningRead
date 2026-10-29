import { useEffect, useState } from "react";
import { api } from "../api";
import { navigate } from "../router";
import type { Catalog } from "../types";

function clock(seconds: number): string {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function Home() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .catalog()
      .then(setCatalog)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "没有连上晨读接口"));
  }, []);

  return (
    <main className="page">
      <div className="hero">
        <div>
          <p className="eyebrow">{catalog?.level || "小学低年级"}</p>
          <h1>{catalog?.title || "英语晨读"}</h1>
          <p className="lede">{catalog?.notes || "按句分页：英文朗读，中文只显示。读完留一段空白，给孩子跟读。"}</p>
        </div>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="piece-grid">
        {(catalog?.pieces ?? []).map((piece) => (
          <button key={piece.id} className="piece-card" onClick={() => navigate(`#/piece/${encodeURIComponent(piece.id)}`)}>
            <span className="piece-file">{piece.file}</span>
            <strong>{piece.title}</strong>
            <span className="muted">{piece.basedOn.join(" · ")}</span>
            <span className="piece-meta">
              <em>
                {piece.count} 句{piece.edited ? " · 已改" : ""}
              </em>
              <em>{piece.hasVideo && piece.seconds ? `已生成 ${clock(piece.seconds)}` : "未生成"}</em>
            </span>
          </button>
        ))}
      </div>
    </main>
  );
}
