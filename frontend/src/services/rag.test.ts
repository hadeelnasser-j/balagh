import { afterEach, describe, expect, it, vi } from 'vitest';
import { generateSrt, reviewSourceMatch, getSourceSummary } from './api';

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe('RAG api calls', () => {
  it('sends the SRT mode as a query parameter', async () => {
    const fetchMock = stubFetch(200, { srt_storage_path: 'p' });
    await generateSrt('abc', 'final');
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/projects/abc/generate-srt');
    expect(String(fetchMock.mock.calls[0][0])).toContain('mode=final');
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('/api/api/');
  });

  it('posts the reviewer name when approving a match', async () => {
    const fetchMock = stubFetch(200, { id: 'm1' });
    await reviewSourceMatch('seg', 'm1', 'approve', 'Reviewer');
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/segments/seg/source-matches/m1/approve');
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toEqual({ reviewed_by: 'Reviewer' });
  });

  it('shows the backend Arabic detail on errors', async () => {
    stubFetch(409, { detail: 'لا يمكن إنشاء SRT نهائي.' });
    await expect(getSourceSummary('x')).rejects.toThrow('لا يمكن إنشاء SRT نهائي.');
  });
});
