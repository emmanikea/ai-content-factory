import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const layerStyle = {
  width: '100%',
  height: '100%',
  objectFit: 'cover',
};

const Caption = ({ caption }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - Math.round(caption.start * fps);
  const fade = interpolate(localFrame, [0, 4, Math.max(5, (caption.end - caption.start) * fps - 4)], [0, 1, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        right: 72,
        bottom: caption.bottom ?? 270,
        display: 'flex',
        justifyContent: 'center',
        opacity: fade,
        zIndex: 40,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth: 900,
          padding: '14px 22px',
          borderRadius: 24,
          background: 'rgba(0,0,0,0.74)',
          color: '#fff',
          fontFamily: 'Inter, Arial, sans-serif',
          fontSize: caption.fontSize ?? 56,
          fontWeight: 800,
          lineHeight: 1.08,
          textAlign: 'center',
          letterSpacing: '-0.025em',
        }}
      >
        {caption.text}
      </div>
    </div>
  );
};

const Cta = ({ cta }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startFrame = Math.round(cta.start * fps);
  const enter = interpolate(frame, [startFrame, startFrame + 8], [40, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = interpolate(frame, [startFrame, startFrame + 6], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        right: 72,
        bottom: 120,
        display: 'flex',
        justifyContent: 'center',
        transform: `translateY(${enter}px)`,
        opacity,
        zIndex: 50,
      }}
    >
      <div
        style={{
          padding: '24px 34px',
          borderRadius: 999,
          background: cta.background ?? '#f4ff75',
          color: cta.color ?? '#101013',
          fontFamily: 'Inter, Arial, sans-serif',
          fontSize: 42,
          fontWeight: 850,
          textAlign: 'center',
          boxShadow: '0 18px 60px rgba(0,0,0,.32)',
        }}
      >
        {cta.text}
      </div>
    </div>
  );
};

export const UGCReel = ({ clips = [], captions = [], cta = null, background = '#0b0b0d' }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background }}>
      {clips.map((clip) => {
        const from = Math.round(clip.start * fps);
        const durationInFrames = Math.max(1, Math.round((clip.end - clip.start) * fps));
        const trimBefore = Math.round((clip.trimStartSeconds ?? 0) * fps);
        return (
          <Sequence key={clip.id} from={from} durationInFrames={durationInFrames} premountFor={fps}>
            <AbsoluteFill>
              {clip.type === 'image' ? (
                <Img src={clip.src} style={{ ...layerStyle, objectFit: clip.fit ?? 'cover' }} />
              ) : (
                <OffthreadVideo
                  src={clip.src}
                  trimBefore={trimBefore}
                  muted={clip.muted ?? false}
                  volume={clip.volume ?? 1}
                  style={{ ...layerStyle, objectFit: clip.fit ?? 'cover' }}
                />
              )}
              {clip.overlay ? (
                <AbsoluteFill style={{ background: clip.overlay, pointerEvents: 'none' }} />
              ) : null}
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {captions.map((caption) => {
        const from = Math.round(caption.start * fps);
        const durationInFrames = Math.max(1, Math.round((caption.end - caption.start) * fps));
        return (
          <Sequence key={caption.id ?? `${caption.start}-${caption.text}`} from={from} durationInFrames={durationInFrames}>
            <Caption caption={caption} />
          </Sequence>
        );
      })}

      {cta ? <Cta cta={cta} /> : null}
    </AbsoluteFill>
  );
};
