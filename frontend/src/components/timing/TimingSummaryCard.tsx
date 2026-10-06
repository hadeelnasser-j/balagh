import React from 'react';
import { TranslationSegment, DubbingMode, DubbingPacing } from '../../types';
import { Activity, Sliders, ShieldCheck } from 'lucide-react';

interface TimingSummaryCardProps {
  segments: TranslationSegment[];
  dubbingMode: DubbingMode;
  pacing: DubbingPacing;
  onChangePacing: (pacing: DubbingPacing) => void;
}

export const TimingSummaryCard: React.FC<TimingSummaryCardProps> = ({
  segments,
  dubbingMode,
  pacing,
  onChangePacing,
}) => {
  const suitableCount = segments.filter((s) => s.timingStatus === 'suitable').length;
  const needsImprovementCount = segments.filter((s) => s.timingStatus === 'needs_improvement').length;

  const totalSourceSec = segments.reduce((acc, s) => acc + s.sourceDurationSec, 0);
  const totalTranslatedSec = segments.reduce((acc, s) => acc + s.translatedDurationSec, 0);
  const durationDiffSec = totalTranslatedSec - totalSourceSec;

  // Calculate overall timing sync score (0 - 100%)
  const syncScore = Math.min(100, Math.round((suitableCount / segments.length) * 100));

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6 space-y-5 transition-all">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center border border-brand-200/60">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-base font-bold text-slate-900">مؤشرات التطابق والسرعة</h4>
            <p className="text-xs text-slate-400">تقييم توازن التوقيت بين المتحدث الأصلي والدبلجة</p>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
          تزامن حي
        </span>
      </div>

      {/* Sync Score Circular / Metric Widget */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {/* Score */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-medium">نسبة التطابق الزمني</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className={`text-2xl font-extrabold font-mono ${syncScore >= 95 ? 'text-emerald-600' : 'text-amber-600'}`}>
              {syncScore}%
            </span>
            <span className="text-[10px] text-slate-400 font-arabic">
              {syncScore === 100 ? 'مثالي' : 'جيد جداً'}
            </span>
          </div>
        </div>

        {/* Source vs Translated Duration */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-medium">المدة الكلية (أصل / ترجمة)</span>
          <div className="flex items-baseline gap-1 mt-1 font-mono text-sm font-bold text-slate-800">
            <span>{totalSourceSec.toFixed(1)}ث</span>
            <span className="text-slate-400">/</span>
            <span className={durationDiffSec > 2 ? 'text-amber-700' : 'text-emerald-700'}>
              {totalTranslatedSec.toFixed(1)}ث
            </span>
          </div>
        </div>

        {/* Breakdown pill */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 flex flex-col justify-between col-span-2 sm:col-span-1">
          <span className="text-xs text-slate-500 font-medium">حالة المقاطع</span>
          <div className="flex items-center gap-2 mt-1 text-xs font-bold">
            <span className="text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded">
              {suitableCount} متطابق
            </span>
            {needsImprovementCount > 0 && (
              <span className="text-amber-700 bg-amber-100/70 px-2 py-0.5 rounded">
                {needsImprovementCount} يحتاج ضغط
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Pacing Speed Multiplier Selector */}
      <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/70 space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
            <Sliders className="w-3.5 h-3.5 text-brand-700" />
            <span>وتيرة الإلقاء الصوتي (Pacing):</span>
          </div>
          <span className="text-[11px] text-slate-400">تعديل السرعة لمطابقة حركة الشفاه</span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => onChangePacing('normal')}
            className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all text-center ${
              pacing === 'normal'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <div>1.0x طبيعي</div>
            <div className={`text-[10px] ${pacing === 'normal' ? 'text-brand-100' : 'text-slate-400'}`}>نبرة هادئة</div>
          </button>

          <button
            type="button"
            onClick={() => onChangePacing('natural_fast')}
            className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all text-center ${
              pacing === 'natural_fast'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <div>1.05x متزن</div>
            <div className={`text-[10px] ${pacing === 'natural_fast' ? 'text-brand-100' : 'text-slate-400'}`}>موصى به للشفاه</div>
          </button>

          <button
            type="button"
            onClick={() => onChangePacing('dynamic')}
            className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all text-center ${
              pacing === 'dynamic'
                ? 'bg-brand-800 text-white border-brand-800 shadow-sm'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <div>1.10x ديناميكي</div>
            <div className={`text-[10px] ${pacing === 'dynamic' ? 'text-brand-100' : 'text-slate-400'}`}>ضغط تلقائي</div>
          </button>
        </div>
      </div>

      {/* Mode Guarantee Note */}
      <div className="p-3.5 rounded-xl bg-brand-50/60 border border-brand-200/60 text-xs text-brand-900 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-brand-700 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          نمط الدبلجة: <strong>{dubbingMode === 'faithful' ? 'الأمينة' : dubbingMode === 'timed' ? 'الزمنية (Timed)' : 'المبسطة'}</strong> — يُعطي الأولوية لمطابقة أوقات التحدث وحركات الشفاه مع المحافظة التامة على المصطلحات الشرعية المعتمدة.
        </p>
      </div>
    </div>
  );
};
