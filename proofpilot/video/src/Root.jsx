import React from 'react';
import { Composition, AbsoluteFill, Sequence } from 'remotion';
import timings from './timings.json';
import { S01_Hook, S02_Gap, S03_Intro, S04_Contract } from './scenes/Part1';
import { S05_Ambiguity, S06_Model, S07_Sandbox } from './scenes/Part2';
import { S08_ServerWrite, S09_Readback, S10_Results } from './scenes/Part3';

const SCENES = [S01_Hook, S02_Gap, S03_Intro, S04_Contract, S05_Ambiguity, S06_Model, S07_Sandbox, S08_ServerWrite, S09_Readback, S10_Results];

export const ProofPilotFilm = () => (
  <AbsoluteFill style={{ backgroundColor: '#080B14' }}>
    {timings.scenes.map((scene, i) => {
      const Scene = SCENES[i];
      return (
        <Sequence key={scene.id} from={scene.from} durationInFrames={scene.dur} name={scene.id}>
          <Scene dur={scene.dur} audio={scene.audio} />
        </Sequence>
      );
    })}
  </AbsoluteFill>
);

export const Root = () => (
  <Composition
    id="ProofPilot"
    component={ProofPilotFilm}
    durationInFrames={timings.total}
    fps={timings.fps}
    width={timings.width}
    height={timings.height}
  />
);
