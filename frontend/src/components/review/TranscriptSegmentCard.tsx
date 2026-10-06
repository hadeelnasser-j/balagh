import React, { useState } from 'react';
import { Play, Edit3, Save, CheckCircle2, AlertTriangle, AlertCircle, Volume2 } from 'lucide-react';
import { TranscriptSegment, ConfidenceLevel } from '../../types';

interface TranscriptSegmentCardProps {
  segment: TranscriptSegment;
  isPlaying: boolean;
  onPlay: (segmentId: string) => void;
  onUpdateText: (segmentId: string, newText: string) => void;
}

export const TranscriptSegmentCard: React.FC<TranscriptSegmentCardProps> = ({
  segment,
  isPlaying,
  onPlay,
  onUpdateText,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(segment.text);

  const handleSave = () => {
    setIsEditing(false);
    onUpdateText(segment.id, editText);
  };

  const getConfidenceBadge = (confidence: ConfidenceLevel, percent?: number) => {
    switch (confidence) {
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>مرتفعة {percent ? `(${percent}%)` : ''}</span>
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>متوسطة {percent ? `(${percent}%)` : ''}</span>
          </span>
        );
      case 'needs_review':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span>يحتاج مراجعة</span>
          </span>
        );
    }
  };

  return (
    <div
      className={`rounded-2xl border transition-all duration-200 p-4 sm:p-5 ${
        isPlaying
          ? 'bg-brand-50/50 border-brand-400 ring-2 ring-brand-700/10 shadow-sm'
          : 'bg-white border-slate-200/90 hover:border-slate-300 shadow-subtle'
      }`}
    >
      {/* Header: Time range + Confidence Badge + Quick play */}
      <div className="flex items-center justify-between gap-3 mb-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          {/* Play Segment Button */}
          <button
            type="button"
            onClick={() => onPlay(segment.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              isPlaying
                ? 'bg-brand-700 text-white shadow-sm'
                : 'bg-slate-100 hover:bg-brand-50 text-slate-700 hover:text-brand-800'
            }`}
            title="تشغيل المقطع الصوتي"
          >
            {isPlaying ? (
              <>
                <Volume2 className="w-3.5 h-3.5 animate-pulse" />
                <span>قيد التشغيل</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>تشغيل المقطع</span>
              </>
            )}
          </button>

          {/* Time range */}
          <span className="font-mono text-xs font-bold text-slate-600 bg-slate-50 px-2 py-1 rounded border border-slate-200/60">
            {segment.startTime} — {segment.endTime}
          </span>
        </div>

        {/* Confidence Indicator (Icon + Text) */}
        <div>
          {getConfidenceBadge(segment.confidence, segment.confidencePercent)}
        </div>
      </div>

      {/* Segment Arabic Text Content */}
      <div className="my-3">
        {isEditing ? (
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            dir="rtl"
            rows={3}
            className="w-full p-3 rounded-xl border border-brand-300 bg-brand-50/20 text-slate-900 text-sm font-arabic focus:ring-2 focus:ring-brand-500/20 focus:outline-none transition-all leading-relaxed"
          />
        ) : (
          <p className="text-sm sm:text-base text-slate-800 font-arabic leading-relaxed">
            {segment.text}
          </p>
        )}
      </div>

      {/* Action Footer: Edit text / Save changes */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-400">
        <div>
          {isEditing && (
            <span className="text-brand-700 font-medium text-[11px]">
              * جاري تعديل النص المفرغ
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                type="button"
                onClick={() => {
                  setEditText(segment.text);
                  setIsEditing(false);
                }}
                className="px-3 py-1.5 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-brand-800 hover:bg-brand-700 text-white font-medium shadow-sm transition-all active:scale-98"
              >
                <Save className="w-3.5 h-3.5" />
                <span>حفظ التغييرات</span>
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>تعديل</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
