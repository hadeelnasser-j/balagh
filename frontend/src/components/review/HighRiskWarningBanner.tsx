import React from 'react';
import { AlertOctagon, RotateCcw, ShieldX } from 'lucide-react';

interface HighRiskWarningBannerProps {
  message: string;
  onRestore: () => void;
}

export const HighRiskWarningBanner: React.FC<HighRiskWarningBannerProps> = ({
  message,
  onRestore,
}) => {
  return (
    <div
      role="alert"
      className="w-full bg-rose-50 border-2 border-rose-400/80 rounded-2xl p-5 shadow-premium animate-in fade-in slide-in-from-top-2 duration-300"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5">
            <AlertOctagon className="w-6 h-6 animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-rose-200 text-rose-900 border border-rose-300">
                <ShieldX className="w-3.5 h-3.5" />
                تنبيه مرتفع الخطورة
              </span>
            </div>

            <p className="text-xs sm:text-sm font-semibold text-rose-900 leading-relaxed max-w-xl">
              {message}
            </p>
            <p className="text-[11px] text-rose-700 mt-1">
              تم إيقاف وتعطيل خيار الاعتماد لحماية الأمانة العلمية حتى تتم استعادة المعنى الشرعي الأصلي.
            </p>
          </div>
        </div>

        {/* Action to restore protected meaning */}
        <button
          type="button"
          onClick={onRestore}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-rose-700 hover:bg-rose-800 text-white font-bold text-xs sm:text-sm shadow-sm transition-all active:scale-98 shrink-0"
        >
          <RotateCcw className="w-4 h-4" />
          <span>استعادة المعنى المحمي</span>
        </button>

      </div>
    </div>
  );
};
