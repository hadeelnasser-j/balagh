import React, { useState, useRef } from 'react';
import { UploadCloud, Film, AlertCircle, FileCheck } from 'lucide-react';
import { MAX_FILE_SIZE_BYTES, MAX_DURATION_SECONDS, ALLOWED_EXTENSIONS } from '../utils/formatters';
import { VideoMetadata, UploadErrorInfo } from '../types';

interface VideoUploaderProps {
  onVideoSelected: (metadata: VideoMetadata) => void;
  onError: (error: UploadErrorInfo) => void;
  isProcessing?: boolean;
  onUseSampleVideo?: () => void;
}

export const VideoUploader: React.FC<VideoUploaderProps> = ({
  onVideoSelected,
  onError,
  isProcessing = false,
  onUseSampleVideo,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndProcessFile = (file: File) => {
    // 1. Check file extension / type
    const lowerName = file.name.toLowerCase();
    const isSupportedExtension = ALLOWED_EXTENSIONS.some(ext => lowerName.endsWith(ext));
    const isSupportedMime = file.type === 'video/mp4' || file.type === 'video/quicktime' || file.type.startsWith('video/');

    if (!isSupportedExtension && !isSupportedMime) {
      onError({
        type: 'INVALID_FORMAT',
        title: 'صيغة الملف غير مدعومة',
        message: 'عذراً، تدعم المنصة حالياً ملفات الفيديو بصيغتي MP4 و MOV فقط.',
        canRetry: false,
      });
      return;
    }

    // 2. Check file size (20 MB limit)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      onError({
        type: 'FILE_TOO_LARGE',
        title: 'حجم الملف يتجاوز الحد المسموح',
        message: 'حجم الفيديو المختار أكبر من 20 ميجابايت (الحد الأقصى في النسخة التجريبية). يُرجى اختيار ملف أصغر حجماً.',
        canRetry: false,
      });
      return;
    }

    // 3. Inspect video duration
    setIsValidating(true);
    const videoObjectUrl = URL.createObjectURL(file);
    const tempVideo = document.createElement('video');
    tempVideo.preload = 'metadata';

    tempVideo.onloadedmetadata = () => {
      const duration = tempVideo.duration;
      // Check 1-minute limit (allow 1s tolerance for rounding)
      if (duration > MAX_DURATION_SECONDS + 1) {
        URL.revokeObjectURL(videoObjectUrl);
        setIsValidating(false);
        onError({
          type: 'DURATION_EXCEEDED',
          title: 'مدة الفيديو أطول من المسموح',
          message: 'مدة الفيديو تتجاوز دقيقة واحدة (الحد الأقصى المسموح به تجريبياً). يُرجى رفع مقطع مدته دقيقة أو أقل.',
          canRetry: false,
        });
        return;
      }

      // Valid video!
      setIsValidating(false);
      onVideoSelected({
        file,
        name: file.name,
        sizeBytes: file.size,
        durationSeconds: duration,
        previewUrl: videoObjectUrl,
      });
    };

    tempVideo.onerror = () => {
      URL.revokeObjectURL(videoObjectUrl);
      setIsValidating(false);
      onError({
        type: 'UPLOAD_FAILED',
        title: 'تعذر قراءة ملف الفيديو',
        message: 'حدث خطأ أثناء فحص ملف الفيديو. يُرجى التأكد من سلامة الملف وإعادة المحاولة.',
        canRetry: true,
      });
    };

    tempVideo.src = videoObjectUrl;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndProcessFile(droppedFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      validateAndProcessFile(selectedFile);
    }
    // reset input so the same file can be re-selected if replaced
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept=".mp4,.mov,video/mp4,video/quicktime"
        className="hidden"
        onChange={handleFileChange}
        disabled={isProcessing || isValidating}
      />

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`group relative w-full rounded-2xl border-2 border-dashed transition-all duration-300 p-8 sm:p-12 flex flex-col items-center justify-center text-center cursor-pointer ${
          isDragging
            ? 'border-brand-500 bg-brand-50/60 scale-[1.005] shadow-lg ring-4 ring-brand-100'
            : 'border-slate-300 hover:border-brand-400 bg-white hover:bg-slate-50/50 shadow-subtle'
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        {/* Visual Glow Backdrop */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-brand-50/20 to-transparent pointer-events-none" />

        {/* Center Icon */}
        <div className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 mb-6 shadow-sm ${
          isDragging
            ? 'bg-brand-600 text-white scale-110'
            : 'bg-brand-50 text-brand-700 group-hover:bg-brand-100 group-hover:scale-105'
        }`}>
          {isValidating ? (
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-600 border-t-transparent" />
          ) : (
            <UploadCloud className="w-10 h-10" />
          )}
        </div>

        {/* Primary and secondary text */}
        <h2 className="text-xl sm:text-2xl font-bold text-slate-800 mb-2">
          ارفع الفيديو للبدء
        </h2>

        <p className="text-sm text-slate-500 max-w-md mb-6 leading-relaxed">
          اسحب الفيديو هنا أو اختر ملفًا من جهازك
        </p>

        {/* Upload Button */}
        <button
          type="button"
          disabled={isProcessing || isValidating}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-800 hover:bg-brand-700 text-white font-medium text-sm transition-all duration-200 shadow-sm hover:shadow active:scale-98"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          <Film className="w-4 h-4 text-brand-200" />
          <span>اختيار فيديو</span>
        </button>

        {onUseSampleVideo && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onUseSampleVideo();
            }}
            className="mt-3 text-xs text-brand-700 hover:text-brand-800 font-medium underline underline-offset-4 transition-colors"
          >
            أو جرّب مقطعاً نموذجياً جاهزاً (درس_تفسير.mp4)
          </button>
        )}

        {/* Limits & Formats Footer */}
        <div className="mt-8 pt-6 border-t border-slate-100 w-full max-w-lg flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <FileCheck className="w-3.5 h-3.5 text-brand-600" />
            <span>الصيغ المدعومة: <strong className="text-slate-600">MP4, MOV</strong></span>
          </div>

          <span className="text-slate-300">•</span>

          <div className="flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-brand-600" />
            <span>الحد الأقصى للحجم: <strong className="text-slate-600">20 ميجابايت</strong></span>
          </div>

          <span className="text-slate-300">•</span>

          <div className="flex items-center gap-1.5">
            <span>المدة التجريبية: <strong className="text-slate-600">دقيقة واحدة</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};
