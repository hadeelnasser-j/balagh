import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Download, FileText, Loader2, Volume2 } from 'lucide-react';
import {
  AI_AUDIO_NOTICE,
  ApiError,
  approveAudioSegment,
  apiErrorMessage,
  downloadDubbedVideo,
  dubbedVideoUrl,
  generateDubbing,
  getDubbingReadiness,
  getJob,
  getPipelineStatus,
  getProject,
  getSegments,
  renderDubbedVideo,
  ReviewSegment,
  segmentAudioUrl,
} from '../services/api';
import { CenteredVideoPlayer } from '../components/CenteredVideoPlayer';

interface DubbingScreenProps {
  projectId: string;
  onBack: () => void;
  onOpenReport?: () => void | Promise<void>;
}

function finalTranslation(segment: ReviewSegment): string {
  return (segment.edited_translation ?? segment.translated_text ?? '').trim();
}

// The backend decides how each segment sounds (audio_mode): "tts", "original" (Quran / possible Quran)
// or "blocked" (uncertain, not yet approved). Older backends without audio_mode fall back to content type.
function isTtsSegment(segment: ReviewSegment): boolean {
  if (segment.audio_mode) return segment.audio_mode === 'tts';
  const contentType = (segment.content_type || '').toLowerCase();
  return contentType !== 'quran' && contentType !== 'uncertain';
}

function isEligibleForDubbing(segment: ReviewSegment): boolean {
  return segment.review_status === 'approved'
    && segment.translation_verified === true
    && segment.ready_for_dubbing === true
    && segment.translation_status === 'translated'
    && segment.source_review_status !== 'rejected'
    && isTtsSegment(segment)
    && finalTranslation(segment).length > 0;
}

async function waitForJob(jobId: string, doneStatuses: string[] = ['completed']): Promise<string | null> {
  for (;;) {
    await new Promise((resolve) => window.setTimeout(resolve, 2000));
    const job = await getJob(jobId);
    if (job.status === 'failed') throw new Error(job.error_message || 'فشلت معالجة الدبلجة.');
    if (doneStatuses.includes(job.status)) return job.current_step;
  }
}

