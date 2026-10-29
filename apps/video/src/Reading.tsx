import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from "remotion";
import { Picture } from "./components/Picture";
import { DEFAULT_COVER_TITLE, DEFAULT_LOOK, lookById } from "./looks";
import { Poster } from "./Poster";
import { FONT, FPS } from "./theme";
import { buildTimeline, toFrames, type TimedPage } from "./timeline";
import type { ReadingProps } from "./types";

function spokenCount(page: TimedPage, local: number): number {
  const ms = (local * 1000) / FPS;
  const words = page.page.line.words;
  if (words.length) return words.filter((word) => word.startMs <= ms).length;
  return Math.ceil(page.page.line.text.split(/\s+/).filter(Boolean).length * Math.min(1, local / Math.max(1, page.speech)));
}

function EnglishLine({ page, local, theme }: { page: TimedPage; local: number; theme: ReturnType<typeof lookById> }) {
  const tokens = page.page.line.text.split(/\s+/).filter(Boolean);
  const started = spokenCount(page, local);
  const size = tokens.length > 8 ? 58 : 72;
  return (
    <div style={{ fontSize: size, fontWeight: 800, lineHeight: 1.35, textAlign: "center" }}>
      {tokens.map((token, index) => (
        <span key={`${token}-${index}`} style={{ color: index < started ? theme.accent : theme.faint }}>
          {token}
          {index < tokens.length - 1 ? " " : ""}
        </span>
      ))}
    </div>
  );
}

function ChineseLine({
  text,
  local,
  speech,
  theme,
}: {
  text: string;
  local: number;
  speech: number;
  theme: ReturnType<typeof lookById>;
}) {
  const covered = Math.ceil(Array.from(text).length * Math.min(1, local / Math.max(1, speech)));
  return (
    <div style={{ fontSize: text.length > 28 ? 40 : 48, fontWeight: 700, lineHeight: 1.45, textAlign: "center" }}>
      {Array.from(text).map((char, index) => (
        <span key={index} style={{ color: index < covered ? theme.ink : theme.faint }}>
          {char}
        </span>
      ))}
    </div>
  );
}

function PageView({
  page,
  local,
  lookId,
  coverTitle,
  subtitle,
}: {
  page: TimedPage;
  local: number;
  lookId: string;
  coverTitle: string;
  subtitle: string;
}) {
  const item = page.page;
  const theme = lookById(lookId);
  if (item.kind === "intro") {
    return <Poster coverTitle={coverTitle} themeTitle={subtitle || item.title} lookId={lookId} />;
  }
  const reading = local < page.speech;
  const cue = reading ? "跟我读" : "你来读";
  const cueColor = reading ? theme.accent : theme.accent2;
  return (
    <AbsoluteFill style={{ fontFamily: FONT, color: theme.ink }}>
      <div style={{ position: "absolute", left: 56, right: 56, top: 72, display: "flex", alignItems: "center", gap: 20 }}>
        <div
          style={{
            minWidth: 88,
            height: 72,
            padding: "0 18px",
            borderRadius: 999,
            background: theme.accent,
            color: theme.card,
            fontSize: 32,
            fontWeight: 800,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {item.index}
        </div>
        <div style={{ fontSize: subtitle.length > 22 ? 32 : 40, fontWeight: 800, lineHeight: 1.2 }}>{subtitle}</div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: 220,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 36,
        }}
      >
        <div
          style={{
            padding: 28,
            borderRadius: 56,
            background: theme.card,
            border: `8px solid ${theme.line}`,
          }}
        >
          <Picture media={item.image} label={item.keyword} size={520} />
        </div>
        <div
          style={{
            alignSelf: "stretch",
            padding: "42px 36px",
            borderRadius: 40,
            background: theme.card,
            border: `8px solid ${cueColor}`,
            boxShadow: `10px 12px 0 ${theme.soft}`,
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          {item.line.lang === "en" ? (
            <EnglishLine page={page} local={local} theme={theme} />
          ) : (
            <ChineseLine text={item.line.text} local={local} speech={page.speech} theme={theme} />
          )}
          {item.line.subtitle ? (
            <div style={{ fontSize: 40, color: theme.muted, textAlign: "center", lineHeight: 1.4 }}>{item.line.subtitle}</div>
          ) : null}
        </div>
        <div
          style={{
            padding: "12px 28px",
            borderRadius: 999,
            background: cueColor,
            color: theme.card,
            fontSize: 32,
            fontWeight: 800,
          }}
        >
          {cue}
        </div>
        {item.credit ? <div style={{ fontSize: 22, color: theme.faint }}>{item.credit}</div> : null}
      </div>
    </AbsoluteFill>
  );
}

export function Reading(props: ReadingProps) {
  const frame = useCurrentFrame();
  const timeline = buildTimeline(props);
  const lookId = props.theme || DEFAULT_LOOK;
  const coverTitle = props.coverTitle || DEFAULT_COVER_TITLE;
  const subtitle = props.subtitle || props.title;
  const theme = lookById(lookId);
  const current = [...timeline.pages].reverse().find((page) => frame >= page.from) ?? timeline.pages[0];
  const progress = frame / timeline.total;
  const onCover = current?.page.kind === "intro";
  return (
    <AbsoluteFill style={{ background: theme.paper }}>
      {timeline.pages.map((page) => (
        <Sequence key={page.page.id} from={page.from} durationInFrames={page.duration} name={page.page.kind === "intro" ? "主图" : page.page.line.text.slice(0, 24)}>
          <PageView page={page} local={frame - page.from} lookId={lookId} coverTitle={coverTitle} subtitle={subtitle} />
        </Sequence>
      ))}
      {onCover ? null : (
      <div style={{ position: "absolute", left: 56, right: 56, bottom: 48 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: FONT, fontSize: 26, color: theme.muted, marginBottom: 12 }}>
          <span>{coverTitle}</span>
          <span>{current ? `第 ${current.page.index} 句` : props.level}</span>
        </div>
        <div style={{ height: 14, borderRadius: 999, background: theme.line, overflow: "hidden" }}>
          <div style={{ width: `${progress * 100}%`, height: "100%", background: theme.accent }} />
        </div>
      </div>
      )}
      {timeline.pages
        .filter((page) => page.page.line.audioUrl)
        .map((page) => (
          <Sequence key={`${page.page.id}-audio`} from={page.from} durationInFrames={Math.max(1, toFrames(page.page.line.audioMs))} layout="none">
            <Audio src={page.page.line.audioUrl} />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
}
