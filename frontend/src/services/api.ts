const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export interface ProcessingJob {
  job_id: string;
  project_id: string;
  status: string;
  progress: number;
  current_step: string | null;
  error_message: string | null;
}

export interface ProjectRecord {
  id: string;
  source_language: string;
  target_language: string;
  srt_storage_path?: string | null;
}

export interface ReviewSegment {
  id: string;
  project_id: string;
  segment_index: number;
  start_time: number;
  end_time: number;
  original_text: string;
  translated_text: string | null;
  edited_translation: string | null;
  final_translation: string | null;
  translation_status: 'pending' | 'translating' | 'translated' | 'failed';
  translation_warning: string | null;
  review_status: 'pending' | 'edited' | 'approved' | 'rejected';
  translation_error: string | null;
  review_note: string | null;
  source_language: string | null;
  target_language: string;
  content_type?: string;
  source_verification_status?: string;
  source_review_status?: string;
  source_match_score?: number | null;
  reference?: string | null;
  verification_source?: string | null;
  translation_source?: string | null;
  translation_origin?: string | null;
  hadith_grade?: string | null;
  meaning_lock_status?: string;
  text_verified?: boolean;
  translation_verified?: boolean;
  recitation_verified?: boolean;
  ready_for_dubbing?: boolean;
  dubbed_audio_path?: string | null;
  audio_duration?: number | null;
  timing_status?: string | null;
  audio_review_status?: string | null;
  audio_mode?: 'tts' | 'original' | 'blocked';
}

export interface SegmentPage {
  project_id: string;
  total: number;
  page: number;
  page_size: number;
  items: ReviewSegment[];
}

export interface ReviewSummary {
  total_segments: number;
  translated_segments: number;
  failed_segments: number;
  pending_review: number;
  edited_segments: number;
  approved_segments: number;
  can_generate_srt: boolean;
}

export interface HealthStatus {
  status: string;
  supabase: string;
  ffmpeg: string;
  ffprobe?: string;
  transcription_provider: string;
  translation_provider: string;
  openai_configured: boolean;
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number | null = null) {
    super(message);
    this.name = 'ApiError';
  }
}

export const MESSAGES = {
  network: 'تعذر الاتصال بالخادم. تأكد من تشغيل خدمة المعالجة.',
  cors: 'تعذر الاتصال بالخادم بسبب إعدادات الوصول. يرجى مراجعة إعدادات الخادم.',
  supabase: 'خدمة التخزين أو قاعدة البيانات غير متاحة حاليًا.',
  ffmpeg: 'خدمة معالجة الفيديو غير جاهزة على الخادم.',
  generic: 'حدث خطأ أثناء الاتصال بالخادم.',
  missingBase: 'يرجى ضبط عنوان الخادم في VITE_API_BASE_URL.',
} as const;

// Join base URL and path without duplicating slashes or the /api prefix.
export function buildApiUrl(base: string | undefined, path: string): string {
  const cleanBase = (base ?? '').trim().replace(/\/+$/, '').replace(/\/api$/, '');
  if (!cleanBase) throw new ApiError(MESSAGES.missingBase);
  return `${cleanBase}/${path.replace(/^\/+/, '')}`;
}

function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null;
  const { message, detail } = body as { message?: unknown; detail?: unknown };
  if (typeof message === 'string' && message) return message;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const validationRows = detail
      .map((item) => {
        if (!item || typeof item !== 'object') return null;
        const row = item as { loc?: unknown; msg?: unknown };
        const loc = Array.isArray(row.loc)
          ? row.loc.map((part) => String(part)).join('.')
          : null;
        const msg = typeof row.msg === 'string' ? row.msg : null;
        if (!loc && !msg) return null;
        if (loc && msg) return `${loc}: ${msg}`;
        return loc || msg;
      })
      .filter((entry): entry is string => Boolean(entry));
    if (validationRows.length > 0) {
      return `الحقول غير صالحة: ${validationRows.join(' | ')}`;
    }
  }
  return null;
}

// Network failures surface as TypeError; a different origin makes CORS the likely cause.
export function networkErrorMessage(base: string | undefined): string {
  try {
    const apiOrigin = new URL(base ?? '').origin;
    if (typeof window !== 'undefined' && apiOrigin !== window.location.origin && window.location.protocol === 'https:' && apiOrigin.startsWith('http:')) {
      return MESSAGES.cors;
    }
  } catch {
    // Fall through to the generic network message.
  }
  return MESSAGES.network;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = buildApiUrl(API_BASE_URL, path);
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new ApiError(networkErrorMessage(API_BASE_URL));
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON responses fall back to the safe generic message.
    }
    throw new ApiError(extractDetail(body) ?? MESSAGES.generic, response.status);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>('/api/health');
}

