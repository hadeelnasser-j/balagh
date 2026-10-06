import React, { useState } from 'react';
import { TranslationSegment, TimingStatus } from '../../types';
import { 
  Play, 
  Volume2, 
  Edit3, 
  Save, 
  CheckCircle2, 
  AlertTriangle, 
  AlertCircle, 
  ShieldCheck, 
  ShieldAlert, 
  Sparkles, 
  RotateCcw, 
  Check, 
  Layers
} from 'lucide-react';

interface TranslationSegmentCardProps {
  segment: TranslationSegment;
  isPlaying: boolean;
  isSelected: boolean;
  onPlay: (segmentId: string) => void;
  onSelect: (segmentId: string) => void;
  onUpdateTranslation: (segmentId: string, newEnglishText: string) => void;
  onApplyShorterAlternative?: (segmentId: string) => void;
  onRegenerate?: (segmentId: string) => void;
  onToggleApproval: (segmentId: string) => void;
}

export const TranslationSegmentCard: React.FC<TranslationSegmentCardProps> = ({
  segment,
  isPlaying,
  isSelected,
  onPlay,
  onSelect,
  onUpdateTranslation,
  onApplyShorterAlternative,
  onRegenerate,
  onToggleApproval,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(segment.englishTranslation);

  const handleSave = () => {
    setIsEditing(false);
    onUpdateTranslation(segment.id, editText);
  };

  const handleCancel = () => {
    setEditText(segment.englishTranslation);
    setIsEditing(false);
  };

  const getTimingStatusBadge = (status: TimingStatus, diffPercent: number) => {
    const formattedDiff = `${diffPercent > 0 ? '+' : ''}${diffPercent.toFixed(1)}%`;

    switch (status) {
      case 'suitable':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>متطابق زمنياً ({formattedDiff})</span>
          </span>
        );
      case 'needs_improvement':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>يحتاج تحسين زمني ({formattedDiff})</span>
          </span>
        );
      case 'needs_adjustment':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span>فارق كبير ({formattedDiff})</span>
          </span>
        );
    }
  };

  return (
    <div
      onClick={() => onSelect(segment.id)}
      className={`rounded-2xl border transition-all duration-200 p-5 sm:p-6 space-y-4 cursor-default ${
        isSelected
          ? 'bg-white border-brand-400 ring-2 ring-brand-800/10 shadow-premium'
          : 'bg-white border-slate-200/90 hover:border-slate-300 shadow-subtle'
      }`}
    >
      {/* 1. Header: Segment Timestamp, Timing Badge, Meaning Lock Badge, and Play Audio */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
        <div className="flex items-center gap-2.5">
          {/* Simulated Dubbed Audio Play button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onPlay(segment.id);
            }}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              isPlaying
                ? 'bg-brand-700 text-white shadow-sm'
                : 'bg-slate-100 hover:bg-brand-50 text-slate-700 hover:text-brand-800'
            }`}
            title="الاستماع للصوت الإنجليزي المدبلج"
          >
            {isPlaying ? (
              <>
                <Volume2 className="w-3.5 h-3.5 animate-pulse" />
                <span>قيد الاستماع</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>استماع للدبلجة</span>
              </>
            )}
          </button>

          {/* Time range */}
          <span className="font-mono text-xs font-bold text-slate-700 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200/60">
            {segment.timestamp}
          </span>
        </div>

        {/* Badges: Timing Status + Meaning Lock */}
        <div className="flex items-center gap-2 flex-wrap">
          {getTimingStatusBadge(segment.timingStatus, segment.durationDifferencePercent)}

          {segment.isMeaningPreserved ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>المعنى محفوظ</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-300">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>انتهاك لقفل المعنى</span>
            </span>
          )}
        </div>
      </div>

      {/* 2. Side-by-Side Texts: Original Arabic & English Dubbing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
        
        {/* Right (Arabic Source) */}
        <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold mb-2">
              <span>النص العربي الأصلي:</span>
              <span className="font-mono text-[11px] text-slate-400">مدة الإلقاء: {segment.sourceDurationSec.toFixed(1)}ث</span>
            </div>
            <p className="text-sm sm:text-base text-slate-800 font-arabic leading-relaxed">
              {segment.arabicText}
            </p>
          </div>
        </div>

        {/* Left (English Translation) */}
        <div className="p-4 rounded-xl bg-brand-50/20 border border-brand-200/70 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-brand-900 font-semibold mb-2">
              <div className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-brand-700" />
                <span>الترجمة الإنجليزية المعتمدة:</span>
              </div>
              <span className="font-mono text-[11px] text-brand-800">
                مدة الصوت: {segment.translatedDurationSec.toFixed(1)}ث
              </span>
            </div>

            {isEditing ? (
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                dir="ltr"
                rows={3}
                className="w-full p-2.5 rounded-lg border border-brand-300 bg-white text-slate-900 text-sm font-sans focus:ring-2 focus:ring-brand-500/20 focus:outline-none transition-all leading-relaxed"
              />
            ) : (
              <p dir="ltr" className="text-sm sm:text-base text-slate-900 font-sans leading-relaxed text-left">
                {segment.englishTranslation}
              </p>
            )}
          </div>

          {/* Edit actions */}
          <div className="flex items-center justify-end gap-2 pt-2.5 mt-2 border-t border-brand-100">
            {isEditing ? (
              <>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-2.5 py-1 rounded text-xs text-slate-500 hover:bg-slate-100"
                >
                  إلغاء
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-brand-800 text-white text-xs font-semibold shadow-sm hover:bg-brand-700"
                >
                  <Save className="w-3 h-3" />
                  <span>حفظ التعديل</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-brand-800 font-medium py-1 px-2 rounded hover:bg-white/60 transition-colors"
              >
                <Edit3 className="w-3 h-3" />
                <span>تعديل الصياغة</span>
              </button>
            )}
          </div>
        </div>

      </div>

      {/* Meaning Alert Warning if violated */}
      {!segment.isMeaningPreserved && segment.missingMeaningText && (
        <div className="p-3 rounded-xl bg-rose-50 border border-rose-300 text-xs text-rose-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span><strong>تنبيه دلالي:</strong> {segment.missingMeaningText}</span>
        </div>
      )}

      {/* 3. Shorter Alternative Recommendation Box (Key Feature for Screen 4) */}
      {segment.shorterAlternative && segment.timingStatus === 'needs_improvement' && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50 to-amber-50/40 border border-amber-200/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
              <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
              <span>اقتراح الذكاء الاصطناعي لاختصار النص ومطابقة مدة الفيديو (18.2 ثانية):</span>
            </div>
            <p dir="ltr" className="text-xs sm:text-sm font-sans text-slate-800 text-left pl-5">
              "{segment.shorterAlternative}"
            </p>
            <p className="text-[11px] text-amber-800">
              * يحافظ هذا البديل على مصطلحات الزكاة والنصاب بدقة تامة ويقلل الفارق الزمني إلى +1.1% فقط.
            </p>
          </div>

          {onApplyShorterAlternative && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onApplyShorterAlternative(segment.id);
              }}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-sm transition-all active:scale-98 shrink-0"
            >
              <Check className="w-3.5 h-3.5" />
              <span>تطبيق البديل الأقصر</span>
            </button>
          )}
        </div>
      )}

      {/* 4. Segment Footer: Regenerate Button & Approval Button */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
        {/* Re-generate option */}
        <div className="flex items-center gap-2">
          {onRegenerate && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onRegenerate(segment.id);
              }}
              disabled={segment.isRegenerating}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition-colors"
            >
              <RotateCcw className={`w-3 h-3 ${segment.isRegenerating ? 'animate-spin text-brand-700' : 'text-slate-500'}`} />
              <span>{segment.isRegenerating ? 'جارٍ إعادة التوليد...' : 'إعادة توليد ذكية'}</span>
            </button>
          )}
        </div>

        {/* Approval Button for this segment */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleApproval(segment.id);
          }}
          disabled={!segment.isMeaningPreserved}
          className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
            segment.isApproved
              ? 'bg-emerald-600 text-white cursor-pointer hover:bg-emerald-700'
              : !segment.isMeaningPreserved
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
              : 'bg-brand-800 hover:bg-brand-700 text-white cursor-pointer active:scale-98'
          }`}
          title={!segment.isMeaningPreserved ? 'لا يمكن اعتماد المقطع مع وجود انتهاك لقفل المعنى' : 'اعتماد هذا المقطع'}
        >
          <Check className="w-3.5 h-3.5" />
          <span>{segment.isApproved ? 'تم اعتماد المقطع ✓' : 'اعتماد هذا المقطع'}</span>
        </button>
      </div>
    </div>
  );
};
