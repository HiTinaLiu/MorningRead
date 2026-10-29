import { Lottie, type LottieAnimationData } from "@remotion/lottie";
import { useEffect, useState, type CSSProperties } from "react";
import { continueRender, delayRender, Img } from "remotion";
import { COLORS, FONT } from "../theme";
import type { MediaRef } from "../types";

function LottiePicture({ url, size, label }: { url: string; size: number; label: string }) {
  const [handle] = useState(() => delayRender(`加载动图 ${url}`));
  const [data, setData] = useState<LottieAnimationData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(url)
      .then((response) => response.json())
      .then((json: LottieAnimationData) => setData(json))
      .catch(() => setFailed(true))
      .finally(() => continueRender(handle));
  }, [handle, url]);

  if (failed) return <Letter label={label} size={size} />;
  if (!data) return null;
  return <Lottie animationData={data} loop style={{ width: size, height: size }} />;
}

function Letter({ label, size }: { label: string; size: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.22,
        background: COLORS.tealSoft,
        color: COLORS.teal,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: FONT,
        fontWeight: 800,
        fontSize: size * 0.42,
      }}
    >
      {(label.trim().slice(0, 1) || "?").toUpperCase()}
    </div>
  );
}

export function Picture({
  media,
  label,
  size,
  style,
}: {
  media: MediaRef;
  label: string;
  size: number;
  style?: CSSProperties;
}) {
  return (
    <div style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center", ...style }}>
      {!media ? <Letter label={label} size={size} /> : null}
      {media?.kind === "lottie" ? <LottiePicture url={media.url} size={size} label={label} /> : null}
      {media?.kind === "image" ? <Img src={media.url} style={{ width: size, height: size, objectFit: "contain" }} /> : null}
    </div>
  );
}
