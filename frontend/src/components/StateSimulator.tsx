import React from 'react';
import { Layers, CheckCircle2, AlertTriangle, FileX, ClockAlert, RefreshCw, Sparkles } from 'lucide-react';

export type DemoStateType =
  | 'empty'
  | 'valid'
  | 'invalid_format'
  | 'file_too_large'
  | 'duration_exceeded'
  | 'upload_error';

interface StateSimulatorProps {
  currentState: DemoStateType;
  onSelectState: (state: DemoStateType) => void;
}

export const StateSimulator: React.FC<StateSimulatorProps> = ({
  currentState,
  onSelectState,
}) => {
  const states: { id: DemoStateType; label: string; icon: React.ElementType }[] = [
    { id: 'empty', label: '1. الحالة الفارغة', icon: Layers },
    { id: 'valid', label: '2. فيديو صالح', icon: CheckCircle2 },
    { id: 'invalid_format', label: '3. صيغة غير مدعومة', icon: FileX },
    { id: 'file_too_large', label: '4. حجم أكبر من 20MB', icon: AlertTriangle },
    { id: 'duration_exceeded', label: '5. مدة أطول من دقيقة', icon: ClockAlert },
    { id: 'upload_error', label: '6. خطأ مع إعادة المحاولة', icon: RefreshCw },
  ];

  return (
    <div className="w-full bg-slate-900 text-slate-200 border-b border-slate-800 py-2.5 px-4 text-xs select-none">
      <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>اختبار الحالات الست (MVP State Switcher):</span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {states.map((st) => {
            const Icon = st.icon;
            const isActive = currentState === st.id;
            return (
              <button
                key={st.id}
                onClick={() => onSelectState(st.id)}
                type="button"
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all text-xs ${
                  isActive
                    ? 'bg-brand-600 text-white font-semibold shadow-sm ring-1 ring-white/20'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{st.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
