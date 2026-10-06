import React from 'react';
import { TranslationSegment } from '../../types';
import { Clock, CheckCircle2, AlertTriangle } from 'lucide-react';

interface InteractiveTimelineBarProps {
  segments: TranslationSegment[];
  activeSegmentId: string | null;
  onSelectSegment: (id: string) => void;
  totalDurationSec?: number;
}

export const InteractiveTimelineBar: React.FC<InteractiveTimelineBarProps> = ({
  segments,
  activeSegmentId,
  onSelectSegment,
  totalDurationSec = 48,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6 transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center border border-brand-200/60">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span>المخطط الزمني للمقاطع وتزامن الإلقاء</span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-brand-50 text-brand-800 border border-brand-200/60">
                00:48 دقيقة
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              انقر على أي مقطع لمعاينته وضبط سرعة التحدث وتطابق الترجمة
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>متطابق</span>
          </span>
          <span className="inline-flex items-center gap-1.5 text-amber-700 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>يحتاج تحسين</span>
          </span>
        </div>
      </div>

      {/* Visual Timeline Bar */}
      <div className="space-y-2">
        <div className="w-full bg-slate-100 rounded-xl p-1.5 border border-slate-200/70 flex gap-1.5 h-20 items-stretch overflow-hidden">
          {segments.map((segment, index) => {
            const isSelected = activeSegmentId === segment.id;
            const isSuitable = segment.timingStatus === 'suitable';

            // Calculate proportional width
            const widthPercent = (segment.sourceDurationSec / totalDurationSec) * 100;

            return (
              <button
                key={segment.id}
                type="button"
                onClick={() => onSelectSegment(segment.id)}
                style={{ width: `${widthPercent}%` }}
                className={`relative flex flex-col justify-between p-2 rounded-lg text-right transition-all group overflow-hidden border ${
                  isSelected
                    ? isSuitable
                      ? 'bg-emerald-50 border-emerald-400 ring-2 ring-emerald-500/20 shadow-sm'
                      : 'bg-amber-50 border-amber-400 ring-2 ring-amber-500/20 shadow-sm'
                    : isSuitable
                    ? 'bg-emerald-50/50 hover:bg-emerald-50 border-emerald-200/70 text-slate-700'
                    : 'bg-amber-50/60 hover:bg-amber-50 border-amber-200/80 text-slate-700'
                }`}
                title={`مقطع ${index + 1}: ${segment.timestamp}`}
              >
                {/* Simulated Audio Waveform SVG Background */}
                <div className="absolute inset-0 flex items-center justify-around opacity-15 pointer-events-none px-1">
                  {[40, 75, 55, 90, 60, 45, 80, 65, 95, 50, 70, 40].map((h, i) => (
                    <div
                      key={i}
                      style={{ height: `${h}%` }}
                      className={`w-1 rounded-full ${isSuitable ? 'bg-emerald-800' : 'bg-amber-800'}`}
                    />
                  ))}
                </div>

                {/* Top info in segment bar */}
                <div className="relative z-10 flex items-center justify-between gap-1 w-full">
                  <span className="text-[11px] font-bold text-slate-800 font-arabic truncate">
                    مقطع {index + 1}
                  </span>
                  {isSuitable ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  )}
                </div>

                {/* Bottom info: timestamps & diff */}
                <div className="relative z-10 flex items-center justify-between text-[10px] w-full pt-1 border-t border-black/5">
                  <span className="font-mono text-slate-500 text-[10px]">
                    {segment.timestamp}
                  </span>
                  <span
                    className={`font-mono font-bold px-1 rounded ${
                      isSuitable
                        ? 'text-emerald-700 bg-emerald-100/60'
                        : 'text-amber-800 bg-amber-100/80'
                    }`}
                  >
                    {segment.durationDifferencePercent > 0 ? '+' : ''}
                    {segment.durationDifferencePercent.toFixed(1)}%
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Timeline Time Ruler */}
        <div className="flex items-center justify-between px-1 text-[11px] font-mono text-slate-400">
          <span>00:00</span>
          <span>00:14</span>
          <span>00:32</span>
          <span>00:48</span>
        </div>
      </div>
    </div>
  );
};
