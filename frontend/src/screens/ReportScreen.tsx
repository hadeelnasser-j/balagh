import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, ArrowLeft, BookOpen, CheckCircle2, Download, Loader2, RefreshCw, ShieldCheck, Volume2, XCircle,
} from 'lucide-react';
import {
  AI_AUDIO_NOTICE,
  apiErrorMessage,
  downloadDubbedVideo,
  dubbedVideoUrl,
  getIntegrityReport,
  IntegrityReport,
  ReportSegment,
} from '../services/api';
import { CenteredVideoPlayer } from '../components/CenteredVideoPlayer';
import { formatDuration } from '../utils/formatters';

interface ReportScreenProps {
  projectId: string;
  onBack: () => void;
  onFinish?: () => void;
}

const DUBBING_MODE_LABELS: Record<string, string> = {
  faithful: 'الأمينة',
  timed: 'الزمنية',
  simplified: 'المبسطة',
};

const UNCERTAIN_REASON_LABELS: Record<string, string> = {
  possible_quran_below_threshold: 'يشبه نصًا قرآنيًا دون بلوغ حد المطابقة؛ محمي من الدبلجة.',
  quran_quote_mixed_with_speech: 'اقتباس قرآني ضمن كلام عام.',
  hadith_quote_mixed_with_speech: 'اقتباس حديث ضمن كلام عام.',
  quran_and_hadith_match: 'تعارض بين مطابقة قرآنية وحديثية.',
  quotation_without_source: 'اقتباس ديني دون مصدر موثق.',
  low_confidence_candidate: 'مطابقة ضعيفة تحتاج مراجعة.',
};

const BLOCKING_LABELS: Record<string, string> = {
  uncertain_needs_review: 'مقطع غير محسوم',
  translation_not_reviewed: 'ترجمة غير معتمدة',
  translation_not_verified: 'ترجمة غير موثقة',
  translation_missing: 'لا توجد ترجمة نهائية',
  audio_missing: 'لم يُولّد الصوت',
  audio_not_approved: 'صوت غير معتمد',
  timing_not_valid: 'توقيت غير صالح',
  timing_overflow: 'تنبيه توقيت (لا يمنع الإخراج)',
  no_segments: 'لا توجد مقاطع',
};

function translationOriginLabel(origin: string | null): string {
  switch (origin) {
    case 'quranenc_local_official':
      return 'QuranEnc (معتمدة)';
    case 'hadeethenc_official':
      return 'HadeethEnc (منشورة)';
    case 'openai_constrained_draft':
    case 'gemini_constrained_draft':
      return 'مسودة آلية مقيدة بالمصدر';
    case 'human_reviewer':
      return 'ترجمة المراجع';
    default:
      return origin ? 'ترجمة آلية' : '—';
  }
}

function timeRange(item: ReportSegment): string {
  if (item.start_time == null || item.end_time == null) return '';
  const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  return `${fmt(item.start_time)} – ${fmt(item.end_time)}`;
}

function blockingLabel(reason: string): string {
  const match = reason.match(/^segment_(\d+):(.+)$/);
  if (!match) return BLOCKING_LABELS[reason] ?? reason;
  return `المقطع ${Number.parseInt(match[1], 10) + 1}: ${BLOCKING_LABELS[match[2]] ?? match[2]}`;
}

