import React from 'react';

interface CenteredVideoPlayerProps {
  src: string;
  title?: string;
}

// Centered player capped at 800px with a responsive 16:9 frame (used on review and report screens).
export const CenteredVideoPlayer: React.FC<CenteredVideoPlayerProps> = ({ src, title }) => (
  <div className="mx-auto w-full max-w-[800px]">
    <div className="aspect-video w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-inner">
      <video controls playsInline preload="metadata" className="h-full w-full object-contain" src={src} title={title} />
    </div>
  </div>
);
