export type MediaRef = { url: string; kind: "image" | "lottie" } | null;

export type WordMark = { text: string; startMs: number; endMs: number };

export type ReadingLine = {
  id: string;
  lang: "zh" | "en";
  text: string;
  subtitle: string;
  audioUrl: string;
  audioMs: number;
  speechMs: number;
  pauseMs: number;
  words: WordMark[];
};

export type ReadingPage = {
  id: string;
  kind: "intro" | "sentence";
  index: number;
  title: string;
  keyword: string;
  image: MediaRef;
  credit: string;
  line: ReadingLine;
};

export type ReadingProps = {
  title: string;
  series: string;
  level: string;
  coverTitle: string;
  subtitle: string;
  theme: string;
  pages: ReadingPage[];
};
