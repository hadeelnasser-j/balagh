import React, { useState, useEffect } from 'react';
import { StageItem } from '../components/StageItem';
import { CancelConfirmModal } from '../components/CancelConfirmModal';
import { ProcessingErrorCard } from '../components/ProcessingErrorCard';
import { ProcessingStage, VideoMetadata, DubbingMode } from '../types';
import { Clock, Sparkles, CheckCircle2, FileText, ArrowLeft, FastForward } from 'lucide-react';

interface ProcessingScreenProps {
  video: VideoMetadata;
  dubbingMode: DubbingMode;
  onCancelProcessing: () => void;
  onNavigateToReview: () => void;
  onProcessingComplete?: () => void;
}

const INITIAL_STAGES: Omit<ProcessingStage, 'status'>[] = [
  { id: 'upload', number: 1, title: 'رفع الفيديو', description: 'نقل وتأمين ملف الفيديو المرفوع على خوادم المعالجة' },
  { id: 'audio_extraction', number: 2, title: 'استخراج الصوت', description: 'فصل المسار الصوتي بدقة وعزل المؤثرات الخلفية' },
  { id: 'transcription', number: 3, title: 'التفريغ', description: 'تحويل الكلام الصوتي إلى نصوص دقيقة مع علامات الوقف' },
  { id: 'term_discovery', number: 4, title: 'اكتشاف المصطلحات', description: 'التعرف على المفاهيم الشرعية والسياقية الحساسة وحمايتها' },
  { id: 'translation', number: 5, title: 'الترجمة', description: 'دبلجة المعنى ونقل الدلالات بوعي وأمانة' },
  { id: 'voice_generation', number: 6, title: 'توليد الصوت', description: 'إنتاج الصوت الاصطناعي بنبرة ملائمة للخطاب الديني' },
  { id: 'timing_check', number: 7, title: 'فحص الزمن', description: 'مزامنة نبرات الصوت ومطابقتها لحركة الشفاه وتوقيت المشهد' },
  { id: 'final_packaging', number: 8, title: 'تجهيز النتيجة', description: 'دمج الصوت المدبلج مع الفيديو وإعداد ملف العرض النهائي' },
];

