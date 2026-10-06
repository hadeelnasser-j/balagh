import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, MESSAGES, buildApiUrl, getHealth, unavailableServices, type HealthStatus } from './api';

const ready: HealthStatus = {
  status: 'healthy', supabase: 'available', ffmpeg: 'available', ffprobe: 'available',
  transcription_provider: 'openai', translation_provider: 'openai',
  openai_configured: true,
};

afterEach(() => vi.unstubAllGlobals());

describe('buildApiUrl', () => {
  it('does not duplicate slashes or /api', () => {
    expect(buildApiUrl('http://localhost:8000/', '/api/projects')).toBe('http://localhost:8000/api/projects');
    expect(buildApiUrl('http://localhost:8000/api', '/api/projects')).toBe('http://localhost:8000/api/projects');
    expect(buildApiUrl('http://localhost:8000', 'api/projects')).toBe('http://localhost:8000/api/projects');
  });
  it('throws an Arabic ApiError when the base URL is empty', () => {
    expect(() => buildApiUrl('', '/api/health')).toThrow(ApiError);
    expect(() => buildApiUrl(undefined, '/api/health')).toThrow(MESSAGES.missingBase);
  });
});

describe('unavailableServices', () => {
  it('is empty when OpenAI is configured and core services are ready', () => {
    expect(unavailableServices(ready)).toEqual([]);
  });
  it('reports supabase, ffmpeg and OpenAI problems', () => {
    expect(unavailableServices({ ...ready, supabase: 'unavailable' })).toContain(MESSAGES.supabase);
    expect(unavailableServices({ ...ready, ffprobe: 'unavailable' })).toContain(MESSAGES.ffmpeg);
    expect(unavailableServices({ ...ready, openai_configured: false })).toContain('مفتاح OpenAI غير مضبوط على الخادم.');
  });
});

describe('request error handling', () => {
  it('maps network errors to an Arabic message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(getHealth()).rejects.toThrow(MESSAGES.network);
  });
  it('shows the backend Arabic message or detail from JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'المشروع غير موجود.' }), { status: 404 })));
    await expect(getHealth()).rejects.toThrow('المشروع غير موجود.');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: 'رسالة' }), { status: 400 })));
    await expect(getHealth()).rejects.toThrow('رسالة');
  });
});