export const ReportScreen: React.FC<ReportScreenProps> = ({ projectId, onBack, onFinish }) => {
  const [report, setReport] = useState<IntegrityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [loadedAt, setLoadedAt] = useState(() => Date.now());  // cache-buster for the player

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setReport(await getIntegrityReport(projectId));
      setLoadedAt(Date.now());
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDownload = async () => {
    setDownloading(true);
    setError('');
    try {
      const filename = await downloadDubbedVideo(projectId);
      setNotice(`بدأ تنزيل الملف: ${filename}`);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setDownloading(false);
    }
  };

  const counts = report?.content_counts;
  const quran = report?.quran_summary;
  const hadith = report?.hadith_summary;
  const uncertain = report?.uncertain_segments ?? [];
  const dubbing = report?.dubbing;
  const validation = report?.validation;
  const blocking = [...(dubbing?.generation_blocking_reasons ?? []), ...(dubbing?.render_blocking_reasons ?? [])];

  return (
    <div className="min-h-[calc(100vh-180px)]">
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6" dir="rtl">
        <button type="button" onClick={onBack} className="mb-3 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-800">
          <ArrowLeft className="h-4 w-4" /> العودة للدبلجة
        </button>

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">تقرير المشروع</h1>
            {report?.project?.title && <p className="mt-1 text-sm text-slate-600">{report.project.title}</p>}
            <p className="mt-1 break-all text-xs text-slate-400" dir="ltr">{projectId}</p>
          </div>
          <div className="flex items-center gap-2">
            {validation && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold ${
                  validation.passed
                    ? 'border border-emerald-200 bg-emerald-50 text-emerald-800'
                    : 'border border-amber-200 bg-amber-50 text-amber-800'
                }`}
              >
                {validation.passed ? <ShieldCheck className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                {validation.passed ? 'اجتاز التحقق النهائي' : 'التحقق النهائي غير مكتمل'}
              </span>
            )}
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-brand-300 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> تحديث
            </button>
          </div>
        </div>

        {error && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
        {notice && <p role="status" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}

        {loading && !report ? (
          <div className="mt-4 flex justify-center rounded-2xl bg-white p-12"><Loader2 className="h-7 w-7 animate-spin text-brand-700" /></div>
        ) : report && (
          <div className="mt-4 space-y-4">
            {/* Project statistics */}
            <Card title="إحصاءات المشروع">
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <Stat label="إجمالي المقاطع" value={report.total_segments} />
                <Stat label="آيات قرآنية" value={counts?.quran ?? quran?.count ?? 0} />
                <Stat label="أحاديث" value={counts?.hadith ?? hadith?.count ?? 0} />
                <Stat label="كلام عام" value={counts?.general ?? 0} />
                <Stat label="غير محسوم" value={counts?.uncertain ?? uncertain.length} tone={uncertain.length ? 'warn' : undefined} />
                <Stat label="صوت مُولّد" value={report.synthesized_segments} />
                <Stat label="صوت أصلي محفوظ" value={report.original_audio_segments} />
                <Stat
                  label="مدة الفيديو"
                  value={report.project?.duration_seconds ? formatDuration(report.project.duration_seconds) : '—'}
                />
              </div>
              {report.project?.dubbing_mode && (
                <p className="mt-3 text-xs text-slate-500">
                  نمط الدبلجة: {DUBBING_MODE_LABELS[report.project.dubbing_mode] ?? report.project.dubbing_mode}
                </p>
              )}
            </Card>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Quran detection summary */}
              <Card title="ملخص الآيات القرآنية" icon={<BookOpen className="h-4 w-4 text-emerald-700" />}>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <Stat label="المكتشفة" value={quran?.count ?? 0} />
                  <Stat label="الموثقة" value={quran?.verified ?? 0} />
                  <Stat label="بصوتها الأصلي" value={quran?.original_audio_preserved ?? 0} />
                </div>
                <p className="mt-3 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">
                  تُترجم الآيات من QuranEnc فقط، ولا تُرسل إلى توليد الصوت مطلقًا.
                  {typeof report.quran_sent_to_tts === 'number' && ` (مقاطع قرآنية أُرسلت للصوت: ${report.quran_sent_to_tts})`}
                </p>
                <SegmentList items={quran?.items ?? []} empty="لا توجد آيات قرآنية في هذا الفيديو." />
              </Card>

              {/* Hadith detection summary */}
              <Card title="ملخص الأحاديث" icon={<BookOpen className="h-4 w-4 text-accent-goldDark" />}>
                <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  <Stat label="المكتشفة" value={hadith?.count ?? 0} />
                  <Stat label="الموثقة" value={hadith?.verified ?? 0} />
                  <Stat label="ترجمة منشورة" value={hadith?.official_translations ?? 0} />
                  <Stat label="مسودة آلية" value={hadith?.ai_drafts ?? 0} />
                </div>
                <SegmentList items={hadith?.items ?? []} empty="لا توجد أحاديث في هذا الفيديو." showGrade />
              </Card>
            </div>

            {/* Uncertain segments */}
            <Card title="المقاطع غير المحسومة" icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}>
              {uncertain.length === 0 ? (
                <p className="text-sm text-slate-600">لا توجد مقاطع غير محسومة.</p>
              ) : (
                <ul className="space-y-2">
                  {uncertain.map((item) => (
                    <li key={item.segment_id} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-amber-900">
                        <span className="font-bold">المقطع {item.segment_index + 1}</span>
                        <span dir="ltr">{timeRange(item)}</span>
                      </div>
                      <p className="mt-1 text-slate-800">{item.original_text}</p>
                      <p className="mt-1 text-xs text-amber-800">
                        {UNCERTAIN_REASON_LABELS[item.reason ?? ''] ?? 'يحتاج مراجعة بشرية.'}
                        {item.reference ? ` المرجع المرشح: ${item.reference}` : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            {/* Dubbing readiness */}
            <Card title="جاهزية الدبلجة" icon={<Volume2 className="h-4 w-4 text-brand-700" />}>
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <Stat label="يحتاج TTS" value={dubbing?.tts_required_segments ?? 0} />
                <Stat label="الصوت المُولّد" value={`${dubbing?.generated_tts_segments ?? 0}/${dubbing?.tts_required_segments ?? 0}`} />
                <Stat label="الصوت المعتمد" value={`${dubbing?.approved_tts_segments ?? 0}/${dubbing?.tts_required_segments ?? 0}`} />
                <Stat
                  label="جاهز للإخراج"
                  value={dubbing?.render_ready ? 'نعم' : 'لا'}
                  tone={dubbing?.render_ready ? 'ok' : 'warn'}
                />
              </div>
              {blocking.length > 0 && (
                <ul className="mt-3 list-disc space-y-0.5 pr-5 text-xs text-amber-800">
                  {Array.from(new Set(blocking.map(blockingLabel))).map((reason) => <li key={reason}>{reason}</li>)}
                </ul>
              )}
            </Card>

            {/* Final validation */}
            <Card title="نتائج التحقق النهائي" icon={<ShieldCheck className="h-4 w-4 text-brand-700" />}>
              {validation ? (
                <ul className="divide-y divide-slate-100">
                  {validation.checks.map((check) => (
                    <li key={check.key} className="flex items-center justify-between gap-3 py-2 text-sm">
                      <span className="flex items-center gap-2 text-slate-800">
                        {check.passed
                          ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                          : check.severity === 'warning'
                            ? <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                            : <XCircle className="h-4 w-4 shrink-0 text-rose-600" />}
                        {check.label}
                      </span>
                      {check.detail && <span className="text-xs text-slate-500">{check.detail}</span>}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-600">نتائج التحقق غير متاحة من الخادم.</p>
              )}
            </Card>

            {/* Final video */}
            <Card title="الفيديو النهائي">
              {report.dubbed_video_available ? (
                <>
                  <p className="mb-3 text-xs text-amber-700">{report.ai_generated_audio_notice || AI_AUDIO_NOTICE}</p>
                  <CenteredVideoPlayer src={`${dubbedVideoUrl(projectId)}?v=${loadedAt}`} title="الفيديو المدبلج" />
                  <div className="mt-4 flex justify-center">
                    <button
                      type="button"
                      onClick={() => void handleDownload()}
                      disabled={downloading}
                      className="inline-flex items-center gap-2 rounded-xl bg-brand-800 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-60"
                    >
                      {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                      {downloading ? 'جارٍ التنزيل...' : 'تنزيل الفيديو المدبلج'}
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-600">لم يُنشأ الفيديو المدبلج بعد.</p>
              )}
            </Card>

            {onFinish && (
              <div className="flex justify-center pt-2">
                <button
                  type="button"
                  onClick={onFinish}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 px-7 py-3 text-sm font-bold text-slate-950 shadow-glow-cyan transition-all hover:brightness-110"
                >
                  <CheckCircle2 className="h-4 w-4" /> إنهاء المشروع
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

const Card: React.FC<{ title: string; icon?: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-subtle">
    <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">{icon}{title}</h2>
    {children}
  </section>
);

const Stat: React.FC<{ label: string; value: string | number; tone?: 'ok' | 'warn' }> = ({ label, value, tone }) => (
  <div className={`rounded-xl p-3 ${tone === 'warn' ? 'bg-amber-50' : tone === 'ok' ? 'bg-emerald-50' : 'bg-slate-50'}`}>
    <p className="text-xs text-slate-500">{label}</p>
    <p className="mt-1 text-lg font-bold text-slate-900">{value}</p>
  </div>
);

const SegmentList: React.FC<{ items: ReportSegment[]; empty: string; showGrade?: boolean }> = ({ items, empty, showGrade }) => (
  items.length === 0 ? (
    <p className="mt-3 text-sm text-slate-600">{empty}</p>
  ) : (
    <ul className="mt-3 space-y-2">
      {items.map((item) => (
        <li key={item.segment_id} className="rounded-xl border border-slate-200 p-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <span className="font-bold text-slate-800">{item.reference ?? '—'}</span>
            <span dir="ltr">
              {timeRange(item)}
              {typeof item.score === 'number' ? ` · ${item.score.toFixed(2)}` : ''}
            </span>
          </div>
          <p className="mt-1 text-slate-700">{item.original_text}</p>
          <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-slate-500">
            <span>الترجمة: {translationOriginLabel(item.translation_origin)}</span>
            {showGrade && item.hadith_grade && <span>الحكم: {item.hadith_grade}</span>}
            {item.source_url && (
              <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">
                المصدر
              </a>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
);

export default ReportScreen;
