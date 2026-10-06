import React, { useCallback, useEffect, useState } from 'react';
import { HomeScreen } from './screens/HomeScreen';
import { ProcessingScreen } from './screens/ProcessingScreen';
import { BackendProcessingScreen } from './screens/BackendProcessingScreen';
import { TranscriptionReviewScreen } from './screens/TranscriptionReviewScreen';
import { DubbingScreen } from './screens/DubbingScreen';
import { ReportScreen } from './screens/ReportScreen';
import { CompletionScreen } from './screens/CompletionScreen';
import { Header } from './components/Header';
import { assertBackendReady, createProject, getPipelineStatus, uploadVideo } from './services/api';
import type { PipelineStatus } from './services/api';
import { WizardControls, WizardStepper } from './wizard/WizardBar';
import {
  EMPTY_STATUS,
  WizardStep,
  firstIncompleteStep,
  guardStep,
  loadStoredStatus,
  mergeStatus,
  normalizeStatus,
  saveStoredStatus,
} from './wizard/wizard';
import { ScreenType, VideoMetadata, DubbingMode } from './types';

const DEFAULT_SAMPLE_VIDEO: VideoMetadata = {
  file: null,
  name: 'quran_tafseer_lesson_01.mp4',
  sizeBytes: 14.8 * 1024 * 1024,
  durationSeconds: 48,
  previewUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
};

