import React from 'react';
import { Sliders, Timer, Check } from 'lucide-react';
import { DubbingMode } from '../types';

interface DubbingModeSelectorProps {
  selectedMode?: DubbingMode;
  onSelectMode: (mode: DubbingMode) => void;
}

interface ModeOption {
  id: DubbingMode;
  title: string;
  description: string;
  badge?: string;
  icon: React.ElementType;
}

const MODES: ModeOption[] = [

  {
    id: 'timed',
    title: 'الزمنية',
    description: 'توازن بين الحفاظ على المعنى ومدة المقطع.',
    badge: 'الوضع الافتراضي المُوصى به',
    icon: Timer,
  },

];

export const DubbingModeSelector: React.FC<DubbingModeSelectorProps> = ({
  selectedMode = 'timed',
  onSelectMode,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-brand-700" />
          <h3 className="text-base font-bold text-slate-800">
            نمط الدبلجة الواعية
          </h3>
        </div>
        <span className="text-xs text-slate-400 hidden sm:inline">
          اختر المنهجية الأنسب للمحتوى
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5" role="radiogroup" aria-label="نمط الدبلجة الواعية">
        {MODES.map((mode) => {
          const isSelected = selectedMode === mode.id;
          const Icon = mode.icon;

          return (
            <div
              key={mode.id}
              role="radio"
              aria-checked={isSelected}
              tabIndex={0}
              onClick={() => onSelectMode(mode.id)}
              onKeyDown={(e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault();
                  onSelectMode(mode.id);
                }
              }}
              className={`group relative rounded-xl p-4 sm:p-4.5 border-2 transition-all duration-200 cursor-pointer flex flex-col justify-between select-none ${
                isSelected
                  ? 'border-brand-700 bg-brand-50/40 ring-2 ring-brand-700/15 shadow-sm'
                  : 'border-slate-200/90 bg-white hover:border-slate-300 hover:bg-slate-50/50'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                        isSelected
                          ? 'bg-brand-800 text-white shadow-sm'
                          : 'bg-slate-100 text-slate-500 group-hover:bg-slate-200/80'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    <h4 className={`text-sm tracking-tight ${isSelected ? 'font-bold text-slate-900' : 'font-semibold text-slate-700'}`}>
                      {mode.title}
                    </h4>
                  </div>

                  {/* High clarity custom radio indicator */}
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center transition-all ${
                      isSelected
                        ? 'bg-brand-700 text-white shadow-sm'
                        : 'border-2 border-slate-300 bg-transparent group-hover:border-slate-400'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </div>
                </div>

                <p className="text-xs text-slate-500 leading-relaxed mt-2.5">
                  {mode.description}
                </p>
              </div>

              {mode.badge && (
                <div className="mt-3.5 pt-2.5 border-t border-brand-100/70">
                  <span className="text-[10px] font-semibold text-brand-800 bg-brand-100/80 px-2 py-0.5 rounded-full inline-block">
                    {mode.badge}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
