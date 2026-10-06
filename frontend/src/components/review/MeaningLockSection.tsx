import React from 'react';
import { Lock, Unlock, ShieldCheck, AlertCircle } from 'lucide-react';
import { ProtectedMeaning } from '../../types';

interface MeaningLockSectionProps {
  meanings: ProtectedMeaning[];
  onToggleViolationTest?: (meaningId: string) => void;
}

export const MeaningLockSection: React.FC<MeaningLockSectionProps> = ({
  meanings,
  onToggleViolationTest,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6 transition-all">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center border border-brand-200/60">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-800">
              قفل المعنى | Meaning Lock
            </h3>
            <p className="text-xs text-slate-400">
              دلالات شرعية محكمة ومحمية برمجياً ضد التحريف أو النقص
            </p>
          </div>
        </div>

        <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-50 text-brand-800 border border-brand-200/60">
          <ShieldCheck className="w-3.5 h-3.5 text-brand-600" />
          <span>حماية دلالية مفعلة</span>
        </span>
      </div>

      {/* Protected Meanings list */}
      <div className="space-y-2.5">
        {meanings.map((m) => {
          const isViolated = m.isViolated;

          return (
            <div
              key={m.id}
              className={`flex items-center justify-between p-3.5 rounded-xl border transition-all ${
                isViolated
                  ? 'bg-rose-50/70 border-rose-300 ring-2 ring-rose-500/10'
                  : 'bg-slate-50/70 border-slate-200/80 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                    isViolated
                      ? 'bg-rose-100 text-rose-700'
                      : 'bg-brand-100/80 text-brand-800'
                  }`}
                >
                  {isViolated ? (
                    <Unlock className="w-4 h-4 animate-bounce" />
                  ) : (
                    <Lock className="w-4 h-4" />
                  )}
                </div>

                <div>
                  <p
                    className={`text-xs sm:text-sm font-semibold ${
                      isViolated
                        ? 'text-rose-900 line-through'
                        : 'text-slate-800'
                    }`}
                  >
                    {m.text}
                  </p>
                  {isViolated && (
                    <span className="text-[11px] text-rose-700 font-bold block mt-0.5">
                      ⚠️ انتهاك لقفل المعنى: تم حذف أو تشويه هذا المبدأ
                    </span>
                  )}
                </div>
              </div>

              {/* Status pill / interactive test toggle */}
              <div className="flex items-center gap-2">
                {isViolated ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200">
                    <AlertCircle className="w-3 h-3 text-rose-600" />
                    <span>منتهك</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                    <Lock className="w-3 h-3 text-emerald-600" />
                    <span>محمي</span>
                  </span>
                )}

                {onToggleViolationTest && (
                  <button
                    type="button"
                    onClick={() => onToggleViolationTest(m.id)}
                    className="text-[10px] text-slate-400 hover:text-slate-600 underline mr-1 transition-colors"
                    title="محاكاة تعديل النص وحذف هذا المعنى"
                  >
                    {isViolated ? 'استعادة' : 'اختبار حذف'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
