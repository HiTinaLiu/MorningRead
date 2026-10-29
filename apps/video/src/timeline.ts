import { FPS, LINE_GAP, MIN_LINE, PAGE_PAD } from "./theme";
import type { ReadingLine, ReadingPage, ReadingProps } from "./types";

export function toFrames(ms: number): number {
  return Math.round((ms * FPS) / 1000);
}

export type TimedPage = {
  page: ReadingPage;
  from: number;
  speech: number;
  duration: number;
};

export type Timeline = {
  pages: TimedPage[];
  total: number;
};

export function timeLine(line: ReadingLine): { speech: number; duration: number } {
  const speech = Math.max(MIN_LINE, toFrames(line.speechMs));
  return { speech, duration: speech + toFrames(line.pauseMs) + LINE_GAP + PAGE_PAD };
}

export function buildTimeline(props: ReadingProps): Timeline {
  let cursor = 0;
  const pages = props.pages.map((page) => {
    const timed = timeLine(page.line);
    const row = { page, from: cursor, speech: timed.speech, duration: timed.duration };
    cursor += timed.duration;
    return row;
  });
  return { pages, total: Math.max(1, cursor) };
}
