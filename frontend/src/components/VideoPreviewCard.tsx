import React from 'react';
import { RefreshCw, Trash2, Clock, HardDrive, CheckCircle2, Film } from 'lucide-react';
import { VideoMetadata } from '../types';
import { formatFileSize, formatDuration } from '../utils/formatters';

interface VideoPreviewCardProps {
  video: VideoMetadata;
  onReplace: () => void;
  onDelete: () => void;
}

export const VideoPreviewCard: React.FC<VideoPreviewCardProps> = ({
  video,
  onReplace,
  onDelete,
}) => {

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200/90 shadow-premium p-6 sm:p-7 transition-all">
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        
        {/* Video Player Preview */}
        <div className="w-full lg:w-72 sm:w-80 shrink-0 rounded-xl overflow-hidden bg-slate-900 aspect-video relative shadow-inner border border-slate-800">
          <video
            src={video.previewUrl}
            controls
            className="w-full h-full object-contain"
            playsInline
          />
          <div className="absolute top-2.5 right-2.5 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded text-[11px] font-mono text-white flex items-center gap-1">
            <Film className="w-3 h-3 text-brand-300" />
            <span>معاينة</span>
          </div>
        </div>

        {/* Video Details & Meta */}
        <div className="flex-1 w-full flex flex-col justify-between self-stretch">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                <CheckCircle2 className="w-3.5 h-3.5" />
                ملف صالح للدبلجة
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {video.name.split('.').pop()?.toUpperCase()}
              </span>
            </div>

            <h3 className="text-lg font-bold text-slate-900 break-all leading-snug" title={video.name}>
              {video.name}
            </h3>

            {/* Meta tags: Size and Duration */}
            <div className="mt-4 flex flex-wrap gap-4 text-xs sm:text-sm text-slate-600">
              <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                <HardDrive className="w-4 h-4 text-slate-400" />
                <span>حجم الملف:</span>
                <span className="font-semibold text-slate-800 font-mono">{formatFileSize(video.sizeBytes)}</span>
              </div>

              <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                <Clock className="w-4 h-4 text-slate-400" />
                <span>المدة:</span>
                <span className="font-semibold text-slate-800 font-mono">{formatDuration(video.durationSeconds)}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons: Replace & Delete */}
          <div className="mt-6 pt-5 border-t border-slate-100 flex items-center justify-between">
            <div className="text-xs text-slate-400 hidden sm:block">
              جاهز لتحديد إعدادات المعالجة
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onReplace}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors active:scale-98"
              >
                <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
                <span>استبدال</span>
              </button>

              <button
                type="button"
                onClick={onDelete}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100/80 transition-colors active:scale-98"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                <span>حذف</span>
              </button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
