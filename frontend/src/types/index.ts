export type DubbingMode = 'faithful' | 'timed' | 'simplified';

export interface VideoMetadata {
  file: File | null;
  name: string;
  sizeBytes: number;
  durationSeconds: number;
  previewUrl: string;
}

export type UploadErrorType = 
  | 'INVALID_FORMAT'
  | 'FILE_TOO_LARGE'
  | 'DURATION_EXCEEDED'
  | 'UPLOAD_FAILED'
  | null;

export interface UploadErrorInfo {
  type: UploadErrorType;
  title: string;
  message: string;
  canRetry?: boolean;
}

export interface ProcessingPayload {
  video: VideoMetadata;
  sourceLanguage: string;
  targetLanguage: string;
  dubbingMode: DubbingMode;
  privacyConsent: boolean;
}

export type StageStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface ProcessingStage {
  id: string;
  number: number;
  title: string;
  description?: string;
  status: StageStatus;
  errorMessage?: string;
}

export type ScreenType = 'home' | 'processing' | 'review' | 'timing_review';

export type ConfidenceLevel = 'high' | 'medium' | 'needs_review';

export interface TranscriptSegment {
  id: string;
  startTime: string;
  endTime: string;
  text: string;
  confidence: ConfidenceLevel;
  confidencePercent?: number;
  hasMeaningLockAlert?: boolean;
}

export interface TerminologyItem {
  id: string;
  term: string;
  approvedEquivalent: string;
  definition: string;
  confidencePercent: number;
  riskLevel: 'مرتفعة' | 'متوسطة' | 'منخفضة';
  reviewStatus: 'مطلوبة' | 'تمت' | 'قيد المراجعة';
  source: string;
  status: 'pending' | 'approved' | 'sent_for_review';
}

export interface ProtectedMeaning {
  id: string;
  text: string;
  isViolated: boolean;
}

export type TimingStatus = 'suitable' | 'needs_improvement' | 'needs_adjustment';

export interface TranslationSegment {
  id: string;
  arabicText: string;
  timestamp: string;
  englishTranslation: string;
  shorterAlternative?: string;
  sourceDurationSec: number;
  translatedDurationSec: number;
  durationDifferencePercent: number;
  timingStatus: TimingStatus;
  isMeaningPreserved: boolean;
  missingMeaningText?: string;
  isApproved: boolean;
  isRegenerating?: boolean;
}

export type AudioTrackOption = 'dubbed' | 'original' | 'mixed';
export type DubbingPacing = 'normal' | 'natural_fast' | 'dynamic';