export const DubbingScreen: React.FC<DubbingScreenProps> = ({ projectId, onBack, onOpenReport }) => {
  const [segments, setSegments] = useState<ReviewSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyAction, setBusyAction] = useState<'generate' | 'approve' | 'render' | null>(null);
  const [downloading, setDownloading] = useState(false);
  // True only when the final video file actually exists on the server.
  const [dubbedReady, setDubbedReady] = useState(false);
  // Changes after every render so the player never keeps showing a cached failed/old response.
  const [videoVersion, setVideoVersion] = useState<number | null>(null);
  const [renderReady, setRenderReady] = useState(false);
  const [generationReasons, setGenerationReasons] = useState<string[]>([]);
  const [renderReasons, setRenderReasons] = useState<string[]>([]);
  const [infoReasons, setInfoReasons] = useState<string[]>([]);
  const [readinessStats, setReadinessStats] = useState({
    totalSegments: 0,
    passthroughSegments: 0,
    ttsRequiredSegments: 0,
    generatedTtsSegments: 0,
    approvedTtsSegments: 0,
  });
  const [autoGenerationFailed, setAutoGenerationFailed] = useState(false);
  const [workflowStep, setWorkflowStep] = useState<'dubbing' | 'render'>('dubbing');
  const [activeGenerationStep, setActiveGenerationStep] = useState<number | null>(null);
  const [failedGenerationStep, setFailedGenerationStep] = useState<number | null>(null);
  const [activeAudioJobStatus, setActiveAudioJobStatus] = useState<string | null>(null);
  const [audioJobTimedOut, setAudioJobTimedOut] = useState(false);
  const autoGenerationKeyRef = useRef<string | null>(null);
  const activeAudioJobRef = useRef<string | null>(null);
  const activeAudioJobStartedAtRef = useRef<number | null>(null);
  const pollingTimerRef = useRef<number | null>(null);
  const busyActionRef = useRef<'generate' | 'approve' | 'render' | null>(null);
  const autoGenerationFailedRef = useRef(false);

  useEffect(() => {
    busyActionRef.current = busyAction;
  }, [busyAction]);
  useEffect(() => {
    autoGenerationFailedRef.current = autoGenerationFailed;
  }, [autoGenerationFailed]);

  const reasonLabel = (reason: string): string => {
    const match = reason.match(/^segment_(\d+):(.+)$/);
    const segmentLabel = match ? `المقطع ${Number.parseInt(match[1], 10) + 1}` : '';
    const code = match ? match[2] : reason;
    const message = (() => {
      switch (code) {
        case 'quran_original_audio':
          return 'قرآن، سيُستخدم الصوت الأصلي.';
        case 'reviewed_original_audio':
          return 'اعتمده المراجع؛ يُحفظ صوته الأصلي لاحتمال احتوائه على نص قرآني.';
        case 'uncertain_needs_review':
          return 'غير محسوم ويحتاج مراجعة قبل الدبلجة.';
        case 'translation_not_translated':
          return 'الترجمة غير مكتملة بعد.';
        case 'translation_not_reviewed':
          return 'الترجمة غير معتمدة.';
        case 'translation_not_verified':
          return 'الترجمة غير موثقة.';
        case 'not_ready_for_dubbing':
          return 'غير جاهز للدبلجة.';
        case 'translation_missing':
          return 'لا توجد ترجمة نهائية.';
        case 'contains_arabic_text':
          return 'الترجمة الإنجليزية تحتوي نصًا عربيًا.';
        case 'source_rejected':
          return 'المصدر المرجعي مرفوض.';
        case 'verification_source_missing':
          return 'لا يوجد مصدر تحقق صالح.';
        case 'audio_missing':
          return 'لم يُولّد الصوت بعد.';
        case 'audio_duration_missing':
          return 'مدة الصوت غير متوفرة بعد التوليد.';
        case 'timing_not_valid':
          return 'توقيت الصوت غير صالح للإخراج النهائي.';
        case 'timing_overflow':
          return 'تنبيه: الصوت أطول من مدة المقطع؛ سيُسرَّع قليلًا ويُستخدم كما اعتُمد دون منع الإخراج.';
        case 'audio_not_approved':
          return 'الصوت غير معتمد بعد.';
        case 'no_segments':
          return 'لا توجد مقاطع في المشروع.';
        default:
          return code;
      }
    })();
    return segmentLabel ? `${segmentLabel}: ${message}` : message;
  };

  const normalizeReasons = (reasons: string[]): string[] => (
    Array.from(new Set(reasons.map(reasonLabel)))
  );

  const needsTts = (segment: ReviewSegment): boolean => isTtsSegment(segment);

  const loadSnapshot = useCallback(async () => {
    const [segmentPage, readiness] = await Promise.all([
      getSegments(projectId, 1, 100),
      getDubbingReadiness(projectId),
    ]);
    setSegments(segmentPage.items);
    const totalSegments = readiness.total_segments ?? segmentPage.items.length;
    const passthroughSegments = readiness.passthrough_segments
      ?? segmentPage.items.filter((segment) => (segment.audio_mode ? segment.audio_mode === 'original' : segment.content_type === 'quran')).length;
    const ttsRequiredSegments = readiness.tts_required_segments
      ?? segmentPage.items.filter((segment) => needsTts(segment)).length;
    const generatedTtsSegments = readiness.generated_tts_segments
      ?? segmentPage.items.filter((segment) => needsTts(segment) && Boolean(segment.dubbed_audio_path) && Boolean(segment.audio_duration)).length;
    const approvedTtsSegments = readiness.approved_tts_segments
      ?? segmentPage.items.filter((segment) => needsTts(segment) && segment.audio_review_status === 'approved').length;
    setReadinessStats({
      totalSegments,
      passthroughSegments,
      ttsRequiredSegments,
      generatedTtsSegments,
      approvedTtsSegments,
    });
    const generationBlocking = readiness.generation_blocking_reasons ?? readiness.reasons ?? [];
    const renderBlocking = readiness.render_blocking_reasons ?? [];
    const infos = readiness.info_reasons ?? [];
    setRenderReady(Boolean(readiness.render_ready ?? false));
    setGenerationReasons(normalizeReasons(generationBlocking));
    setRenderReasons(normalizeReasons(renderBlocking));
    setInfoReasons(normalizeReasons(infos));
    // Previously this used render_ready ("can render"), which mounted the player before any video
    // existed; the failed request then stuck and the new video never appeared after rendering.
    setDubbedReady(Boolean(readiness.dubbed_video_available ?? false));
    setVideoVersion(readiness.dubbed_video_version ?? null);
    return { segmentPage, readiness };
  }, [projectId]);

  const clearPolling = useCallback(() => {
    if (pollingTimerRef.current !== null) {
      window.clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    activeAudioJobRef.current = null;
    activeAudioJobStartedAtRef.current = null;
    setActiveAudioJobStatus(null);
  }, []);

  const startJobPolling = useCallback((jobId: string) => {
    clearPolling();
    activeAudioJobRef.current = jobId;
    activeAudioJobStartedAtRef.current = Date.now();
    setActiveAudioJobStatus('generating_audio');
    setAudioJobTimedOut(false);
    pollingTimerRef.current = window.setInterval(async () => {
      try {
        const startedAt = activeAudioJobStartedAtRef.current;
        if (startedAt && Date.now() - startedAt >= 120_000) {
          clearPolling();
          setBusyAction(null);
          setActiveGenerationStep(null);
          setAudioJobTimedOut(true);
          setNotice('');
          setError('استغرق توليد الصوت وقتًا أطول من المتوقع');
          return;
        }
        const job = await getJob(jobId);
        setActiveAudioJobStatus(job.status);
        if (job.status === 'completed' || job.status === 'failed') {
          clearPolling();
          setBusyAction(null);
          setActiveGenerationStep(null);
          if (job.status === 'failed') {
            setAutoGenerationFailed(true);
            setError(job.error_message || 'تعذر توليد الصوت.');
            setNotice('');
            return;
          }
          await loadSnapshot();
          setNotice('اكتمل توليد الصوت للمقاطع الجاهزة.');
        }
      } catch (requestError) {
        clearPolling();
        setBusyAction(null);
        setActiveGenerationStep(null);
        setAutoGenerationFailed(true);
        setError(apiErrorMessage(requestError));
        setNotice('');
      }
    }, 3000);
  }, [clearPolling, loadSnapshot]);

  const maybeAttachActiveJob = useCallback(async (): Promise<boolean> => {
    await getPipelineStatus(projectId);
    const project = await getProject(projectId) as unknown as { latest_job?: { job_id?: string; status?: string } };
    const activeJobId = String(project.latest_job?.job_id || '').trim();
    const activeStatus = String(project.latest_job?.status || '').trim().toLowerCase();
    if (!activeJobId) return false;
    const terminalStatuses = new Set([
      'failed',
      'completed',
      'waiting_audio_review',
      'render_pending',
      'rendering',
      'awaiting_review',
      'srt_generated',
    ]);
    if (terminalStatuses.has(activeStatus)) return false;
    setBusyAction('generate');
    setActiveGenerationStep(1);
    setAudioJobTimedOut(false);
    startJobPolling(activeJobId);
    return true;
  }, [projectId, startJobPolling]);

  const startAutoGeneration = useCallback(async () => {
    if (autoGenerationKeyRef.current === projectId) return;
    if (activeAudioJobRef.current) return;
    if (busyActionRef.current !== null) return;
    if (autoGenerationFailedRef.current) return;
    try {
      const attachedToRunningJob = await maybeAttachActiveJob();
      if (attachedToRunningJob) {
        setLoading(false);
        return;
      }
      const { segmentPage, readiness } = await loadSnapshot();
      const segmentsReadyForTts = segmentPage.items.filter((segment) => {
        return isTtsSegment(segment)
          && segment.ready_for_dubbing === true
          && segment.review_status === 'approved'
          && segment.translation_status === 'translated'
          && segment.translation_verified === true
          && !segment.dubbed_audio_path;
      });
      if (!segmentsReadyForTts.length) return;
      if (!(readiness.generation_ready ?? readiness.ready ?? false)) return;
      if ((readiness.generation_blocking_reasons ?? readiness.reasons ?? []).length > 0) return;

      autoGenerationKeyRef.current = projectId;
      setBusyAction('generate');
      setActiveGenerationStep(1);
      setFailedGenerationStep(null);
      setAudioJobTimedOut(false);
      setError('');
      setNotice('جارٍ توليد الصوت تلقائيًا للمقاطع الجاهزة...');
      try {
        const started = await generateDubbing(projectId);
        startJobPolling(started.job_id);
      } catch (requestError) {
        if (requestError instanceof ApiError && requestError.status === 409) {
          const attachedAfterConflict = await maybeAttachActiveJob();
          if (attachedAfterConflict) return;
        }
        throw requestError;
      }
    } catch (requestError) {
      setBusyAction(null);
      setActiveGenerationStep(null);
      setAutoGenerationFailed(true);
      setError(apiErrorMessage(requestError));
      setNotice('');
    } finally {
      setLoading(false);
    }
  }, [loadSnapshot, maybeAttachActiveJob, projectId, startJobPolling]);

  useEffect(() => {
    setLoading(true);
    setError('');
    setNotice('');
    setAutoGenerationFailed(false);
    setActiveGenerationStep(null);
    setFailedGenerationStep(null);
    setAudioJobTimedOut(false);
    setActiveAudioJobStatus(null);
    autoGenerationKeyRef.current = null;
    clearPolling();
    void startAutoGeneration();
    return () => {
      clearPolling();
    };
  }, [projectId, startAutoGeneration, clearPolling]);

  const eligibleSegments = useMemo(
    () => segments.filter(isEligibleForDubbing),
    [segments],
  );
  const totalSegments = readinessStats.totalSegments || segments.length;
  const passthroughSegments = readinessStats.passthroughSegments;
  const ttsRequiredSegments = readinessStats.ttsRequiredSegments;
  const generatedCount = readinessStats.generatedTtsSegments;
  const approvedCount = readinessStats.approvedTtsSegments;
  const quranOnlyProject = totalSegments > 0 && ttsRequiredSegments === 0;
  const allApproved = ttsRequiredSegments === 0 || approvedCount === ttsRequiredSegments;
  const canRender = renderReady && renderReasons.length === 0 && allApproved;
  const isGeneratingAudio = Boolean(
    activeAudioJobRef.current
    && activeAudioJobStatus
    && !['completed', 'failed', 'waiting_audio_review'].includes(activeAudioJobStatus),
  );
  const shouldShowRenderSection = ttsRequiredSegments > 0 && generatedCount === ttsRequiredSegments && allApproved;

  useEffect(() => {
    if (shouldShowRenderSection) {
      setWorkflowStep('render');
    } else {
      setWorkflowStep('dubbing');
    }
  }, [shouldShowRenderSection]);

  const handleApproveSegment = async (segmentId: string) => {
    setBusyAction('approve');
    setError('');
    try {
      await approveAudioSegment(projectId, segmentId);
      await loadSnapshot();
      setNotice('تم اعتماد الصوت.');
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const handleRender = async () => {
    setBusyAction('render');
    setError('');
    try {
      const started = await renderDubbedVideo(projectId);
      const finalStep = await waitForJob(started.job_id, ['completed']);
      const { readiness } = await loadSnapshot();
      if (!readiness.dubbed_video_available) {
        throw new Error('اكتملت المعالجة لكن ملف الفيديو المدبلج غير موجود على الخادم.');
      }
      setVideoVersion(readiness.dubbed_video_version ?? Date.now());
      setDubbedReady(true);
      setNotice(finalStep || 'اكتمل إنشاء الفيديو المدبلج.');
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setBusyAction(null);
    }
  };

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

  return (
    <div className="min-h-[calc(100vh-180px)]">
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6" dir="rtl">
        <button type="button" onClick={onBack} className="mb-3 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-800">
          <ArrowLeft className="h-4 w-4" /> العودة للمراجعة
        </button>
        <h1 className="text-2xl font-bold text-slate-900">الدبلجة</h1>
        <p className="mt-1 break-all text-xs text-slate-400" dir="ltr">{projectId}</p>

        {error && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
        {notice && <p role="status" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}

        <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-subtle">
          <p className="mb-4 text-xs text-amber-700">{AI_AUDIO_NOTICE}</p>
          <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <Stat label="إجمالي المقاطع" value={`${totalSegments}`} />
            <Stat label="قرآن بالصوت الأصلي" value={`${passthroughSegments}`} />
            <Stat label="يحتاج TTS" value={`${ttsRequiredSegments}`} />
            <Stat label="مقاطع جاهزة للدبلجة" value={`${eligibleSegments.length}/${totalSegments}`} />
            <Stat label="الصوت المُولّد" value={`${generatedCount}/${ttsRequiredSegments}`} />
            <Stat label="الصوت المعتمد" value={`${approvedCount}/${ttsRequiredSegments}`} />
          </div>
          {quranOnlyProject && (
            <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
              لا يحتاج هذا المشروع إلى صوت مولد، لأن المحتوى قرآن وسيُحفظ صوته الأصلي.
            </div>
          )}
          {infoReasons.length > 0 && (
            <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
              <p className="font-semibold">معلومات المقاطع:</p>
              <ul className="mt-1 list-disc pr-5">
                {infoReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
          {generationReasons.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">أسباب منع توليد الصوت:</p>
              <ul className="mt-1 list-disc pr-5">
                {generationReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
          {renderReasons.length > 0 && !isGeneratingAudio && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">أسباب منع إنشاء الفيديو النهائي:</p>
              <ul className="mt-1 list-disc pr-5">
                {renderReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {autoGenerationFailed && (
              <button
                type="button"
                onClick={() => {
                  setAutoGenerationFailed(false);
                  setFailedGenerationStep(null);
                  setAudioJobTimedOut(false);
                  autoGenerationKeyRef.current = null;
                  void startAutoGeneration();
                }}
                disabled={busyAction !== null}
                className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-800 disabled:opacity-50"
              >
                إعادة المحاولة
              </button>
            )}
            {audioJobTimedOut && (
              <button
                type="button"
                onClick={() => { void maybeAttachActiveJob(); }}
                disabled={busyAction !== null}
                className="rounded-xl border border-brand-300 bg-brand-50 px-4 py-2.5 text-sm font-semibold text-brand-800 disabled:opacity-50"
              >
                التحقق من الحالة
              </button>
            )}
          </div>
        </section>

        {workflowStep === 'dubbing' && (
        <section className="mt-4 space-y-3">
          {isGeneratingAudio && (
            <div className="rounded-2xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900">
              <div className="flex items-center gap-2 font-semibold">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>جارٍ توليد الصوت...</span>
              </div>
              <p className="mt-2 text-sm font-semibold">
                {ttsRequiredSegments > 1
                  ? `جارٍ توليد الصوت: المقطع ${activeGenerationStep ?? 1} من ${ttsRequiredSegments}`
                  : `جارٍ توليد الصوت للمقطع ${activeGenerationStep ?? 1}...`}
              </p>
              <p className="mt-1 text-xs text-brand-800">
                يرجى الانتظار، سيتم تحديث الصفحة تلقائيًا عند اكتمال التوليد.
              </p>
            </div>
          )}

          {autoGenerationFailed && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
              <p className="font-semibold">
                {`تعذر توليد الصوت للمقطع ${failedGenerationStep ?? Math.min(generatedCount + 1, Math.max(1, ttsRequiredSegments))}`}
              </p>
              <p className="mt-1 text-xs text-rose-800">
                {error || 'حدث خطأ غير متوقع أثناء توليد الصوت.'}
              </p>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center rounded-2xl bg-white p-12"><Loader2 className="h-7 w-7 animate-spin text-brand-700" /></div>
          ) : eligibleSegments.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-700">
              لا توجد مقاطع جاهزة للدبلجة بعد.
            </div>
          ) : eligibleSegments.map((segment) => (
            <article key={segment.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">المقطع {segment.segment_index + 1}</h3>
                <span className="text-xs text-slate-500">{segment.timing_status || 'timing: غير متاح'}</span>
              </div>
              <p className="text-sm text-slate-700" dir="ltr">{finalTranslation(segment)}</p>
              {segment.dubbed_audio_path ? (
                <div className="mt-3 rounded-xl border border-slate-200 p-3">
                  <div className="mb-2 inline-flex items-center gap-1 text-xs text-slate-600">
                    <Volume2 className="h-3.5 w-3.5" />
                    <span>مدة الصوت: {segment.audio_duration ? `${segment.audio_duration.toFixed(2)}s` : 'غير متوفرة'}</span>
                  </div>
                  <audio controls className="w-full" src={segmentAudioUrl(projectId, segment.id)} />
                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => void handleApproveSegment(segment.id)}
                      disabled={busyAction === 'approve' || !segment.dubbed_audio_path || !segment.audio_duration || segment.audio_review_status === 'approved'}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      اعتماد الصوت
                    </button>
                  </div>
                </div>
              ) : (
                !isGeneratingAudio && <p className="mt-2 text-xs text-amber-700">لم يُولَّد صوت لهذا المقطع بعد.</p>
              )}
            </article>
          ))}
        </section>
        )}

        {workflowStep === 'render' && shouldShowRenderSection && (
          <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-subtle">
            <h2 className="text-lg font-bold text-slate-900">إنشاء الفيديو النهائي</h2>
            <p className="mt-2 text-sm text-slate-600">
              تم اعتماد جميع الأصوات المطلوبة. يمكنك الآن إنشاء الفيديو المدبلج ثم معاينته وتنزيله.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void handleRender()}
                disabled={busyAction !== null || !canRender}
                className="rounded-xl bg-brand-800 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"
              >
                {busyAction === 'render' ? 'جارٍ إنشاء الفيديو المدبلج' : 'إنشاء الفيديو المدبلج'}
              </button>
              {dubbedReady && (
                <button
                  type="button"
                  onClick={() => void handleDownload()}
                  disabled={downloading}
                  className="inline-flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-sm font-bold text-emerald-800 disabled:opacity-60"
                >
                  {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  {downloading ? 'جارٍ التنزيل...' : 'تنزيل الفيديو المدبلج'}
                </button>
              )}
              {dubbedReady && onOpenReport && (
                <button
                  type="button"
                  onClick={() => void onOpenReport()}
                  className="inline-flex items-center gap-2 rounded-xl border border-brand-300 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-800"
                >
                  <FileText className="h-4 w-4" /> عرض التقرير
                </button>
              )}
            </div>
            {dubbedReady && (
              <div className="mt-4">
                <CenteredVideoPlayer
                  key={videoVersion ?? 'video'}
                  src={`${dubbedVideoUrl(projectId)}?v=${videoVersion ?? Date.now()}`}
                  title="الفيديو المدبلج"
                />
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-xl bg-slate-50 p-3">
    <p className="text-xs text-slate-500">{label}</p>
    <p className="mt-1 text-xl font-bold text-slate-900">{value}</p>
  </div>
);
