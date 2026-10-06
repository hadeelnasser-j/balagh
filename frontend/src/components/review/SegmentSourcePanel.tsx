import React from 'react';
import {
  RecoveredSourceItem,
  ReviewSegment,
} from '../../services/api';

export const CONTENT_TYPE_LABELS: Record<string, string> = {
  general: 'عام',
  quran: 'آية قرآنية',
  hadith: 'حديث',
  uncertain: 'غير محسوم',
  unknown: 'غير محدد',
};

export const VERIFICATION_LABELS: Record<string, string> = {
  pending: 'لم يُتحقق منه',
  candidate: 'مرشح بانتظار الاعتماد',
  verified: 'موثّق',
  not_found: 'لم يوجد في المصادر المعتمدة',
  conflict: 'تعارض بين المصادر',
  rejected: 'مرفوض',
};

interface Props {
  segment: ReviewSegment;
  recoveredSources?: RecoveredSourceItem[];
}

const STATUS_LABELS: Record<RecoveredSourceItem['status'], string> = {
  recovered: 'مسترجع',
  candidate: 'مرشح',
  approved: 'معتمد',
  rejected: 'مرفوض',
};

const displaySource = (source: string): string => {
  if (source.includes('Dorar') || source.includes('الدرر')) return 'الدرر السنية';
  return source;
};

const extractVerdict = (section?: string | null): string | null => {
  if (!section) return null;
  const parts = section.split('|').map((part) => part.trim());
  const verdict = parts.find((part) => part.startsWith('الحكم:'));
  if (!verdict) return null;
  return verdict.replace('الحكم:', '').trim() || null;
};

export const SegmentSourcePanel: React.FC<Props> = ({ segment, recoveredSources = [] }) => {
  const religious = segment.content_type && segment.content_type !== 'general';

  if (!religious) return null;

  const status = segment.source_verification_status ?? 'pending';
  const translationSource = segment.translation_source ?? segment.verification_source ?? '—';
  const reference = segment.reference ?? '—';
  const grade = segment.hadith_grade ?? null;
  return (
    <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-4 text-sm" aria-label="التحقق من المصدر">
      <div className="flex flex-wrap items-center gap-2 font-semibold">
        <span>نوع المحتوى: {CONTENT_TYPE_LABELS[segment.content_type ?? ''] ?? segment.content_type}</span>
        <span>— التحقق: {VERIFICATION_LABELS[status] ?? status}</span>
        {typeof segment.source_match_score === 'number' && <span>— الدرجة {segment.source_match_score.toFixed(2)}</span>}
        <span>— مصدر الترجمة: {translationSource}</span>
        <span>— المرجع: {reference}</span>
        {grade ? <span>— الحكم: {grade}</span> : null}
      </div>
      <p className="mt-2 text-xs text-slate-600">حالة المراجعة: {segment.review_status === 'approved' ? 'معتمد' : segment.review_status === 'rejected' ? 'مرفوض' : 'بانتظار المراجعة'}</p>

      {recoveredSources.length > 0 && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <h4 className="font-bold text-slate-800">المصدر والتحقق المرجعي</h4>
          <ul className="mt-2 space-y-3">
            {recoveredSources.map((item) => {
              const confidencePercent = `${(item.confidence * 100).toFixed(2)}%`;
              const verdict = extractVerdict(item.section);
              return (
                <li key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-sm text-slate-800">المصدر: {displaySource(item.source)}</p>
                  <p className="mt-1 text-sm text-slate-700">المرجع: {item.reference || '—'}</p>
                  {verdict && <p className="mt-1 text-sm text-slate-700">الحكم: {verdict}</p>}
                  {item.section && <p className="mt-1 text-xs text-slate-500">تفاصيل: {item.section}</p>}
                  <p className="mt-1 text-sm text-slate-700">درجة المطابقة: {confidencePercent}</p>
                  <p className="mt-1 text-sm text-slate-700">الحالة: {STATUS_LABELS[item.status] ?? item.status}</p>
                  {displaySource(item.source) === 'الدرر السنية' && (
                    <p className="mt-2 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">
                      الترجمة: مسودة آلية بواسطة OpenAI وتحتاج مراجعة بشرية
                    </p>
                  )}
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-600">عرض النص الكامل</summary>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{item.full_text}</p>
                  </details>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
};
