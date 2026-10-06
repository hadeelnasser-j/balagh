export const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB
export const MAX_DURATION_SECONDS = 60; // 1 minute (60 seconds)
export const ALLOWED_EXTENSIONS = ['.mp4', '.mov'];

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 ميجابايت';
  const k = 1024;
  const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = parseFloat((bytes / Math.pow(k, i)).toFixed(1));
  return `${val} ${sizes[i]}`;
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const formattedSecs = secs < 10 ? `0${secs}` : `${secs}`;
  const formattedMins = mins < 10 ? `0${mins}` : `${mins}`;
  return `${formattedMins}:${formattedSecs} دقيقة`;
}
