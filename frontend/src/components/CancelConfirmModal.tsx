import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface CancelConfirmModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const CancelConfirmModal: React.FC<CancelConfirmModalProps> = ({
  isOpen,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-dialog-title"
    >
      <div 
        className="w-full max-w-md bg-white rounded-2xl shadow-float border border-slate-200 p-6 text-right animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="p-3 rounded-xl bg-amber-50 text-amber-600 border border-amber-200/60">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            aria-label="إغلاق النافذة"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <h3 id="cancel-dialog-title" className="text-lg font-bold text-slate-900 mb-2">
          تأكيد إلغاء المعالجة
        </h3>

        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          هل أنت متأكد من رغبتك في إلغاء عملية الدبلجة الجارية؟ سيتم إيقاف تقدم الذكاء الاصطناعي والعودة إلى شاشة رفع الفيديو.
        </p>

        <div className="flex flex-col-reverse sm:flex-row items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 font-medium text-sm transition-colors"
          >
            متابعة المعالجة
          </button>

          <button
            type="button"
            onClick={onConfirm}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-medium text-sm transition-colors shadow-sm"
          >
            نعم، إلغاء المعالجة
          </button>
        </div>
      </div>
    </div>
  );
};
