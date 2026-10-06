import React from 'react';
import { AlertCircle, RotateCcw, X } from 'lucide-react';
import { UploadErrorInfo } from '../types';

interface ErrorBannerProps {
  error: UploadErrorInfo;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onRetry,
  onDismiss,
}) => {
  return (
    <div
      role="alert"
      className="w-full bg-rose-50/90 border border-rose-200/80 rounded-2xl p-4 transition-all duration-300 shadow-sm animate-in fade-in"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-rose-100/80 text-rose-700 shrink-0 mt-0.5">
            <AlertCircle className="w-5 h-5" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-rose-900">
              {error.title}
            </h3>
            <p className="text-xs md:text-sm text-rose-700/90 mt-1 leading-relaxed">
              {error.message}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {error.canRetry && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-800 bg-rose-100 hover:bg-rose-200 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>إعادة المحاولة</span>
            </button>
          )}

          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              aria-label="إغلاق التنبيه"
              className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