export const ProcessingScreen: React.FC<ProcessingScreenProps> = ({
  video,
  dubbingMode,
  onCancelProcessing,
  onNavigateToReview,
  onProcessingComplete,
}) => {
  const [stages, setStages] = useState<ProcessingStage[]>(() =>
    INITIAL_STAGES.map((st, idx) => ({
      ...st,
      status: idx === 0 ? 'in_progress' : 'pending',
    }))
  );

  const [currentStageIdx, setCurrentStageIdx] = useState<number>(0);
  const [progressPercent, setProgressPercent] = useState<number>(12);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState<boolean>(false);
  const [activeError, setActiveError] = useState<{ title?: string; message: string } | null>(null);

  const isCompleted = progressPercent === 100 || currentStageIdx >= stages.length;

  // Automated Mock Processing Simulation
  useEffect(() => {
    if (activeError) return; // Pause while in error state

    // If all completed
    if (currentStageIdx >= stages.length) {
      setProgressPercent(100);
      if (onProcessingComplete) onProcessingComplete();
      return;
    }

    const timer = setTimeout(() => {
      // Complete current stage and move to next
      setStages((prevStages) =>
        prevStages.map((stage, idx) => {
          if (idx < currentStageIdx) return { ...stage, status: 'completed' };
          if (idx === currentStageIdx) return { ...stage, status: 'completed' };
          if (idx === currentStageIdx + 1) return { ...stage, status: 'in_progress' };
          return { ...stage, status: 'pending' };
        })
      );

      const nextIdx = currentStageIdx + 1;
      setCurrentStageIdx(nextIdx);

      // Smooth percentage calculation across 8 stages
      const nextPercent = Math.min(100, Math.round(((nextIdx) / stages.length) * 100));
      setProgressPercent(nextPercent);
    }, 1800); // 1.8s per stage for comfortable pacing

    return () => clearTimeout(timer);
  }, [currentStageIdx, activeError, stages.length, onProcessingComplete]);

  // Fast forward simulation directly to 100% for easy demo/testing
  const handleFastForward = () => {
    setStages((prev) => prev.map((s) => ({ ...s, status: 'completed' })));
    setCurrentStageIdx(stages.length);
    setProgressPercent(100);
  };

  // Handle retry from error state
  const handleRetry = () => {
    setActiveError(null);
    setStages((prevStages) =>
      prevStages.map((st, idx) => {
        if (idx === currentStageIdx) return { ...st, status: 'in_progress' };
        return st;
      })
    );
  };

  // Helper for simulating error
  const triggerSampleError = () => {
    setStages((prevStages) =>
      prevStages.map((st, idx) => {
        if (idx === currentStageIdx) return { ...st, status: 'error' };
        return st;
      })
    );
    setActiveError({
      title: 'تعذر التعرف على الكلام بوضوح',
      message: 'تعذر التعرف على الكلام بوضوح في هذا المقطع. يُرجى تجربة فيديو بصوت أوضح أو ضوضاء أقل، ثم الضغط على إعادة المحاولة.',
    });
  };

  const currentStageName = isCompleted
    ? 'اكتملت جميع مراحل المعالجة بنجاح'
    : currentStageIdx < stages.length
    ? stages[currentStageIdx].title
    : 'اكتملت جميع مراحل المعالجة';

  return (
    <div className="flex min-h-[calc(100vh-180px)] flex-col selection:bg-brand-100 selection:text-brand-900">

      {/* Main Processing Container - Desktop 1440 × 900 Optimized */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        
        {/* Top Active Processing Card */}
        <section 
          aria-label="حالة المعالجة الحالية"
          className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-6 sm:p-7 mb-6"
        >
          {/* Header of card: Stage title & Percentage */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  isCompleted
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-brand-50 text-brand-800 border border-brand-200/60'
                }`}>
                  {isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-brand-600 animate-spin" />
                  )}
                  {isCompleted ? 'اكتملت المعالجة 100%' : 'دبلجة جارية بالذكاء الاصطناعي'}
                </span>
                <span className="text-xs text-slate-400">
                  النمط: {dubbingMode === 'faithful' ? 'الأمينة' : dubbingMode === 'timed' ? 'الزمنية' : 'المبسطة'}
                </span>
              </div>

              <h2 className="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
                <span>{isCompleted ? 'النتيجة:' : 'المرحلة الحالية:'}</span>
                <span className={`${isCompleted ? 'text-emerald-700 font-extrabold' : 'text-brand-900 font-extrabold'}`}>
                  {currentStageName}
                </span>
              </h2>
            </div>

            {/* Percentage Display */}
            <div className="flex items-baseline gap-1 sm:self-center">
              <span className={`text-3xl sm:text-4xl font-extrabold font-mono tracking-tight ${
                isCompleted ? 'text-emerald-600' : 'text-brand-800'
              }`}>
                {progressPercent}%
              </span>
              <span className="text-xs text-slate-400 font-medium">مكتمل</span>
            </div>
          </div>

          {/* Smooth Animated Progress Bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden p-0.5 border border-slate-200/60">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out shadow-sm ${
                isCompleted
                  ? 'bg-emerald-600'
                  : 'bg-gradient-to-l from-brand-600 to-brand-800'
              }`}
              style={{ width: `${progressPercent}%` }}
              role="progressbar"
              aria-valuenow={progressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>

          {/* Prompt 100% Navigation Banner when completed */}
          {isCompleted ? (
            <div className="mt-5 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in duration-300">
              <div className="flex items-center gap-2.5">
                <FileText className="w-5 h-5 text-emerald-700 shrink-0" />
                <p className="text-xs sm:text-sm font-semibold text-emerald-900">
                  تم الانتهاء من المعالجة بنجاح. النصوص والمصطلحات جاهزة للمراجعة والتدقيق الدلالي.
                </p>
              </div>

              <button
                type="button"
                onClick={onNavigateToReview}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-800 hover:bg-brand-700 text-white font-bold text-sm shadow-premium transition-all active:scale-98 shrink-0"
              >
                <span>مراجعة النص والمصطلحات</span>
                <ArrowLeft className="w-4 h-4" />
              </button>
            </div>
          ) : (
            /* Time & File info footer during processing */
            <div className="mt-5 pt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand-600 shrink-0" />
                <p className="font-medium text-slate-600">
                  قد تستغرق المعالجة بضع دقائق حسب مدة الفيديو وجودته.
                </p>
              </div>

              <div className="flex items-center gap-2 text-slate-400">
                <span className="truncate max-w-[200px]" title={video.name}>{video.name}</span>
              </div>
            </div>
          )}
        </section>

        {/* Error notification if triggered */}
        {activeError && (
          <div className="mb-6">
            <ProcessingErrorCard
              title={activeError.title}
              message={activeError.message}
              onRetry={handleRetry}
            />
          </div>
        )}

        {/* 2. Processing Stages Visible List */}
        <section aria-label="مراحل معالجة المحتوى" className="space-y-4 mb-8">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-base font-bold text-slate-800">
              مراحل المعالجة الثمانية
            </h3>
            <span className="text-xs text-slate-400">
              المرحلة {Math.min(currentStageIdx + 1, 8)} من 8
            </span>
          </div>

          <div className="space-y-2.5">
            {stages.map((stage, idx) => (
              <StageItem
                key={stage.id}
                stage={stage}
                isCurrent={idx === currentStageIdx}
              />
            ))}
          </div>
        </section>

        {/* 3. Action Footer */}
        <section 
          aria-label="إجراءات التحكم"
          className="pt-2 pb-6 border-t border-slate-200/80 flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          {/* Secondary Button: إلغاء المعالجة (Only available before completion) */}
          {!isCompleted ? (
            <button
              type="button"
              onClick={() => setIsCancelModalOpen(true)}
              className="w-full sm:w-auto px-6 py-3 rounded-xl border border-slate-300 text-slate-700 hover:text-rose-700 hover:border-rose-200 hover:bg-rose-50/50 font-medium text-sm transition-all shadow-subtle active:scale-98"
            >
              إلغاء المعالجة
            </button>
          ) : (
            <button
              type="button"
              onClick={onNavigateToReview}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl bg-brand-800 hover:bg-brand-700 text-white font-bold text-sm shadow-premium transition-all active:scale-98"
            >
              <span>مراجعة النص والمصطلحات</span>
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}

          {/* Dev/Demo Fast Forward & Test Triggers */}
          <div className="flex items-center gap-3">
            {!isCompleted && !activeError && (
              <button
                type="button"
                onClick={handleFastForward}
                className="inline-flex items-center gap-1 text-[11px] text-brand-700 hover:text-brand-900 bg-brand-50 px-2.5 py-1 rounded-lg border border-brand-200/70 transition-colors"
                title="تسريع المحاكاة للوصول الفوري إلى 100% لتجربة الشاشة 3"
              >
                <FastForward className="w-3 h-3" />
                <span>تخطي للانتهاء (100%)</span>
              </button>
            )}

            {!activeError && !isCompleted && (
              <button
                type="button"
                onClick={triggerSampleError}
                className="text-[11px] text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors"
                title="محاكاة خطأ معالجة لاختبار زر إعادة المحاولة"
              >
                (تجربة حالة الخطأ)
              </button>
            )}
          </div>
        </section>

      </main>

      {/* Confirmation Dialog on Cancel */}
      <CancelConfirmModal
        isOpen={isCancelModalOpen}
        onConfirm={() => {
          setIsCancelModalOpen(false);
          onCancelProcessing();
        }}
        onCancel={() => setIsCancelModalOpen(false)}
      />

      {/* Subtle Footer */}
      <footer className="w-full py-6 mt-auto border-t border-slate-200/60 bg-white/40 text-center text-xs text-slate-400">
        <p>منصة بلاغ (BALAGH) — دبلجة ذكية واعية بالسياق والمصطلحات الإسلامية © 2026</p>
      </footer>

    </div>
  );
};
