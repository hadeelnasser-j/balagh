import React from 'react';
import { CheckCircle2, Loader2, CircleDashed, AlertCircle } from 'lucide-react';
import { ProcessingStage, StageStatus } from '../types';

interface StageItemProps {
  stage: ProcessingStage;
  isCurrent: boolean;
}

export const StageItem: React.FC<StageItemProps> = ({ stage, isCurrent }) => {
  const getStatusBadge = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>مكتمل</span>
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-50 text-brand-800 border border-brand-200 shadow-sm animate-pulse">
            <Loader2 className="w-3.5 h-3.5 text-brand-700 animate-spin shrink-0" />
            <span>جاري التنفيذ</span>
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span>خطأ</span>
          </span>
        );
      case 'pending':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-50 text-slate-500 border border-slate-200/70">
            <CircleDashed className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>لم يبدأ</span>
          </span>
        );
    }
  };

  return (
    <div
      className={`flex items-center justify-between p-4 sm:p-4.5 rounded-xl border transition-all duration-300 ${
        isCurrent || stage.status === 'in_progress'
          ? 'bg-brand-50/40 border-brand-300 ring-2 ring-brand-700/10 shadow-sm'
          : stage.status === 'completed'
          ? 'bg-white border-slate-200/80 hover:bg-slate-50/40'
          : stage.status === 'error'
          ? 'bg-rose-50/30 border-rose-200'
          : 'bg-white/60 border-slate-100 opacity-80'
      }`}
    >
      <div className="flex items-center gap-3.5">
        {/* Stage Number Badge */}
        <div
          className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold font-mono transition-colors ${
            stage.status === 'completed'
              ? 'bg-emerald-100 text-emerald-800'
              : stage.status === 'in_progress'
              ? 'bg-brand-700 text-white shadow-sm'
              : stage.status === 'error'
              ? 'bg-rose-100 text-rose-800'
              : 'bg-slate-100 text-slate-500'
          }`}
        >
          {stage.number}
        </div>

        <div>
          <h4
            className={`text-sm font-bold tracking-tight ${
              stage.status === 'in_progress'
                ? 'text-brand-950 font-extrabold'
                : stage.status === 'completed'
                ? 'text-slate-800'
                : stage.status === 'error'
                ? 'text-rose-900'
                : 'text-slate-600'
            }`}
          >
            {stage.title}
          </h4>
          {stage.description && (
            <p className="text-xs text-slate-500 mt-0.5 hidden sm:block">
              {stage.description}
            </p>
          )}
        </div>
      </div>

      {/* Explicit status: icon + text */}
      <div className="shrink-0 mr-3">
        {getStatusBadge(stage.status)}
      </div>
    </div>
  );
};
