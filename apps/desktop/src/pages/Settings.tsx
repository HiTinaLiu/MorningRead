import { useEffect, useState } from "react";
import { api } from "../api";
import type { Settings } from "../types";

export function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [pixabayKey, setPixabayKey] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    api
      .settings()
      .then(setForm)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "读不到设置"));
  }, []);

  async function save() {
    setError("");
    setSaved("");
    try {
      const next = await api.saveSettings(pixabayKey.trim() ? pixabayKey.trim() : null);
      setForm(next);
      setPixabayKey("");
      setSaved("已保存");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  return (
    <main className="page settings">
      <h1>设置</h1>
      <p className="lede">配图先用 Twemoji。没有表情时，按 Lottie JSON、Pixabay、Openverse 的顺序网上找。Pixabay 不填密钥就会跳过。</p>
      {error ? <p className="error">{error}</p> : null}
      {form ? (
        <label>
          Pixabay 密钥 {form.pixabayKeyHint ? <em>当前 {form.pixabayKeyHint}</em> : <em>不填也能搜索</em>}
          <input
            value={pixabayKey}
            onChange={(event) => setPixabayKey(event.target.value)}
            placeholder={form.hasPixabayKey ? "留空则保持原密钥" : "到 pixabay.com/api/docs 申请"}
            type="password"
          />
        </label>
      ) : null}
      <div className="row">
        <button className="primary" onClick={() => void save()} disabled={!form}>
          保存
        </button>
        {saved ? <span className="muted">{saved}</span> : null}
      </div>
    </main>
  );
}
