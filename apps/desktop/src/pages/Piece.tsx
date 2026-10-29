import { useEffect, useMemo, useRef, useState } from "react";
import { Player } from "@remotion/player";
import { Reading } from "@reading/Reading";
import { DEFAULT_COVER_TITLE, LOOKS } from "@reading/looks";
import { FPS, HEIGHT, WIDTH } from "@reading/theme";
import { buildTimeline } from "@reading/timeline";
import type { ReadingProps } from "@reading/types";
import { api } from "../api";
import { PictureThumb, sourceLabel } from "../PictureThumb";
import { applyProgress, ProgressList, type ProgressStep } from "../ProgressList";
import type { DraftBody, HandoutInfo, ImageHit, Piece, Sentence, VideoInfo, VoiceCatalog, VoiceChoice } from "../types";

type Row = Sentence & { key: string };

function clock(seconds: number): string {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function rowsFrom(sentences: Sentence[]): Row[] {
  return sentences.map((sentence) => ({ ...sentence, key: crypto.randomUUID() }));
}

const FALLBACK_VOICES: VoiceChoice = { zh: "xiaoxiao", en: "jenny" };

function draftBody(introZh: string, coverTitle: string, subtitle: string, theme: string, voices: VoiceChoice, rows: Row[]): DraftBody {
  return {
    introZh,
    coverTitle,
    subtitle,
    theme,
    voices,
    sentences: rows.map(({ en, zh, keyword, voice, picture }) => ({ en, zh, keyword, voice, picture })),
  };
}

export function PiecePage({ id }: { id: string }) {
  const [piece, setPiece] = useState<Piece | null>(null);
  const [introZh, setIntroZh] = useState("");
  const [coverTitle, setCoverTitle] = useState(DEFAULT_COVER_TITLE);
  const [subtitle, setSubtitle] = useState("");
  const [theme, setTheme] = useState(LOOKS[0].id);
  const [voices, setVoices] = useState<VoiceChoice>(FALLBACK_VOICES);
  const [roles, setRoles] = useState<VoiceCatalog | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [listening, setListening] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [preview, setPreview] = useState<ReadingProps | null>(null);
  const [video, setVideo] = useState<VideoInfo | null>(null);
  const [handout, setHandout] = useState<HandoutInfo | null>(null);
  const [pickerKey, setPickerKey] = useState("");
  const [pickerQuery, setPickerQuery] = useState("");
  const [hits, setHits] = useState<ImageHit[]>([]);
  const [pickerError, setPickerError] = useState("");
  const [pickerBusy, setPickerBusy] = useState(false);
  const pending = useRef(new Set<string>());
  const dirty = useRef(false);
  const keywordTimer = useRef<number | null>(null);

  function requestPicture(key: string, keyword: string, force = false) {
    const text = keyword.trim();
    if (!text) return;
    const mark = `${key}|${text}`;
    if (!force && pending.current.has(mark)) return;
    pending.current.add(mark);
    void api
      .resolvePicture(text)
      .then((picture) => {
        setRows((current) =>
          current.map((row) => (row.key === key && row.keyword === text && !row.picture ? { ...row, picture } : row)),
        );
      })
      .catch(() => undefined);
  }

  function applyPiece(record: Piece) {
    const next = rowsFrom(record.sentences);
    dirty.current = false;
    pending.current.clear();
    setPiece(record);
    setIntroZh(record.introZh);
    setCoverTitle(record.coverTitle || DEFAULT_COVER_TITLE);
    setSubtitle(record.subtitle || record.title);
    setTheme(record.theme || LOOKS[0].id);
    setVoices(record.voices || FALLBACK_VOICES);
    setRows(next);
    setVideo(record.video);
    setHandout(record.handout);
    next.forEach((row) => {
      if (!row.picture && row.keyword) requestPicture(row.key, row.keyword);
    });
  }

  useEffect(() => {
    api
      .voices()
      .then(setRoles)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    setPiece(null);
    setPreview(null);
    setError("");
    setPickerKey("");
    api
      .piece(id)
      .then((record) => applyPiece(record))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "没有打开这篇晨读"));
    // Load once per piece. applyPiece closes over the latest setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!piece || !dirty.current) return;
    const handle = window.setTimeout(() => {
      dirty.current = false;
      void api.saveDraft(id, draftBody(introZh, coverTitle, subtitle, theme, voices, rows)).catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "草稿没有保存");
      });
    }, 700);
    return () => window.clearTimeout(handle);
  }, [id, introZh, coverTitle, subtitle, theme, piece, rows, voices]);

  const timeline = useMemo(() => (preview ? buildTimeline(preview) : null), [preview]);

  function patch(key: string, change: Partial<Row>) {
    dirty.current = true;
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...change } : row)));
  }

  function changeKeyword(key: string, keyword: string) {
    dirty.current = true;
    setRows((current) => current.map((row) => (row.key === key ? { ...row, keyword, picture: null } : row)));
    if (keywordTimer.current) window.clearTimeout(keywordTimer.current);
    keywordTimer.current = window.setTimeout(() => requestPicture(key, keyword, true), 500);
  }

  async function matchKeyword(row: Row) {
    setError("");
    try {
      const found = await api.keyword(row.en, row.zh);
      changeKeyword(row.key, found.keyword);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "没有选出配图词");
    }
  }

  function removeRow(key: string) {
    dirty.current = true;
    setRows((current) => (current.length <= 1 ? current : current.filter((row) => row.key !== key)));
    if (pickerKey === key) setPickerKey("");
  }

  function addRow() {
    dirty.current = true;
    setRows((current) => [
      ...current,
      { key: crypto.randomUUID(), index: current.length, en: "", zh: "", keyword: "", voice: "", picture: null },
    ]);
  }

  async function search(query: string) {
    setPickerQuery(query);
    setPickerBusy(true);
    setPickerError("");
    try {
      const found = await api.searchImages(query);
      setHits(found.hits);
      if (found.hits.length === 0) setPickerError("没有搜到配图");
    } catch (reason) {
      setHits([]);
      setPickerError(reason instanceof Error ? reason.message : "搜索失败");
    } finally {
      setPickerBusy(false);
    }
  }

  function openPicker(row: Row) {
    setPickerKey(row.key);
    setHits([]);
    void search(row.keyword || row.en);
  }

  async function chooseHit(row: Row, hit: ImageHit) {
    setPickerBusy(true);
    setPickerError("");
    try {
      const picture = await api.importPicture(hit, row.keyword || hit.title);
      patch(row.key, { picture, keyword: row.keyword || picture.keyword });
      setPickerKey("");
    } catch (reason) {
      setPickerError(reason instanceof Error ? reason.message : "这张图没有保存下来");
    } finally {
      setPickerBusy(false);
    }
  }

  async function reset() {
    setBusy("正在恢复原文…");
    setError("");
    try {
      applyPiece(await api.resetDraft(id));
      setPreview(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "没有恢复原文");
    } finally {
      setBusy("");
    }
  }

  function editCover(value: string) {
    dirty.current = true;
    setCoverTitle(value);
    setPreview(null);
  }

  function editSubtitle(value: string) {
    dirty.current = true;
    setSubtitle(value);
    setPreview(null);
  }

  function chooseLook(id: string) {
    dirty.current = true;
    setTheme(id);
    setPreview(null);
  }

  function chooseVoice(lang: "zh" | "en", role: string) {
    dirty.current = true;
    setVoices((current) => ({ ...current, [lang]: role }));
    setPreview(null);
  }

  async function listen(mark: string, role: string, lang: "zh" | "en", text = "") {
    setListening(mark);
    setError("");
    try {
      const clip = await api.sample(role, lang, text);
      await new Audio(clip.url).play();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "试听失败");
    } finally {
      setListening("");
    }
  }

  async function makeHandout() {
    const body = draftBody(introZh, coverTitle, subtitle, theme, voices, rows);
    setBusy("正在生成讲义…");
    setError("");
    setSteps([]);
    try {
      await api.saveDraft(id, body);
      setHandout(await api.handout(id, body, (event) => setSteps((current) => applyProgress(current, event))));
      setPiece((current) => (current ? { ...current, edited: true } : current));
      setSteps([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "讲义没有生成");
    } finally {
      setBusy("");
    }
  }

  async function run(kind: "preview" | "render") {
    const body = draftBody(introZh, coverTitle, subtitle, theme, voices, rows);
    setBusy(kind === "preview" ? "正在准备预览…" : "正在生成视频…");
    setError("");
    setSteps([]);
    try {
      await api.saveDraft(id, body);
      if (kind === "preview") {
        setPreview(await api.preview(id, body, (event) => setSteps((current) => applyProgress(current, event))));
      } else {
        const next = await api.render(id, body, (event) => setSteps((current) => applyProgress(current, event)));
        setVideo(next);
        setPiece((current) => (current ? { ...current, video: next, edited: true } : current));
      }
      setSteps([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "生成失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="page">
      <div className="hero">
        <div>
          <p className="eyebrow">{piece?.series || "英语晨读"}</p>
          <h1>{piece?.title || "晨读"}</h1>
          <label>
            主图标题
            <input value={coverTitle} onChange={(event) => editCover(event.target.value)} />
          </label>
          <label>
            二级标题
            <input value={subtitle} placeholder={piece?.title || "当前主题"} onChange={(event) => editSubtitle(event.target.value)} />
          </label>
          <div className="look-row">
            {LOOKS.map((look) => (
              <button
                key={look.id}
                type="button"
                className={theme === look.id ? "look-chip on" : "look-chip"}
                style={{ background: look.soft, borderColor: look.accent, color: look.ink }}
                onClick={() => chooseLook(look.id)}
              >
                <span style={{ background: look.accent }} />
                {look.name}
              </button>
            ))}
          </div>
          <label>
            开场白，只朗读，不出现在画面上
            <textarea
              value={introZh}
              rows={3}
              onChange={(event) => {
                dirty.current = true;
                setIntroZh(event.target.value);
              }}
            />
          </label>
          <div className="voice-bar">
            <label>
              中文开场
              <select value={voices.zh} onChange={(event) => chooseVoice("zh", event.target.value)}>
                {(roles?.zh ?? []).map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name} · {role.detail}
                  </option>
                ))}
              </select>
              <button disabled={listening === "zh" || !piece} onClick={() => void listen("zh", voices.zh, "zh", introZh)}>
                试听
              </button>
            </label>
            <label>
              英文朗读
              <select value={voices.en} onChange={(event) => chooseVoice("en", event.target.value)}>
                {(roles?.en ?? []).map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name} · {role.detail}
                  </option>
                ))}
              </select>
              <button disabled={listening === "en" || !piece} onClick={() => void listen("en", voices.en, "en")}>
                试听
              </button>
            </label>
          </div>
        </div>
        <div className="actions">
          <button disabled={Boolean(busy) || !piece} onClick={() => void reset()}>
            恢复原文
          </button>
          <button disabled={Boolean(busy) || !piece} onClick={() => void run("preview")}>
            {preview ? "刷新预览" : "预览"}
          </button>
          <button className="primary" disabled={Boolean(busy) || !piece} onClick={() => void run("render")}>
            生成视频
          </button>
          <button disabled={Boolean(busy) || !piece} onClick={() => void makeHandout()}>
            {handout ? "重新生成讲义" : "生成A4讲义"}
          </button>
        </div>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {busy ? <p className="muted">{busy}</p> : null}
      <ProgressList steps={steps} />
      <div className="split">
        <section className="sentence-list">
          {rows.map((row, index) => (
            <article key={row.key} className="sentence-edit">
              <span className="sentence-no">{index + 1}</span>
              <div className="sentence-fields">
                <textarea
                  value={row.en}
                  rows={2}
                  placeholder="英文，会朗读"
                  onChange={(event) => patch(row.key, { en: event.target.value })}
                />
                <textarea
                  value={row.zh}
                  rows={2}
                  placeholder="中文，只显示"
                  onChange={(event) => patch(row.key, { zh: event.target.value })}
                />
                <div className="keyword-row">
                  <input
                    value={row.keyword}
                    placeholder="配图词"
                    onChange={(event) => changeKeyword(row.key, event.target.value)}
                  />
                  <select
                    value={row.voice}
                    onChange={(event) => {
                      patch(row.key, { voice: event.target.value });
                      setPreview(null);
                    }}
                  >
                    <option value="">跟随本篇英文角色</option>
                    {(roles?.en ?? []).map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.name} · {role.detail}
                      </option>
                    ))}
                  </select>
                  <button
                    disabled={listening === row.key || !row.en.trim()}
                    onClick={() => void listen(row.key, row.voice || voices.en, "en", row.en)}
                  >
                    试听这句
                  </button>
                  <button disabled={Boolean(busy) || !row.en.trim()} onClick={() => void matchKeyword(row)}>
                    按句子
                  </button>
                  <button className="danger" disabled={rows.length <= 1 || Boolean(busy)} onClick={() => removeRow(row.key)}>
                    删除
                  </button>
                </div>
                {pickerKey === row.key ? (
                  <div className="picker">
                    <div className="keyword-row">
                      <input value={pickerQuery} onChange={(event) => setPickerQuery(event.target.value)} />
                      <button disabled={pickerBusy} onClick={() => void search(pickerQuery)}>
                        搜索
                      </button>
                      <button onClick={() => setPickerKey("")}>收起</button>
                    </div>
                    {pickerError ? <p className="error">{pickerError}</p> : null}
                    <div className="hit-grid">
                      {hits.map((hit) => (
                        <button key={hit.url} className="hit" disabled={pickerBusy} onClick={() => void chooseHit(row, hit)}>
                          <img src={hit.thumb || hit.url} alt="" />
                          <em>{sourceLabel(hit.source)}</em>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="sentence-picture">
                <div className="thumb">
                  <PictureThumb picture={row.picture} />
                </div>
                <em>{row.picture ? sourceLabel(row.picture.source) : "正在配图"}</em>
                <button disabled={Boolean(busy)} onClick={() => openPicker(row)}>
                  换图
                </button>
                <button
                  disabled={Boolean(busy) || !row.keyword.trim()}
                  onClick={() => {
                    dirty.current = true;
                    patch(row.key, { picture: null });
                    requestPicture(row.key, row.keyword, true);
                  }}
                >
                  自动
                </button>
              </div>
            </article>
          ))}
          <button disabled={Boolean(busy)} onClick={addRow}>
            加一句
          </button>
        </section>
        <aside className="stage">
          {preview && timeline ? (
            <>
              <Player
                component={Reading}
                inputProps={preview}
                durationInFrames={timeline.total}
                fps={FPS}
                compositionWidth={WIDTH}
                compositionHeight={HEIGHT}
                controls
                style={{ width: 360, height: 640 }}
              />
              <p className="muted">预览 {clock(timeline.total / FPS)}。生成视频会做成 1080×1920。</p>
            </>
          ) : (
            <p className="muted">左边改句子、配图和配音角色。试听一句，或预览整篇。生成视频用同一份草稿。</p>
          )}
          {video ? (
            <div className="video-ready">
              <video src={video.url} controls />
              <p className="muted">
                已生成 {clock(video.seconds)} · {video.pages} 页
              </p>
              {window.desktop ? (
                <button
                  onClick={() => {
                    void window.desktop?.showInFolder(video.path);
                  }}
                >
                  在文件夹中显示
                </button>
              ) : null}
            </div>
          ) : null}
          {handout ? (
            <div className="video-ready">
              <p className="muted">
                A4 讲义 · {handout.pages} 页 · {handout.sentences} 句
              </p>
              <a className="file-link" href={handout.url} target="_blank" rel="noreferrer">
                打开讲义 PDF
              </a>
              {window.desktop ? (
                <button onClick={() => void window.desktop?.showInFolder(handout.path)}>在文件夹中显示</button>
              ) : null}
            </div>
          ) : null}
        </aside>
      </div>
    </main>
  );
}
