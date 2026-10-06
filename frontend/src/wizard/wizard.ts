import type { PipelineStatus } from '../services/api';

export type WizardStep = keyof PipelineStatus;

const INTERNAL_STEPS: WizardStep[] = [
  'project',
  'upload',
  'transcription',
  'review',
  'verification',
  'dubbing',
  'report',
];

export const WIZARD_STEPS: WizardStep[] = [
  'project',
  'upload',
  'transcription',
  'review',
  'dubbing',
  'report',
];

export const STEP_LABELS: Record<WizardStep, string> = {
  project: 'بدء المشروع',
  upload: 'الرفع',
  transcription: 'التفريغ',
  review: 'المراجعة والتحقق',
  verification: 'التحقق',
  dubbing: 'الدبلجة',
  report: 'التقرير',
};

export type StepState = 'completed' | 'current' | 'locked' | 'available';

export const EMPTY_STATUS: PipelineStatus = {
  project: false,
  upload: false,
  transcription: false,
  review: false,
  verification: false,
  dubbing: false,
  report: false,
};

function visibleComplete(status: PipelineStatus, step: WizardStep): boolean {
  if (step === 'review') return status.review && status.verification;
  return status[step];
}

// Enforce sequential gating: a step counts as complete only if all earlier steps are.
export function normalizeStatus(status: Partial<PipelineStatus>): PipelineStatus {
  const result = { ...EMPTY_STATUS };
  let previousDone = true;
  for (const step of INTERNAL_STEPS) {
    previousDone = previousDone && Boolean(status[step]);
    result[step] = previousDone;
  }
  return result;
}

export function firstIncompleteStep(status: PipelineStatus): WizardStep {
  const normalized = normalizeStatus(status);
  return WIZARD_STEPS.find((step) => !visibleComplete(normalized, step)) ?? 'report';
}

export function canNavigate(status: PipelineStatus, target: WizardStep): boolean {
  const normalized = normalizeStatus(status);
  const targetIndex = WIZARD_STEPS.indexOf(target);
  return targetIndex <= WIZARD_STEPS.indexOf(firstIncompleteStep(normalized)) &&
    WIZARD_STEPS.slice(0, targetIndex).every((step) => visibleComplete(normalized, step));
}

// Redirect target for a requested step: itself when reachable, otherwise the first incomplete step.
export function guardStep(status: PipelineStatus, requested: WizardStep): WizardStep {
  return canNavigate(status, requested) ? requested : firstIncompleteStep(status);
}

export function stepState(status: PipelineStatus, step: WizardStep, current: WizardStep): StepState {
  if (step === current) return 'current';
  if (visibleComplete(normalizeStatus(status), step)) return 'completed';
  return canNavigate(status, step) ? 'available' : 'locked';
}

export function previousStep(step: WizardStep): WizardStep | null {
  const index = WIZARD_STEPS.indexOf(step);
  return index > 0 ? WIZARD_STEPS[index - 1] : null;
}

export function nextStep(step: WizardStep): WizardStep | null {
  const index = WIZARD_STEPS.indexOf(step);
  return index < WIZARD_STEPS.length - 1 ? WIZARD_STEPS[index + 1] : null;
}

export function canGoNext(status: PipelineStatus, current: WizardStep): boolean {
  const next = nextStep(current);
  return next !== null && normalizeStatus(status)[current];
}

const STORAGE_PREFIX = 'balagh.wizard.';

function storageKey(projectId: string | null): string {
  return `${STORAGE_PREFIX}${projectId ?? 'draft'}`;
}

export function loadStoredStatus(projectId: string | null): PipelineStatus {
  try {
    const raw = window.localStorage.getItem(storageKey(projectId));
    return raw ? normalizeStatus(JSON.parse(raw) as Partial<PipelineStatus>) : { ...EMPTY_STATUS };
  } catch {
    return { ...EMPTY_STATUS };
  }
}

export function saveStoredStatus(projectId: string | null, status: PipelineStatus): void {
  try {
    window.localStorage.setItem(storageKey(projectId), JSON.stringify(normalizeStatus(status)));
  } catch {
    // Storage may be unavailable; the backend remains the source of truth.
  }
}

// Backend wins over local storage; local storage only fills in while the backend is unreachable.
export function mergeStatus(local: PipelineStatus, remote: PipelineStatus | null): PipelineStatus {
  return normalizeStatus(remote ?? local);
}
