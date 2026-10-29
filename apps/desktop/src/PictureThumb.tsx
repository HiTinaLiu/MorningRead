import lottie, { type AnimationItem } from "lottie-web";
import { useEffect, useState } from "react";
import type { PictureInfo } from "./types";

const SOURCE: Record<string, string> = {
  twemoji: "Twemoji",
  lottiefiles: "Lottie",
  pixabay: "Pixabay",
  openverse: "Openverse",
};

export function sourceLabel(source: string): string {
  return SOURCE[source] || source || "配图";
}

export function PictureThumb({ picture }: { picture: PictureInfo | null }) {
  if (!picture) return <span className="thumb-empty">无图</span>;
  if (picture.kind === "lottie") return <LottieThumb url={picture.url} />;
  return <img src={picture.url} alt="" />;
}

function LottieThumb({ url }: { url: string }) {
  const [node, setNode] = useState<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!node) return;
    let anim: AnimationItem | null = null;
    let gone = false;
    fetch(url)
      .then((response) => response.json())
      .then((data: unknown) => {
        if (gone) return;
        anim = lottie.loadAnimation({
          container: node,
          renderer: "svg",
          loop: true,
          autoplay: true,
          animationData: data,
        });
      })
      .catch(() => {
        if (!gone) setFailed(true);
      });
    return () => {
      gone = true;
      anim?.destroy();
    };
  }, [node, url]);

  if (failed) return <span className="thumb-empty">动图</span>;
  return <div ref={setNode} className="thumb-motion" />;
}
