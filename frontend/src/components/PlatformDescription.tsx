import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const PlatformDescription: React.FC = () => {
  return (
    <section 
      aria-label="نبذة عن المنصة"
      className="w-full text-center py-5 px-6 rounded-2xl bg-gradient-to-b from-brand-50/50 via-white to-white border border-brand-100/70 shadow-subtle"
    >
      <div className="max-w-2xl mx-auto flex flex-col items-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-100/70 text-brand-800 text-xs font-semibold mb-2.5">
          <ShieldCheck className="w-3.5 h-3.5 text-brand-700" />
          <span>حفظ الأمانة العلمية والدلالية</span>
        </div>

        <p className="text-base sm:text-lg text-slate-800 font-medium leading-relaxed">
          منصة دبلجة واعية تحافظ على المعنى والمصطلحات الإسلامية أثناء الترجمة.
        </p>
      </div>
    </section>
  );
};
