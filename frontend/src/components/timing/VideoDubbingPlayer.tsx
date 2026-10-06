import React, { useState, useRef } from 'react';
import { VideoMetadata, AudioTrackOption, TranslationSegment } from '../../types';
import { Film, Volume2, Subtitles, Play, Pause, RotateCcw } from 'lucide-react';

interface VideoDubbingPlayerProps {
  video: VideoMetadata;
  activeSegment?: TranslationSegment | null;
  audioTrack: AudioTrackOption;
  onChangeAudioTrack: (track: AudioTrackOption) => void;
  showSubtitles: boolean;
  onToggleSubtitles: () => void;
}

export const VideoDubbingPlayer: React.FC<VideoDubbingPlayerProps> = ({
  video,
  activeSegment,
  audioTrack,
  onChangeAudioTrack,
  showSubtitles,
  onToggleSubtitles,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const restartVideo = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play();
    setIsPlaying(true);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6 space-y-4 transition-all">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-brand-700" />
          <h3 className="text-base font-bold text-slate-900">
            معاينة الدبلجة والمطابقة
          </h3>
        </div>

        <span className="text-[11px] font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-100 max-w-[150px] truncate" title={video.name}>
          {video.name}
        </span>
      </div>

      {/* Video Box with subtitle overlay */}
      <div className="mx-auto w-full max-w-[800px] rounded-xl overflow-hidden bg-slate-950 aspect-video relative shadow-inner border border-slate-800 flex flex-col justify-end group">
        <video
          ref={videoRef}
          src={video.previewUrl}
          controls={false}
          className="w-full h-full object-contain"
          playsInline
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />

        {/* Subtitle Overlay when enabled */}
        {showSubtitles && activeSegment && (
          <div className="absolute bottom-12 inset-x-4 flex justify-center pointer-events-none z-10 animate-in fade-in duration-150">
            <div className="bg-black/85 backdrop-blur-sm text-white px-4 py-2 rounded-xl text-center shadow-lg border border-white/10 max-w-xl">
              <p dir="ltr" className="text-xs sm:text-sm font-sans font-medium text-amber-200 text-left">
                {activeSegment.englishTranslation}
              </p>
              <p className="text-[11px] text-slate-300 font-arabic text-right mt-1 opacity-80">
                {activeSegment.arabicText}
              </p>
            </div>
          </div>
        )}

        {/* Custom Mini Control Bar over video */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-3 flex items-center justify-between text-white z-20">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={togglePlay}
              className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white transition-colors"
              title={isPlaying ? 'إيقاف مؤقت' : 'تشغيل'}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
            </button>

            <button
              type="button"
              onClick={restartVideo}
              className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="إعادة من البداية"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            <span className="text-xs font-mono opacity-80">00:48 / 00:00</span>
          </div>

          <div className="flex items-center gap-2">
            {/* Subtitles Toggle button */}
            <button
              type="button"
              onClick={onToggleSubtitles}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                showSubtitles
                  ? 'bg-brand-500 text-white font-semibold'
                  : 'bg-white/10 text-slate-300 hover:bg-white/20'
              }`}
              title="إظهار / إخفاء الترجمة على الفيديو"
            >
              <Subtitles className="w-3.5 h-3.5" />
              <span>الترجمة {showSubtitles ? 'مفعّلة' : 'معطّلة'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Audio Track Selector (Original vs Dubbed vs Mixed) */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-600 font-semibold">
          <div className="flex items-center gap-1.5">
            <Volume2 className="w-4 h-4 text-brand-700" />
            <span>المسار الصوتي للمعاينة:</span>
          </div>
          <span className="text-[11px] text-slate-400 font-normal">
            {audioTrack === 'dubbed' ? 'الصوت الإنجليزي المعالج' : audioTrack === 'original' ? 'الصوت الأصلي للخطيب' : 'مزيج ثنائي متزامن'}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => onChangeAudioTrack('dubbed')}
            className={`py-2 px-2.5 rounded-lg font-medium transition-all text-center border ${
              audioTrack === 'dubbed'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm font-bold'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            المدبلج (الإنجليزية)
          </button>

          <button
            type="button"
            onClick={() => onChangeAudioTrack('original')}
            className={`py-2 px-2.5 rounded-lg font-medium transition-all text-center border ${
              audioTrack === 'original'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm font-bold'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            الأصل (العربية)
          </button>

          <button
            type="button"
            onClick={() => onChangeAudioTrack('mixed')}
            className={`py-2 px-2.5 rounded-lg font-medium transition-all text-center border ${
              audioTrack === 'mixed'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm font-bold'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            مزيج متوازن
          </button>
        </div>
      </div>
    </div>
  );
};
