import React from 'react';
import { BookMarked, Check, Edit2, Send, ShieldAlert, Sparkles, Database } from 'lucide-react';
import { TerminologyItem } from '../../types';

interface TerminologyCardProps {
  term: TerminologyItem;
  isApprovalDisabled?: boolean;
  onApprove: (id: string) => void;
  onEdit: (id: string) => void;
  onSendForReview: (id: string) => void;
}

export const TerminologyCard: React.FC<TerminologyCardProps> = ({
  term,
  isApprovalDisabled = false,
  onApprove,
  onEdit,
  onSendForReview,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5 sm:p-6 transition-all">
      {/* Header: Term title & Approved English equivalent */}
      <div className="flex items-start justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-800 flex items-center justify-center shrink-0 border border-brand-200/60">
            <BookMarked className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">المصطلح:</span>
              <h4 className="text-base font-bold text-slate-900">{term.term}</h4>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-slate-400 font-medium">المقابل المعتمد:</span>
              <span className="text-sm font-semibold text-brand-900 font-mono bg-brand-50/70 px-2 py-0.5 rounded border border-brand-200/60">
                {term.approvedEquivalent}
              </span>
            </div>
          </div>
        </div>

        {/* Confidence & Risk Badges */}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
            <Sparkles className="w-3 h-3 text-emerald-600" />
            <span>الثقة: {term.confidencePercent}%</span>
          </span>

          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            <ShieldAlert className="w-3 h-3 text-amber-600" />
            <span>الخطورة: {term.riskLevel}</span>
          </span>
        </div>
      </div>

      {/* Definition & Meta Details */}
      <div className="space-y-2.5 text-xs text-slate-600 mb-5">
        <div className="bg-slate-50/80 p-3 rounded-xl border border-slate-100">
          <span className="font-semibold text-slate-700 block mb-1">التعريف:</span>
          <p className="leading-relaxed text-slate-800 text-xs sm:text-sm">
            {term.definition}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-500">
            <span className="font-semibold text-slate-700">المراجعة:</span>
            <span className="px-2 py-0.5 rounded bg-slate-100 font-medium text-slate-700">
              {term.reviewStatus}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-slate-500">
            <Database className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="font-semibold text-slate-700">المصدر:</span>
            <span className="text-slate-700 font-medium truncate" title={term.source}>
              {term.source}
            </span>
          </div>
        </div>
      </div>

      {/* Actions: تعديل | اعتماد | إرسال للمراجعة */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Edit button */}
          <button
            type="button"
            onClick={() => onEdit(term.id)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium transition-colors"
          >
            <Edit2 className="w-3 h-3 text-slate-500" />
            <span>تعديل</span>
          </button>

          {/* Send for review button */}
          <button
            type="button"
            onClick={() => onSendForReview(term.id)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium transition-colors"
          >
            <Send className="w-3 h-3 text-slate-500" />
            <span>إرسال للمراجعة</span>
          </button>
        </div>

        {/* Approve button */}
        <button
          type="button"
          onClick={() => onApprove(term.id)}
          disabled={isApprovalDisabled || term.status === 'approved'}
          className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${
            term.status === 'approved'
              ? 'bg-emerald-600 text-white cursor-default'
              : isApprovalDisabled
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200 shadow-none'
              : 'bg-brand-800 hover:bg-brand-700 text-white cursor-pointer active:scale-98'
          }`}
          title={isApprovalDisabled ? 'تم تعطيل الاعتماد لحين استعادة المعنى المحمي' : 'اعتماد المصطلح'}
        >
          <Check className="w-3.5 h-3.5" />
          <span>{term.status === 'approved' ? 'تم الاعتماد' : 'اعتماد'}</span>
        </button>
      </div>
    </div>
  );
};
