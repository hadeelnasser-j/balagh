import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { apiErrorMessage, getJob, ProcessingJob, startTranscription } from '../services/api';

interface BackendProcessingScreenProps {
  projectId: string;
  initialJobId: string | null;
  onOpenReview: () => void;
  onBackHome: () => void;
}

const DONE_STATUSES = new Set(['awaiting_review', 'srt_generated', 'failed']);

export const BackendProcessingScreen: React.FC<BackendProcessingScreenProps> = ({
  projectId,
  initialJobId,
  onOpenReview,
  onBackHome,
}) => {
  const [jobId, setJobId] = useState<string | null>(initialJobId);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!jobId) return undefined;
    const activeJobId = jobId;
    let cancelled = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const current = await getJob(activeJobId);
        if (cancelled) return;
        setJob(current);
        setError('');
        if (current.status === 'audio_extracted' || DONE_STATUSES.has(current.status)) return;
        timer = window.setTimeout(poll, 1500);
      } catch (requestError) {
        if (!cancelled) {
          setError(apiErrorMessage(requestError));
          timer = window.setTimeout(poll, 3000);
        }
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId]);

  const handleStartTranscription = async () => {
    setStarting(true);
    setError('');
    try {
      const started = await startTranscription(projectId);
      setJobId(started.job_id);
      setJob(started);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setStarting(false);
    }
  };

  const audioReady = job?.status === 'audio_extracted';
  const reviewReady = job && (job.status === 'awaiting_review' || job.status === 'srt_generated');
  const failed = job?.status === 'failed';

  return (
    <div className="min-h-[calc(100vh-180px)]">
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6" dir="rtl">
        <div className="mx-auto w-full max-w-3xl">
        <button type="button" onClick={onBackHome} className="mb-6 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-800">
          <ArrowLeft className="h-4 w-4" /> العودة للرئيسية
        </button>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-subtle sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-brand-700">معالجة المشروع</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900">التفريغ والترجمة</h1>
              <p className="mt-2 break-all text-xs text-slate-400" dir="ltr">{projectId}</p>
            </div>
            {job && !DONE_STATUSES.has(job.status) && !audioReady && (
              <Loader2 className="h-6 w-6 animate-spin text-brand-700" />
            )}
          </div>

          <div className="mt-8">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span>{job?.current_step || 'جارٍ تحميل حالة المعالجة...'}</span>
              <span className="font-mono font-bold text-brand-800">{job?.progress ?? 0}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-brand-700 transition-all" style={{ width: `${job?.progress ?? 0}%` }} />
            </div>
          </div>

          {error && <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
          {failed && <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{job.error_message || 'فشلت المعالجة.'}</p>}

          {audioReady && (
            <div className="mt-7 rounded-xl bg-emerald-50 p-4 text-emerald-900">
              <p className="font-semibold">اكتمل رفع الفيديو واستخراج الصوت.</p>
              <button
                type="button"
                disabled={starting}
                onClick={() => void handleStartTranscription()}
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-800 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                ابدأ التفريغ والترجمة
              </button>
            </div>
          )}

          {reviewReady && (
            <button
              type="button"
              onClick={onOpenReview}
              className="mt-7 inline-flex items-center gap-2 rounded-xl bg-brand-800 px-6 py-3 font-bold text-white hover:bg-brand-700"
            >
              فتح صفحة مراجعة الترجمة <ArrowLeft className="h-4 w-4" />
            </button>
          )}
        </section>
        </div>
      </main>
    </div>
  );
};
