import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

interface ProcessingErrorCardProps {
  title?: string;
  message: string;
  onRetry: () => void;
  canRetry?: boolean;
}

export const ProcessingErrorCard: React.FC<ProcessingErrorCardProps> = ({
  title = 'توقفت المعالجة مؤقتاً',
  message,
  onRetry,
  canRetry = true,
}) => {
  return (
    <div 
      role="alert"
      className="w-full bg-rose-50/90 border border-rose-200 rounded-2xl p-5 sm:p-6 shadow-sm transition-all animate-in fade-in"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5 sm:mt-0">
            <AlertCircle className="w-5 h-5" />
          </div>

          <div>
            <h4 className="text-sm sm:text-base font-bold text-rose-900">
              {title}
            </h4>
            <p className="text-xs sm:text-sm text-rose-700/95 mt-1 leading-relaxed max-w-xl">
              {message}
            </p>
          </div>
        </div>

        {canRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-rose-700 hover:bg-rose-800 text-white font-medium text-xs sm:text-sm transition-all shadow-sm shrink-0 active:scale-98"
          >
            <RotateCcw className="w-4 h-4" />
            <span>إعادة المحاولة</span>
          </button>
        )}

      </div>
    </div>
  );
};
