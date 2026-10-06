import { describe, expect, it, vi, beforeEach } from 'vitest';
import { AI_AUDIO_NOTICE, buildApiUrl, dubbedVideoUrl, generateDubbing, getDubbingReadiness } from './api';

describe('dubbing api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('builds the dubbed video url without duplicating /api', () => {
    expect(dubbedVideoUrl('p1')).toMatch(/\/api\/projects\/p1\/dubbed-video$/);
    expect(dubbedVideoUrl('p1')).not.toContain('/api/api');
    expect(buildApiUrl('http://x:8000/', '/api/a')).toBe('http://x:8000/api/a');
  });

  it('shows the AI generated audio notice in Arabic', () => {
    expect(AI_AUDIO_NOTICE).toContain('الذكاء الاصطناعي');
  });

  it('reads readiness from the backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ready: false, reasons: ['no_segments'] }), { status: 200 })));
    const result = await getDubbingReadiness('p1');
    expect(result.ready).toBe(false);
  });

  it('passes force=true when regenerating', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ job_id: 'j' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await generateDubbing('p1', true);
    expect(String(fetchMock.mock.calls[0][0])).toContain('force=true');
  });

  it('maps a blocked response to the Arabic detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'غير جاهز' }), { status: 409 })));
    await expect(generateDubbing('p1')).rejects.toThrow('غير جاهز');
  });
});

describe('dubbed video download', () => {
  it('reads UTF-8 and plain file names from Content-Disposition', async () => {
    const { filenameFromDisposition, dubbedVideoDownloadUrl } = await import('./api');
    expect(filenameFromDisposition("attachment; filename*=utf-8''BALAGH-%D8%AF%D8%B1%D8%B3-dubbed.mp4", 'x.mp4'))
      .toBe('BALAGH-درس-dubbed.mp4');
    expect(filenameFromDisposition('attachment; filename="BALAGH-lesson-dubbed.mp4"', 'x.mp4')).toBe('BALAGH-lesson-dubbed.mp4');
    expect(filenameFromDisposition(null, 'fallback.mp4')).toBe('fallback.mp4');
    expect(dubbedVideoDownloadUrl('p1')).toMatch(/\/api\/projects\/p1\/dubbed-video\?download=1$/);
  });

  it('maps a missing video to the Arabic detail without navigating', async () => {
    const { downloadDubbedVideo } = await import('./api');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'لم يُنشأ الفيديو المدبلج بعد.' }), { status: 404 })));
    await expect(downloadDubbedVideo('p1')).rejects.toThrow('لم يُنشأ الفيديو المدبلج بعد.');
  });
});
