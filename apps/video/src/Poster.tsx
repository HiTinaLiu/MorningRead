import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { DEFAULT_COVER_TITLE, lookById, type LookTheme } from "./looks";

const DISPLAY = '"Comic Sans MS", "Segoe Print", "Microsoft YaHei", "PingFang SC", sans-serif';

const STICKERS: Record<string, string[]> = {
  sun: ["☀️", "🍳", "⭐", "🐤"],
  meadow: ["🌱", "🌸", "🦋", "🍀"],
  bubble: ["🫧", "🐟", "⭐", "🐳"],
  candy: ["🍬", "🍭", "🍩", "🎀"],
  rainbow: ["🌈", "🎈", "⭐", "☁️"],
  zoo: ["🐯", "🐰", "🐥", "🐾"],
};

const BLOBS: Array<{ top?: number; left?: number; right?: number; bottom?: number; size: number; color: number }> = [
  { top: 80, left: 36, size: 170, color: 0 },
  { top: 160, right: 48, size: 110, color: 1 },
  { top: 520, left: -24, size: 86, color: 2 },
  { bottom: 280, right: 36, size: 150, color: 1 },
  { bottom: 160, left: 48, size: 100, color: 2 },
  { top: 980, right: -16, size: 72, color: 0 },
];

function spots(theme: LookTheme): string[] {
  return [theme.accent, theme.accent2, theme.accent3, theme.soft];
}

function pop(frame: number, fps: number, delay: number) {
  return spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 140, mass: 0.7 } });
}

export function Poster({
  coverTitle,
  themeTitle,
  lookId,
  animate = true,
}: {
  coverTitle: string;
  themeTitle: string;
  lookId: string;
  animate?: boolean;
}) {
  const theme = lookById(lookId);
  const colors = spots(theme);
  const title = coverTitle.trim() || DEFAULT_COVER_TITLE;
  const stickers = STICKERS[theme.id] ?? STICKERS.sun;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const motion = animate ? frame : 0;
  const settled = animate ? 0 : 1;
  const card = settled || pop(motion, fps, 4);
  const sun = settled || pop(motion, fps, 0);
  return (
    <AbsoluteFill style={{ background: theme.paper, fontFamily: DISPLAY, color: theme.ink, overflow: "hidden" }}>
      {BLOBS.map((blob, index) => {
        const drift = animate ? Math.sin((motion + index * 18) / 20) * 16 : 0;
        return (
          <div
            key={index}
            style={{
              position: "absolute",
              top: blob.top,
              left: blob.left,
              right: blob.right,
              bottom: blob.bottom,
              width: blob.size,
              height: blob.size,
              borderRadius: "50%",
              background: colors[blob.color % colors.length],
              transform: `translateY(${drift}px)`,
            }}
          />
        );
      })}
      <div
        style={{
          position: "absolute",
          top: 118,
          left: 150,
          width: 210,
          height: 210,
          transform: `scale(${0.72 + sun * 0.28}) rotate(${animate ? motion * 0.45 : 0}deg)`,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: "50%",
            background: theme.accent3,
            border: `12px solid ${theme.card}`,
            boxShadow: `0 0 0 16px ${theme.soft}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 36,
            left: 42,
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: theme.card,
            opacity: 0.85,
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: 210,
          left: 300,
          width: 150,
          height: 88,
          borderRadius: 80,
          background: theme.card,
          transform: `translateX(${(1 - sun) * -40}px)`,
          opacity: sun,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 430,
          bottom: 120,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 36,
          padding: "0 72px",
        }}
      >
        <div
          style={{
            alignSelf: "stretch",
            padding: "56px 44px 48px",
            borderRadius: 72,
            background: theme.card,
            border: `10px solid ${theme.accent}`,
            boxShadow: `16px 18px 0 ${theme.accent2}`,
            transform: `translateY(${(1 - card) * 56}px) scale(${0.9 + card * 0.1})`,
            opacity: card,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 26,
          }}
        >
          <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: 4, color: theme.accent2 }}>Morning Reading</div>
          <div style={{ fontSize: title.length > 12 ? 60 : 72, fontWeight: 800, lineHeight: 1.28, textAlign: "center" }}>{title}</div>
          <div style={{ width: 180, height: 12, borderRadius: 999, background: theme.soft }} />
          <div
            style={{
              marginTop: 6,
              padding: "16px 40px",
              borderRadius: 999,
              background: theme.accent,
              color: theme.card,
              fontSize: 54,
              fontWeight: 800,
              textAlign: "center",
            }}
          >
            {themeTitle}
          </div>
        </div>
        <div style={{ display: "flex", gap: 28, fontSize: 78, lineHeight: 1 }}>
          {stickers.map((sticker, index) => {
            const shown = settled || pop(motion, fps, 12 + index * 4);
            const bob = animate ? Math.sin((motion + index * 10) / 9) * 8 : 0;
            return (
              <span key={sticker} style={{ display: "inline-block", transform: `translateY(${bob}px) scale(${shown})`, opacity: shown }}>
                {sticker}
              </span>
            );
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {colors.map((color, index) => {
            const shown = settled || pop(motion, fps, 18 + index * 3);
            return (
              <div
                key={color + index}
                style={{
                  width: index === 2 ? 84 : 58,
                  height: index === 2 ? 84 : 58,
                  borderRadius: "50%",
                  background: color,
                  border: `6px solid ${theme.card}`,
                  transform: `scale(${shown})`,
                }}
              />
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
}
