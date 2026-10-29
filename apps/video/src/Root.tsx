import { Composition, Still } from "remotion";
import { Cover } from "./Cover";
import { Reading } from "./Reading";
import { SAMPLE } from "./sample";
import { FPS, HEIGHT, WIDTH } from "./theme";
import { buildTimeline } from "./timeline";

export function Root() {
  return (
    <>
      <Composition
        id="Reading"
        component={Reading}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        durationInFrames={buildTimeline(SAMPLE).total}
        defaultProps={SAMPLE}
        calculateMetadata={({ props }) => ({ durationInFrames: buildTimeline(props).total })}
      />
      <Still id="Cover" component={Cover} width={WIDTH} height={HEIGHT} defaultProps={SAMPLE} />
    </>
  );
}
