import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  EMPTY_STATUS,
  WIZARD_STEPS,
  canGoNext,
  canNavigate,
  firstIncompleteStep,
  guardStep,
  loadStoredStatus,
  mergeStatus,
  normalizeStatus,
  saveStoredStatus,
  stepState,
} from './wizard';
import { getPipelineStatus } from '../services/api';

function stubStorage() {
  const store = new Map<string, string>();
  vi.stubGlobal('window', {
    localStorage: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    },
  });
}

describe('wizard logic', () => {
  beforeEach(stubStorage);
  afterEach(() => vi.unstubAllGlobals());

  it('gates steps sequentially', () => {
    const status = normalizeStatus({ project: false, upload: true });
    expect(status.upload).toBe(false);
    expect(firstIncompleteStep(status)).toBe('project');
  });

  it('redirects future steps to the first incomplete step', () => {
    const status = normalizeStatus({ project: true });
    expect(guardStep(status, 'review')).toBe('upload');
    expect(guardStep(status, 'project')).toBe('project');
    expect(canNavigate(status, 'upload')).toBe(true);
    expect(canNavigate(status, 'dubbing')).toBe(false);
  });

  it('computes step states', () => {
    const status = normalizeStatus({ project: true });
    expect(stepState(status, 'project', 'upload')).toBe('completed');
    expect(stepState(status, 'upload', 'upload')).toBe('current');
    expect(stepState(status, 'review', 'upload')).toBe('locked');
  });

  it('disables Next until the current step is complete', () => {
    expect(canGoNext(EMPTY_STATUS, 'project')).toBe(false);
    expect(canGoNext(normalizeStatus({ project: true }), 'project')).toBe(true);
    expect(canGoNext(normalizeStatus({ project: true, upload: true, transcription: true, review: true, verification: true, dubbing: true, report: true }), 'report')).toBe(false);
  });

  it('exposes exactly 6 visible wizard steps', () => {
    expect(WIZARD_STEPS).toEqual([
      'project',
      'upload',
      'transcription',
      'review',
      'dubbing',
      'report',
    ]);
    expect(WIZARD_STEPS).toHaveLength(6);
  });

  it('persists to local storage and prefers backend status', () => {
    saveStoredStatus('p1', normalizeStatus({ project: true }));
    expect(loadStoredStatus('p1').project).toBe(true);
    expect(loadStoredStatus('p2').project).toBe(false);
    const local = loadStoredStatus('p1');
    expect(mergeStatus(local, null).project).toBe(true);
    expect(mergeStatus(local, EMPTY_STATUS).project).toBe(false);
  });
});

describe('getPipelineStatus', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('requests the pipeline-status endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ...EMPTY_STATUS, project: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const result = await getPipelineStatus('abc');
    expect(result.project).toBe(true);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/projects/abc/pipeline-status');
  });
});
