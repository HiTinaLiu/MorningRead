import { Poster } from "./Poster";
import { DEFAULT_COVER_TITLE, DEFAULT_LOOK } from "./looks";
import type { ReadingProps } from "./types";

export function Cover(props: ReadingProps) {
  return (
    <Poster
      coverTitle={props.coverTitle || DEFAULT_COVER_TITLE}
      themeTitle={props.subtitle || props.title}
      lookId={props.theme || DEFAULT_LOOK}
      animate={false}
    />
  );
}
