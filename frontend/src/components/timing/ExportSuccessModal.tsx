import React from 'react';
import { CheckCircle2, Download, Film, FileText, Music, X, ArrowRight, ShieldCheck } from 'lucide-react';

interface ExportSuccessModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBackToHome: () => void;
  videoName: string;
}

export const ExportSuccessModal: React.FC<ExportSuccessModalProps> = ({
  isOpen,
  onClose,
  onBackToHome,
  videoName,
}) => {
  if (!isOpen) return null;

  const handleDownload = (filename: string) => {
    alert(`بدء تحميل ملف: ${filename}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-lg bg-white rounded-3xl border border-slate-200 shadow-2xl p-6 sm:p-7 relative text-slate-800 font-arabic animate-in zoom-in-95 duration-200"
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 left-5 p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Success Icon */}
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center border-2 border-emerald-200/80 mb-4 mx-auto shadow-sm">
          <CheckCircle2 className="w-8 h-8" />
        </div>

        {/* Title */}
        <div className="text-center space-y-1.5 mb-6">
          <h3 className="text-xl sm:text-2xl font-bold text-slate-900">
            اكتمل تصدير الفيديو المدبلج بنجاح!
          </h3>
          <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
            تمت مطابقة زمن الإلقاء الصوتي بدقة، وتطبيق الترجمة المعتمدة مع الحفاظ الصارم على المعاني الشرعية الإسلامية.
          </p>
        </div>

        {/* Quality Certificate Badge */}
        <div className="p-3 rounded-2xl bg-emerald-50/80 border border-emerald-200/80 flex items-center justify-between text-xs mb-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
            <span className="font-bold text-emerald-900">شهادة تدقيق بلاغ:</span>
          </div>
          <div className="flex items-center gap-3 font-semibold text-emerald-800">
            <span>تطابق زمني 99%</span>
            <span>•</span>
            <span>أمانة شرعية 100%</span>
          </div>
        </div>

        {/* Exported Files List */}
        <div className="space-y-2.5 mb-6">
          {/* 1. Final Dubbed Video */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex items-center justify-between gap-3 hover:bg-slate-100/60 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-brand-100 text-brand-800 flex items-center justify-center shrink-0">
                <Film className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-bold text-slate-800">
                  الفيديو النهائي مدبلج (MP4 1080p)
                </p>
                <span className="text-[11px] text-slate-400 font-mono">
                  {videoName.replace('.mp4', '_dubbed_en.mp4')} • 24.8 MB
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleDownload('dubbed_video_1080p.mp4')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-800 hover:bg-brand-700 text-white text-xs font-semibold shadow-sm transition-all active:scale-98"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تحميل</span>
            </button>
          </div>

          {/* 2. Subtitles SRT */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex items-center justify-between gap-3 hover:bg-slate-100/60 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-bold text-slate-800">
                  ملف الترجمة المتزامن (SRT)
                </p>
                <span className="text-[11px] text-slate-400 font-mono">
                  subtitles_en_timed.srt • 1.4 KB
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleDownload('subtitles_en_timed.srt')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-all"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>تحميل</span>
            </button>
          </div>

          {/* 3. Audio Track WAV */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex items-center justify-between gap-3 hover:bg-slate-100/60 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center shrink-0">
                <Music className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-bold text-slate-800">
                  المسار الصوتي الإنجليزي المعزول (WAV)
                </p>
                <span className="text-[11px] text-slate-400 font-mono">
                  audio_voiceover_en.wav • 8.6 MB
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleDownload('audio_voiceover_en.wav')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-all"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>تحميل</span>
            </button>
          </div>
        </div>

        {/* Modal Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onBackToHome}
            className="w-full sm:w-auto flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-100 font-bold text-xs sm:text-sm transition-all"
          >
            <span>بدء مشروع جديد</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => handleDownload('balagh_export_bundle.zip')}
            className="w-full sm:w-auto flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-brand-800 hover:bg-brand-700 text-white font-bold text-xs sm:text-sm shadow-premium transition-all active:scale-98"
          >
            <Download className="w-4 h-4 text-amber-300" />
            <span>تحميل الحزمة كاملة (ZIP)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