// Returns Arabic messages for each unavailable service; empty means ready to process.
export function unavailableServices(health: HealthStatus): string[] {
  const problems: string[] = [];
  if (health.supabase !== 'available') problems.push(MESSAGES.supabase);
  if (health.ffmpeg !== 'available' || (health.ffprobe !== undefined && health.ffprobe !== 'available')) {
    problems.push(MESSAGES.ffmpeg);
  }
  if (!health.openai_configured) problems.push('مفتاح OpenAI غير مضبوط على الخادم.');
  return problems;
}

export async function assertBackendReady(): Promise<void> {
  const problems = unavailableServices(await getHealth());
  if (problems.length > 0) throw new ApiError(problems.join(' '), 503);
}

if (import.meta.env.DEV) {
  console.info('API base URL configured:', Boolean(API_BASE_URL));
}
export async function createProject(payload: {
  title: string;
  source_language: string;
  target_language: string;
  dubbing_mode: string;
}): Promise<ProjectRecord> {
  return request<ProjectRecord>('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function uploadVideo(projectId: string, file: File): Promise<ProcessingJob> {
  const body = new FormData();
  body.append('file', file);
  return request<ProcessingJob>(`/api/projects/${projectId}/upload`, {
    method: 'POST',
    body,
  });
}

export async function getJob(jobId: string): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/api/jobs/${jobId}`);
}

export async function getProject(projectId: string): Promise<ProjectRecord> {
  return request<ProjectRecord>(`/api/projects/${projectId}`);
}

export async function startTranscription(projectId: string): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/api/projects/${projectId}/transcribe`, { method: 'POST' });
}

export async function startTranslation(projectId: string): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/api/projects/${projectId}/translate`, { method: 'POST' });
}

export async function getSegments(projectId: string, page: number, pageSize = 50): Promise<SegmentPage> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return request<SegmentPage>(`/api/projects/${projectId}/segments?${query}`);
}

export async function getReviewSummary(projectId: string): Promise<ReviewSummary> {
  return request<ReviewSummary>(`/api/projects/${projectId}/review-summary`);
}

export async function editSegment(segmentId: string, editedTranslation: string): Promise<ReviewSegment> {
  return request<ReviewSegment>(`/api/segments/${segmentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edited_translation: editedTranslation }),
  });
}

export async function approveSegment(segmentId: string): Promise<ReviewSegment> {
  return request<ReviewSegment>(`/api/segments/${segmentId}/approve`, { method: 'POST' });
}

