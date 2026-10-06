import React, { useState } from 'react';
import { PlatformDescription } from '../components/PlatformDescription';
import { VideoUploader } from '../components/VideoUploader';
import { VideoPreviewCard } from '../components/VideoPreviewCard';
import { LanguageSelector } from '../components/LanguageSelector';
import { DubbingModeSelector } from '../components/DubbingModeSelector';
import { PrivacyConsent } from '../components/PrivacyConsent';
import { ErrorBanner } from '../components/ErrorBanner';
import { DubbingMode, VideoMetadata, UploadErrorInfo } from '../types';
import { Sparkles, Loader2 } from 'lucide-react';

interface HomeScreenProps {
  onStartProcessing: (payload: {
    video: VideoMetadata;
    dubbingMode: DubbingMode;
    sourceLanguage: string;
    targetLanguage: string;
  }) => void | Promise<void>;
  initialVideo?: VideoMetadata | null;
  initialDubbingMode?: DubbingMode;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onStartProcessing,
  initialVideo = null,
  initialDubbingMode = 'timed',
}) => {
  const [video, setVideo] = useState<VideoMetadata | null>(initialVideo);
  const [error, setError] = useState<UploadErrorInfo | null>(null);
  
  // Dubbing mode: "الزمنية" selected by default as required
  const [dubbingMode, setDubbingMode] = useState<DubbingMode>(initialDubbingMode);
  
  // Privacy consent: unchecked by default
  const [privacyConsent, setPrivacyConsent] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Handle video selection from file uploader
  const handleVideoSelected = (newVideo: VideoMetadata) => {
    setVideo(newVideo);
    setError(null);
  };

  const handleUseSampleVideo = () => {
    setVideo({
      file: null,
      name: 'quran_tafseer_lesson_01.mp4',
      sizeBytes: 14.8 * 1024 * 1024,
      durationSeconds: 48,
      previewUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    });
    setError(null);
  };

  // Handle error messages
  const handleError = (errorInfo: UploadErrorInfo) => {
    setError(errorInfo);
  };

  // Handle delete video
  const handleDeleteVideo = () => {
    if (video?.previewUrl && video.file) {
      URL.revokeObjectURL(video.previewUrl);
    }
    setVideo(null);
    setError(null);
    setDubbingMode('timed');
  };

  // Handle replace video
  const handleReplaceVideo = () => {
    handleDeleteVideo();
  };

  // Handle retry
  const handleRetry = () => {
    setError(null);
  };

  // CTA trigger: Navigates to Screen 2
  const handleStartProcessing = async () => {
    if (!video || !privacyConsent) return;
    setIsProcessing(true);

    try {
      await onStartProcessing({
        video,
        dubbingMode,
        sourceLanguage: 'ar',
        targetLanguage: 'en',
      });
    } catch (requestError) {
      setIsProcessing(false);
      setError({
        type: 'UPLOAD_FAILED',
        title: 'تعذر بدء المعالجة',
        message: requestError instanceof Error ? requestError.message : 'حدث خطأ أثناء الاتصال بالخادم.',
        canRetry: true,
      });
    }
  };

  // CTA disabled condition: video must be uploaded AND privacy consent must be checked
  const canSubmit = Boolean(video) && privacyConsent && !isProcessing;

  return (
    <div className="flex min-h-[calc(100vh-180px)] flex-col selection:bg-brand-100 selection:text-brand-900">

      {/* Main Container - Optimized for Desktop 1440 × 900 */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        
        <div className="space-y-6">

          {/* 2. Short platform description */}
          <PlatformDescription />

          {/* Notification / Error message if triggered */}
          {error && (
            <div className="animate-in fade-in duration-200">
              <ErrorBanner
                error={error}
                onRetry={handleRetry}
                onDismiss={() => setError(null)}
              />
            </div>
          )}

          {/* 3. Video upload section */}
          <section aria-label="منطقة رفع الفيديو">
            {!video ? (
              <VideoUploader
                onVideoSelected={handleVideoSelected}
                onError={handleError}
                isProcessing={isProcessing}
                onUseSampleVideo={handleUseSampleVideo}
              />
            ) : (
              <VideoPreviewCard
                video={video}
                onReplace={handleReplaceVideo}
                onDelete={handleDeleteVideo}
              />
            )}
          </section>

          {/* 4. Source and target language settings */}
          <section aria-label="إعدادات اللغات">
            <LanguageSelector
              sourceLanguage="العربية"
              targetLanguage="الإنجليزية"
            />
          </section>

          {/* 5. Dubbing mode selection */}
          <section aria-label="نمط الدبلجة">
            <DubbingModeSelector
              selectedMode={dubbingMode}
              onSelectMode={setDubbingMode}
            />
          </section>

          {/* 6. AI processing consent and privacy notice */}
          <section aria-label="الموافقة والخصوصية">
            <PrivacyConsent
              checked={privacyConsent}
              onChange={setPrivacyConsent}
              disabled={isProcessing}
            />
          </section>

          {/* 7. Primary 'ابدأ المعالجة' button */}
          <section aria-label="إجراء بدء المعالجة" className="pt-2 flex flex-col items-stretch sm:items-end">
            <button
              type="button"
              onClick={handleStartProcessing}
              disabled={!canSubmit}
              className={`w-full sm:w-auto min-w-[240px] px-8 py-4 rounded-xl font-bold text-base transition-all duration-200 flex items-center justify-center gap-3 shadow-premium ${
                canSubmit
                  ? 'bg-brand-800 hover:bg-brand-700 text-white cursor-pointer active:scale-98 shadow-brand-900/10'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-200 shadow-none'
              }`}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-white" />
                  <span>جارٍ الانتقال للمعالجة...</span>
                </>
              ) : (
                <>
                  <span>ابدأ المعالجة</span>
                  <Sparkles className={`w-4 h-4 ${canSubmit ? 'text-amber-300' : 'text-slate-400'}`} />
                </>
              )}
            </button>

            {/* Helper status text when disabled */}
            {!canSubmit && (
              <p className="text-xs text-slate-400 mt-2.5 text-center sm:text-right">
                {!video && !privacyConsent
                  ? 'يُرجى رفع مقطع فيديو صالح وتأكيد الموافقة للمتابعة'
                  : !video
                  ? 'يُرجى رفع مقطع فيديو صالح أولاً'
                  : 'يُرجى تأكيد الموافقة على معالجة الفيديو بالذكاء الاصطناعي'}
              </p>
            )}
          </section>

        </div>

      </main>

      {/* Footer */}
      <footer className="mt-6 w-full border-t border-slate-200/60 bg-white/40 py-6 text-center text-xs text-slate-400">
        <p>منصة بلاغ (BALAGH) — دبلجة ذكية واعية بالسياق والمصطلحات الإسلامية © 2026</p>
      </footer>

    </div>
  );
};
