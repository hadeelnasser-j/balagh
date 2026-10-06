import React from 'react';
import type { PipelineStatus } from '../services/api';
import {
  WIZARD_STEPS,
  STEP_LABELS,
  WizardStep,
  stepState,
  canNavigate,
  canGoNext,
  previousStep,
  nextStep,
} from './wizard';

interface WizardBarProps {
  status: PipelineStatus;
  current: WizardStep;
  onNavigate: (step: WizardStep) => void;
}

const STATE_CLASSES = {
  completed: 'bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-sm',
  current: 'bg-brand-800 text-white font-bold shadow-sm border border-brand-700',
  available: 'bg-white text-slate-700 border border-slate-300 hover:border-brand-400 hover:bg-brand-50',
  locked: 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-70',
} as const;

const STATE_LABELS = { completed: 'مكتمل', current: 'الحالية', available: 'متاحة', locked: 'مقفلة' } as const;

export const WizardStepper: React.FC<WizardBarProps> = ({ status, current, onNavigate }) => (
  <nav aria-label="خطوات العمل" dir="rtl" className="w-full border-b border-slate-200 bg-white/95 px-4 py-3 shadow-sm">
    <ol className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-start gap-2">
      {WIZARD_STEPS.map((step, index) => {
        const state = stepState(status, step, current);
        const locked = state === 'locked';
        return (
          <li key={step}>
            <button
              type="button"
              disabled={locked}
              aria-current={state === 'current' ? 'step' : undefined}
              aria-label={`${STEP_LABELS[step]} - ${STATE_LABELS[state]}`}
              data-step={step}
              data-state={state}
              onClick={() => canNavigate(status, step) && onNavigate(step)}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-all duration-200 flex items-center gap-1.5 ${STATE_CLASSES[state]}`}
            >
              <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold bg-black/20">
                {index + 1}
              </span>
              <span>{STEP_LABELS[step]}</span>
            </button>
          </li>
        );
      })}
    </ol>
  </nav>
);

export const WizardControls: React.FC<WizardBarProps> = ({ status, current, onNavigate }) => {
  const previous = previousStep(current);
  const next = nextStep(current);
  return (
    <div dir="rtl" className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-5 sm:px-6">
      <button
        type="button"
        disabled={!previous}
        onClick={() => previous && onNavigate(previous)}
        className="rounded-xl border border-slate-700 bg-slate-900/80 px-5 py-2.5 text-sm text-slate-300 hover:border-cyan-500/50 hover:text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
      >
        السابق
      </button>
      <button
        type="button"
        disabled={!canGoNext(status, current)}
        onClick={() => next && onNavigate(next)}
        className="rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 px-6 py-2.5 text-sm font-bold text-slate-950 shadow-glow-cyan hover:brightness-110 transition-all disabled:cursor-not-allowed disabled:opacity-40"
      >
        التالي
      </button>
    </div>
  );
};
