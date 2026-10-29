import type { ReadingProps } from "@reading/types";

export type PieceSummary = {
  id: string;
  title: string;
  file: string;
  basedOn: string[];
  count: number;
  edited: boolean;
  hasVideo: boolean;
  seconds: number | null;
};

export type Catalog = {
  title: string;
  level: string;
  notes: string;
  pieces: PieceSummary[];
};

export type PictureInfo = {
  file: string;
  kind: "image" | "lottie";
  source: string;
  credit: string;
  keyword: string;
  url: string;
};

export type ImageHit = {
  url: string;
  thumb: string;
  source: string;
  pageUrl: string;
  title: string;
  credit: string;
};

export type VoiceRole = {
  id: string;
  lang: "zh" | "en";
  name: string;
  detail: string;
};

export type VoiceChoice = {
  zh: string;
  en: string;
};

export type VoiceCatalog = {
  zh: VoiceRole[];
  en: VoiceRole[];
  defaults: VoiceChoice;
};

export type Sentence = {
  index: number;
  en: string;
  zh: string;
  keyword: string;
  voice: string;
  picture: PictureInfo | null;
};

export type DraftBody = {
  introZh: string;
  coverTitle: string;
  subtitle: string;
  theme: string;
  voices: VoiceChoice;
  sentences: Array<Pick<Sentence, "en" | "zh" | "keyword" | "voice" | "picture">>;
};

export type VideoInfo = {
  file: string;
  subtitles: string;
  createdAt: string;
  seconds: number;
  pages: number;
  url: string;
  subtitlesUrl: string;
  path: string;
};

export type HandoutInfo = {
  file: string;
  createdAt: string;
  pages: number;
  sentences: number;
  url: string;
  path: string;
};

export type Piece = {
  id: string;
  title: string;
  file: string;
  basedOn: string[];
  introZh: string;
  coverTitle: string;
  subtitle: string;
  theme: string;
  level: string;
  series: string;
  edited: boolean;
  voices: VoiceChoice;
  sentences: Sentence[];
  video: VideoInfo | null;
  handout: HandoutInfo | null;
};

export type Settings = {
  hasPixabayKey: boolean;
  pixabayKeyHint: string;
};

export type { ReadingProps };