export async function rejectSegment(segmentId: string): Promise<ReviewSegment> {
  return request<ReviewSegment>(`/api/segments/${segmentId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
}

export async function generateSrt(projectId: string, mode?: 'draft' | 'final'): Promise<void> {
  const query = mode ? `?mode=${mode}` : '';
  await request(`/api/projects/${projectId}/generate-srt${query}`, { method: 'POST' });
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export interface SourceMatch {
  id: string | null;
  segment_id: string | null;
  source_id: string;
  source_name: string | null;
  title: string | null;
  reference_key: string | null;
  exact_quote: string | null;
  url: string | null;
  match_type: string;
  match_score: number;
  status: 'candidate' | 'verified' | 'rejected' | 'conflict';
}

export interface MeaningLock {
  id: string;
  segment_id: string;
  original_span: string;
  translated_span: string | null;
  lock_type: string;
  risk_level: 'low' | 'medium' | 'high';
  review_status: 'pending' | 'approved' | 'rejected';
}

export interface SourceSummary {
  project_id: string;
  total_segments: number;
  religious_segments: number;
  verified: number;
  candidate: number;
  not_found: number;
  conflict: number;
  pending: number;
  pending_locks: number;
  ready_for_dubbing: number;
  blocked_reasons: Record<string, string[]>;
}

export interface DubbingCheck {
  project_id: string;
  ready: boolean;
  segments_total: number;
  segments_ready: number;
}

export async function verifySources(projectId: string): Promise<void> {
  await request(`/api/projects/${projectId}/verify-sources`, { method: 'POST' });
}

export async function getSourceSummary(projectId: string): Promise<SourceSummary> {
  return request<SourceSummary>(`/api/projects/${projectId}/source-summary`);
}

export async function checkDubbingReadiness(projectId: string): Promise<DubbingCheck> {
  return request<DubbingCheck>(`/api/projects/${projectId}/dubbing-check`, { method: 'POST' });
}

export async function getSourceMatches(segmentId: string): Promise<SourceMatch[]> {
  return request<SourceMatch[]>(`/api/segments/${segmentId}/source-matches`);
}

export async function reviewSourceMatch(
  segmentId: string, matchId: string, action: 'approve' | 'reject', reviewedBy: string,
): Promise<SourceMatch> {
  return request<SourceMatch>(`/api/segments/${segmentId}/source-matches/${matchId}/${action}`, {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ reviewed_by: reviewedBy }),
  });
}

export async function getMeaningLocks(segmentId: string): Promise<MeaningLock[]> {
  return request<MeaningLock[]>(`/api/segments/${segmentId}/meaning-locks`);
}

export async function updateMeaningLock(lockId: string, reviewStatus: 'approved' | 'rejected'): Promise<MeaningLock> {
  return request<MeaningLock>(`/api/meaning-locks/${lockId}`, {
    method: 'PATCH', headers: JSON_HEADERS, body: JSON.stringify({ review_status: reviewStatus }),
  });
}

export async function downloadSrt(projectId: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(buildApiUrl(API_BASE_URL, `/api/projects/${projectId}/srt`));
  } catch {
    throw new ApiError(networkErrorMessage(API_BASE_URL));
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON responses fall back to the safe message.
    }
    throw new ApiError(extractDetail(body) ?? 'تعذر تنزيل ملف الترجمة.', response.status);
  }
  return response.blob();
}
export function apiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.';
}

export interface DubbingReadiness {
  ready: boolean;
  dubbed_video_available?: boolean;
  dubbed_video_version?: number | null;
  reasons: string[];
  generation_ready?: boolean;
  render_ready?: boolean;
  segments_total?: number;
  segments_ready?: number;
  total_segments?: number;
  ready_segments?: number;
  passthrough_segments?: number;
  tts_required_segments?: number;
  generated_tts_segments?: number;
  approved_tts_segments?: number;
  blocking_reasons?: string[];
  generation_blocking_reasons?: string[];
  render_blocking_reasons?: string[];
  info_reasons?: string[];
}

export interface ReportSegment {
  segment_id: string;
  segment_index: number;
  start_time: number | null;
  end_time: number | null;
  original_text: string | null;
  final_translation: string | null;
  reference: string | null;
  score: number | null;
  verification_status: string | null;
  translation_source: string | null;
  translation_origin: string | null;
  hadith_grade: string | null;
  source_url: string | null;
  review_status: string | null;
  reason?: string | null;
  quran_suspected?: boolean;
}

export interface ValidationCheck {
  key: string;
  label: string;
  passed: boolean;
  detail: string | null;
  severity?: 'required' | 'warning';
}

export interface IntegrityReport {
  project_id: string;
  total_segments: number;
  synthesized_segments: number;
  original_audio_segments: number;
  religious_segments: number;
  approved_audio_segments: number;
  ready_for_dubbing: boolean;
  dubbed_video_available: boolean;
  ai_generated_audio_notice: string;
  quran_sent_to_tts?: number;
  project?: {
    title: string | null;
    status: string | null;
    dubbing_mode: string | null;
    source_language: string | null;
    target_language: string | null;
    duration_seconds: number | null;
    created_at: string | null;
    srt_available: boolean;
  };
  content_counts?: Record<'quran' | 'hadith' | 'general' | 'uncertain', number>;
  quran_summary?: { count: number; verified: number; original_audio_preserved: number; items: ReportSegment[] };
  hadith_summary?: {
    count: number; verified: number; official_translations: number; ai_drafts: number; items: ReportSegment[];
  };
  uncertain_segments?: ReportSegment[];
  dubbing?: {
    generation_ready: boolean;
    render_ready: boolean;
    tts_required_segments: number;
    generated_tts_segments: number;
    approved_tts_segments: number;
    passthrough_segments: number;
    generation_blocking_reasons: string[];
    render_blocking_reasons: string[];
    warning_reasons?: string[];
  };
  validation?: { passed: boolean; checks: ValidationCheck[] };
}

export const AI_AUDIO_NOTICE = 'هذا الصوت مُولَّد بالذكاء الاصطناعي. النصوص القرآنية تُحفَظ بصوتها الأصلي ولا يُعاد توليدها.';

export async function getDubbingReadiness(projectId: string): Promise<DubbingReadiness> {
  const payload = await request<DubbingReadiness>(`/api/projects/${projectId}/dubbing-readiness`);
  const normalizedReasons = payload.generation_blocking_reasons
    ?? payload.reasons
    ?? payload.blocking_reasons
    ?? [];
  return {
    ...payload,
    reasons: normalizedReasons,
    generation_blocking_reasons: payload.generation_blocking_reasons ?? normalizedReasons,
    render_blocking_reasons: payload.render_blocking_reasons ?? [],
    info_reasons: payload.info_reasons ?? [],
  };
}

export async function generateDubbing(projectId: string, force = false): Promise<{ job_id: string }> {
  return request<{ job_id: string }>(`/api/projects/${projectId}/generate-dubbing${force ? '?force=true' : ''}`, { method: 'POST' });
}

export async function approveAllAudio(projectId: string): Promise<void> {
  await request(`/api/projects/${projectId}/approve-all-audio`, { method: 'POST' });
}

export async function approveAudioSegment(projectId: string, segmentId: string): Promise<void> {
  await request(`/api/projects/${projectId}/segments/${segmentId}/approve-audio`, { method: 'POST' });
}

export async function renderDubbedVideo(projectId: string): Promise<{ job_id: string }> {
  return request<{ job_id: string }>(`/api/projects/${projectId}/render-dubbed-video`, { method: 'POST' });
}

export async function getIntegrityReport(projectId: string): Promise<IntegrityReport> {
  return request<IntegrityReport>(`/api/projects/${projectId}/integrity-report`);
}

export function dubbedVideoUrl(projectId: string): string {
  return buildApiUrl(API_BASE_URL, `/api/projects/${projectId}/dubbed-video`);
}

export function dubbedVideoDownloadUrl(projectId: string): string {
  return `${dubbedVideoUrl(projectId)}?download=1`;
}

// Reads the file name from Content-Disposition (RFC 5987 filename* first, then filename).
export function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const encoded = header.match(/filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ''));
    } catch {
      // Fall through to the plain filename.
    }
  }
  const plain = header.match(/filename\s*=\s*"?([^";]+)"?/);
  return plain ? plain[1].trim() : fallback;
}

// Downloads the dubbed video as a file without leaving the current screen.
export async function downloadDubbedVideo(projectId: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch(dubbedVideoDownloadUrl(projectId));
  } catch {
    throw new ApiError(networkErrorMessage(API_BASE_URL));
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON responses fall back to the safe message.
    }
    throw new ApiError(extractDetail(body) ?? 'تعذر تنزيل الفيديو المدبلج.', response.status);
  }
  const filename = filenameFromDisposition(response.headers.get('Content-Disposition'), `${projectId}-dubbed.mp4`);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  return filename;
}

export function segmentAudioUrl(projectId: string, segmentId: string): string {
  return buildApiUrl(API_BASE_URL, `/api/projects/${projectId}/segments/${segmentId}/audio`);
}
export interface PipelineStatus {
  project: boolean;
  upload: boolean;
  transcription: boolean;
  review: boolean;
  verification: boolean;
  dubbing: boolean;
  report: boolean;
}

export async function getPipelineStatus(projectId: string): Promise<PipelineStatus> {
  return request<PipelineStatus>(`/api/projects/${projectId}/pipeline-status`);
}

export async function getSourcesStatus(): Promise<{ sources: boolean; approved_sources_count: number; documents_count: number; passages_count: number; chunks_count: number }> {
  return request<Awaited<ReturnType<typeof getSourcesStatus>>>('/api/pipeline/sources-status');
}

export interface RecoveredSourceItem {
  id: string;
  type: string;
  source: string;
  reference: string | null;
  section?: string | null;
  segment_id?: string | null;
  confidence: number;
  full_text: string;
  status: 'recovered' | 'candidate' | 'approved' | 'rejected';
}

export interface RecoverSourcesResult {
  threshold: number;
  recovered: RecoveredSourceItem[];
  candidates: RecoveredSourceItem[];
  detected_count: number;
}

export async function recoverSources(projectId: string): Promise<RecoverSourcesResult> {
  return request<RecoverSourcesResult>(`/api/projects/${projectId}/recover-sources`, { method: 'POST' });
}

export async function getRecoveredSources(projectId: string): Promise<RecoveredSourceItem[]> {
  return request<RecoveredSourceItem[]>(`/api/projects/${projectId}/recovered-sources`);
}

export async function reviewRecoveredSource(
  projectId: string,
  recoveredId: string,
  decision: 'approved' | 'rejected',
  reviewedBy: string,
): Promise<RecoveredSourceItem> {
  return request<RecoveredSourceItem>(`/api/projects/${projectId}/recovered-sources/${recoveredId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reviewed_by: reviewedBy }),
  });
}
