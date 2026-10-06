import React from 'react';
import { ArrowLeft, Globe2 } from 'lucide-react';

interface LanguageSelectorProps {
  sourceLanguage?: string;
  targetLanguage?: string;
  onTargetChange?: (lang: string) => void;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  sourceLanguage = 'العربية',
  targetLanguage = 'الإنجليزية',
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-6">
      <div className="flex items-center gap-2 mb-4">
        <Globe2 className="w-5 h-5 text-brand-700" />
        <h3 className="text-base font-bold text-slate-800">
          إعدادات اللغات
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-[1fr,auto,1fr] items-center gap-3">
        {/* Source Language */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-500">
            لغة المصدر (الأصلية)
          </label>
          <div className="h-12 px-4 rounded-xl border border-slate-200 bg-slate-50/80 flex items-center justify-between text-slate-800 font-medium text-sm">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              {sourceLanguage}
            </span>
            <span className="text-xs text-slate-400 bg-white px-2 py-0.5 rounded border border-slate-200/60">
              تلقائي
            </span>
          </div>
        </div>

        {/* Direction Indicator */}
        <div className="flex justify-center items-center pt-5">
          <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 border border-slate-200">
            <ArrowLeft className="w-4 h-4" />
          </div>
        </div>

        {/* Target Language */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-500">
            لغة الدبلجة المستهدفة
          </label>
          <div className="h-12 px-4 rounded-xl border border-brand-200 bg-brand-50/30 flex items-center justify-between text-slate-900 font-medium text-sm">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-600" />
              {targetLanguage}
            </span>
            <span className="text-xs text-brand-700 bg-brand-100/60 px-2 py-0.5 rounded font-semibold">
              EN
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
