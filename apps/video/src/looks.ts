export type LookTheme = {
  id: string;
  name: string;
  paper: string;
  ink: string;
  muted: string;
  faint: string;
  card: string;
  line: string;
  accent: string;
  accent2: string;
  accent3: string;
  soft: string;
};

export const DEFAULT_COVER_TITLE = "英语美文晨读 - 低年级";
export const DEFAULT_LOOK = "sun";

export const LOOKS: LookTheme[] = [
  {
    id: "sun",
    name: "太阳早餐",
    paper: "#fff6d8",
    ink: "#3b2a1a",
    muted: "#8a5a32",
    faint: "#c4a27a",
    card: "#fffdf6",
    line: "#ffe0a3",
    accent: "#f4a261",
    accent2: "#e76f51",
    accent3: "#2a9d8f",
    soft: "#ffe8a3",
  },
  {
    id: "meadow",
    name: "青草地",
    paper: "#e9fbe3",
    ink: "#1d3b24",
    muted: "#4d7a45",
    faint: "#9ec49a",
    card: "#fbfff8",
    line: "#c7efc0",
    accent: "#2f9e44",
    accent2: "#f4a261",
    accent3: "#74c0fc",
    soft: "#d3f9d8",
  },
  {
    id: "bubble",
    name: "泡泡海",
    paper: "#e7f6ff",
    ink: "#16324f",
    muted: "#3b6f99",
    faint: "#9ec4e6",
    card: "#f8fcff",
    line: "#c5e4ff",
    accent: "#1c7ed6",
    accent2: "#f06595",
    accent3: "#ffd43b",
    soft: "#d0ebff",
  },
  {
    id: "candy",
    name: "糖果屋",
    paper: "#fff0f6",
    ink: "#5c2142",
    muted: "#a5527a",
    faint: "#e7a8c4",
    card: "#fffafc",
    line: "#ffd0e4",
    accent: "#e64980",
    accent2: "#be4bdb",
    accent3: "#ff922b",
    soft: "#ffdeeb",
  },
  {
    id: "rainbow",
    name: "彩虹糖",
    paper: "#fff9db",
    ink: "#3d2c1e",
    muted: "#9a6b2f",
    faint: "#d4b07a",
    card: "#fffef8",
    line: "#ffe8a3",
    accent: "#f76707",
    accent2: "#ae3ec9",
    accent3: "#12b886",
    soft: "#fff3bf",
  },
  {
    id: "zoo",
    name: "动物园",
    paper: "#fff4e6",
    ink: "#3d2914",
    muted: "#8a5a2b",
    faint: "#d4b48a",
    card: "#fffaf3",
    line: "#ffe0c2",
    accent: "#e67700",
    accent2: "#2b8a3e",
    accent3: "#1c7ed6",
    soft: "#ffe8cc",
  },
];

export function lookById(id: string): LookTheme {
  return LOOKS.find((theme) => theme.id === id) ?? LOOKS[0];
}
