import React from 'react';
import { registerRoot, Composition } from 'remotion';
import { UGCReel } from './reel.jsx';

const defaultProps = {
  fps: 30,
  durationSeconds: 18,
  background: '#0b0b0d',
  clips: [],
  captions: [],
  cta: null,
};

const Root = () => (
  <Composition
    id="UGCReel"
    component={UGCReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={18 * 30}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.max(1, Math.ceil((props.durationSeconds ?? 18) * 30)),
      props,
    })}
  />
);

registerRoot(Root);