export const App: React.FC = () => {
  const initialProjectMatch = typeof window !== 'undefined'
    ? window.location.pathname.match(/^\/projects\/([0-9a-f-]+)\/(review|dubbing|report)\/?$/i)
    : null;
  const initialReviewProjectId = initialProjectMatch?.[1] ?? null;
  const initialPathStep = initialProjectMatch?.[2]?.toLowerCase();
  const initialReviewStep: WizardStep = initialPathStep === 'dubbing' || initialPathStep === 'report'
    ? initialPathStep
    : 'review';
  const initialCompletion = typeof window !== 'undefined'
    && /^\/projects\/[0-9a-f-]+\/complete\/?$/i.test(window.location.pathname);
  const [showCompletion, setShowCompletion] = useState(initialCompletion);
  const [backendProjectId, setBackendProjectId] = useState<string | null>(initialReviewProjectId);
  const [backendJobId, setBackendJobId] = useState<string | null>(null);
  const [showBackendReview, setShowBackendReview] = useState(Boolean(initialReviewProjectId));
  const [currentScreen, setCurrentScreen] = useState<ScreenType>(() => {
    if (typeof window !== 'undefined') {
      const param = new URLSearchParams(window.location.search).get('screen');
      if (param === 'timing_review' || param === 'review' || param === 'processing' || param === 'home') {
        return param as ScreenType;
      }
    }
    return 'home';
  });

  const [activeVideo, setActiveVideo] = useState<VideoMetadata | null>(() => {
    if (typeof window !== 'undefined') {
      const param = new URLSearchParams(window.location.search).get('screen');
      if (param === 'timing_review' || param === 'review' || param === 'processing') {
        return DEFAULT_SAMPLE_VIDEO;
      }
    }
    return null;
  });

  const [selectedDubbingMode, setSelectedDubbingMode] = useState<DubbingMode>('timed');
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>(() => loadStoredStatus(initialReviewProjectId));
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [reviewStep, setReviewStep] = useState<WizardStep>(initialReviewStep);

  // Synchronize the wizard status with the backend; fall back to local storage when unreachable.
  const refreshStatus = useCallback(async () => {
    let remote: PipelineStatus | null = null;
    try {
      remote = backendProjectId
        ? await getPipelineStatus(backendProjectId)
        : { ...EMPTY_STATUS };
    } catch {
      remote = null;
    }
    const merged = mergeStatus(loadStoredStatus(backendProjectId), remote);
    saveStoredStatus(backendProjectId, merged);
    setPipelineStatus(merged);
    setStatusLoaded(true);
  }, [backendProjectId]);

  useEffect(() => {
    setStatusLoaded(false);
    void refreshStatus();
  }, [refreshStatus, showBackendReview, backendJobId]);

  // Keep the status fresh while a project is open.
  useEffect(() => {
    if (!backendProjectId) return undefined;
    const timer = window.setInterval(() => void refreshStatus(), 5000);
    return () => window.clearInterval(timer);
  }, [backendProjectId, refreshStatus]);

  // Guard: a manually entered review URL is redirected when the review step is locked.
  useEffect(() => {
    if (!statusLoaded || !backendProjectId || !showBackendReview) return;
    if (guardStep(pipelineStatus, reviewStep) !== reviewStep) {
      const fallback = guardStep(pipelineStatus, reviewStep);
      if (fallback === 'review' || fallback === 'dubbing' || fallback === 'report') {
        setReviewStep(fallback);
        window.history.replaceState({}, '', `/projects/${backendProjectId}/${fallback}`);
        return;
      }
      window.history.replaceState({}, '', `/projects/${backendProjectId}`);
      setShowBackendReview(false);
    }
  }, [statusLoaded, backendProjectId, showBackendReview, pipelineStatus, reviewStep]);

  const normalizedStatus = normalizeStatus(pipelineStatus);
  const showWizard = Boolean(backendProjectId) || currentScreen === 'home';
  const currentStep: WizardStep = (() => {
    if (!backendProjectId) return 'project';
    if (showBackendReview) {
      return guardStep(normalizedStatus, reviewStep) === reviewStep
        ? reviewStep
        : firstIncompleteStep(normalizedStatus);
    }
    return normalizedStatus.transcription ? 'transcription' : 'upload';
  })();

  const handleWizardNavigate = (step: WizardStep) => {
    const target = guardStep(normalizedStatus, step);
    if (target === 'project') {
      if (backendProjectId) handleBackToHome();
      return;
    }
    if (!backendProjectId) return;
    if (target === 'upload' || target === 'transcription') {
      window.history.pushState({}, '', `/projects/${backendProjectId}`);
      setShowBackendReview(false);
      return;
    }
    setReviewStep(target);
    if (!showBackendReview) setShowBackendReview(true);
    const reviewPath = target === 'dubbing' || target === 'report' ? target : 'review';
    window.history.pushState({}, '', `/projects/${backendProjectId}/${reviewPath}`);
  };

  // Navigate from Screen 1 (Home) to Screen 2 (Processing)
  const handleStartProcessing = async (payload: {
    video: VideoMetadata;
    dubbingMode: DubbingMode;
    sourceLanguage: string;
    targetLanguage: string;
  }) => {
    setActiveVideo(payload.video);
    setSelectedDubbingMode(payload.dubbingMode);
    if (payload.video.file) {
      // Single health check before any project is created or video uploaded.
      await assertBackendReady();
      const project = await createProject({
        title: payload.video.name.replace(/\.[^.]+$/, '') || 'BALAGH project',
        source_language: payload.sourceLanguage,
        target_language: payload.targetLanguage,
        dubbing_mode: payload.dubbingMode,
      });
      const upload = await uploadVideo(project.id, payload.video.file);
      setBackendProjectId(project.id);
      setBackendJobId(upload.job_id);
      setShowBackendReview(false);
      window.history.pushState({}, '', `/projects/${project.id}`);
      setCurrentScreen('processing');
      return;
    }
    setBackendProjectId(null);
    setBackendJobId(null);
    setCurrentScreen('processing');
  };

  // Cancel processing: Navigate back to Screen 1
  const handleCancelProcessing = () => {
    setCurrentScreen('home');
  };

  // Navigate from Screen 2 (Processing) to Screen 3 (Review)
  const handleNavigateToReview = () => {
    setCurrentScreen('review');
  };

  // Return to Home
  const handleBackToHome = () => {
    setShowCompletion(false);
    setBackendProjectId(null);
    setBackendJobId(null);
    setShowBackendReview(false);
    window.history.pushState({}, '', '/');
    setCurrentScreen('home');
  };

  const handleOpenBackendReview = () => {
    if (!backendProjectId) return;
    setReviewStep('review');
    window.history.pushState({}, '', `/projects/${backendProjectId}/review`);
    setShowBackendReview(true);
  };

  const handleBackToBackendProject = () => {
    if (backendProjectId) {
      window.history.pushState({}, '', `/projects/${backendProjectId}`);
    } else {
      setBackendProjectId(null);
      window.history.pushState({}, '', '/');
      setCurrentScreen('home');
    }
    setShowBackendReview(false);
  };

  // Final thank-you page shown after the report (full page, no wizard).
  const handleFinishProject = () => {
    if (!backendProjectId) return;
    window.history.pushState({}, '', `/projects/${backendProjectId}/complete`);
    setShowBackendReview(false);
    setBackendProjectId(null);
    setBackendJobId(null);
    setShowCompletion(true);
    window.scrollTo({ top: 0 });
  };

  const handleStartNewProject = () => {
    saveStoredStatus(null, { ...EMPTY_STATUS });  // start the wizard from a clean draft
    setActiveVideo(null);
    handleBackToHome();
    window.scrollTo({ top: 0 });
  };

  if (showCompletion) {
    return (
      <div className="min-h-screen bg-[#060B1E] font-arabic">
        <Header />
        <CompletionScreen
          onGoHome={() => {
            handleBackToHome();
            window.scrollTo({ top: 0 });
          }}
          onStartNewProject={handleStartNewProject}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-slate-800 font-arabic">
      <Header />
      {showWizard && (
        <WizardStepper status={normalizedStatus} current={currentStep} onNavigate={handleWizardNavigate} />
      )}
      {backendProjectId && showBackendReview && (
        reviewStep === 'report' ? (
          <ReportScreen
            projectId={backendProjectId}
            onFinish={handleFinishProject}
            onBack={() => {
              setReviewStep('dubbing');
              window.history.pushState({}, '', `/projects/${backendProjectId}/dubbing`);
            }}
          />
        ) : reviewStep === 'dubbing' ? (
          <DubbingScreen
            projectId={backendProjectId}
            onBack={() => {
              setReviewStep('review');
              window.history.pushState({}, '', `/projects/${backendProjectId}/review`);
            }}
            onOpenReport={async () => {
              // Refresh first so the step guard sees the completed dubbing step.
              await refreshStatus();
              setReviewStep('report');
              window.history.pushState({}, '', `/projects/${backendProjectId}/report`);
            }}
          />
        ) : (
          <TranscriptionReviewScreen
            projectId={backendProjectId}
            onBack={handleBackToBackendProject}
            onGoToDubbing={() => {
              setReviewStep('dubbing');
              window.history.pushState({}, '', `/projects/${backendProjectId}/dubbing`);
            }}
          />
        )
      )}
      {backendProjectId && !showBackendReview && (
        <BackendProcessingScreen
          key={backendProjectId}
          projectId={backendProjectId}
          initialJobId={backendJobId}
          onOpenReview={handleOpenBackendReview}
          onBackHome={handleBackToHome}
        />
      )}
      {/* Screen 1: Home / Video Upload */}
      {!backendProjectId && currentScreen === 'home' && (
        <HomeScreen
          onStartProcessing={handleStartProcessing}
          initialVideo={activeVideo}
          initialDubbingMode={selectedDubbingMode}
        />
      )}

      {showWizard && (
        <WizardControls status={normalizedStatus} current={currentStep} onNavigate={handleWizardNavigate} />
      )}

      {/* Screen 2: Processing */}
      {!backendProjectId && currentScreen === 'processing' && activeVideo && (
        <ProcessingScreen
          video={activeVideo}
          dubbingMode={selectedDubbingMode}
          onCancelProcessing={handleCancelProcessing}
          onNavigateToReview={handleNavigateToReview}
        />
      )}

    </div>
  );
};

export default App;
