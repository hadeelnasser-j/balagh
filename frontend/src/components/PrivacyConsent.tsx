import React from 'react';
import { ShieldAlert, Check } from 'lucide-react';

interface PrivacyConsentProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export const PrivacyConsent: React.FC<PrivacyConsentProps> = ({
  checked,
  onChange,
  disabled = false,
}) => {
  return (
    <div className="bg-slate-50/70 rounded-2xl border border-slate-200/80 p-5 transition-all">
      <label className="flex items-start gap-3.5 cursor-pointer select-none">
        <div className="relative flex items-center pt-0.5">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
            className="sr-only peer"
          />
          <div className="w-5 h-5 rounded-md border border-slate-300 bg-white peer-checked:bg-brand-700 peer-checked:border-brand-700 peer-focus:ring-2 peer-focus:ring-brand-500/20 transition-all flex items-center justify-center">
            {checked && <Check className="w-3.5 h-3.5 text-white stroke-[3]" />}
          </div>
        </div>

        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-800 leading-snug">
            أوافق على معالجة الفيديو باستخدام تقنيات الذكاء الاصطناعي.
          </p>
          <div className="flex items-start gap-1.5 mt-1.5 text-xs text-slate-500 leading-relaxed">
            <ShieldAlert className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
            <span>
              نلتزم بحفظ الأمان والخصوصية وصيانة قدسية وضوابط المحتوى الإسلامي. لا تتم مشاركة مقاطعك أو استخدامها لتدريب نماذج خارجية دون إذن صريح.
            </span>
          </div>
        </div>
      </label>
    </div>
  );
};
