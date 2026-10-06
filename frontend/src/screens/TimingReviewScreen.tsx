import React, { useState } from 'react';
import { InteractiveTimelineBar } from '../components/timing/InteractiveTimelineBar';
import { TimingSummaryCard } from '../components/timing/TimingSummaryCard';
import { VideoDubbingPlayer } from '../components/timing/VideoDubbingPlayer';
import { TranslationSegmentCard } from '../components/timing/TranslationSegmentCard';
import { ExportSuccessModal } from '../components/timing/ExportSuccessModal';
import { HighRiskWarningBanner } from '../components/review/HighRiskWarningBanner';
import { 
  TranslationSegment, 
  VideoMetadata, 
  DubbingMode, 
  AudioTrackOption, 
  DubbingPacing 
} from '../types';
import { 
  ArrowRight, 
  Download, 
  ShieldCheck
} from 'lucide-react';

interface TimingReviewScreenProps {
  video: VideoMetadata;
  dubbingMode: DubbingMode;
  onBackToReview: () => void;
  onBackToHome: () => void;
}

// Initial Translation Segments based on the transcribed text from Screen 3
const INITIAL_TRANSLATION_SEGMENTS: TranslationSegment[] = [
  {
    id: 'trans_1',
    arabicText: 'الحمد لله والصلاة والسلام على رسول الله، نتحدث اليوم عن فريضة الزكاة ومكانتها في الإسلام.',
    timestamp: '00:00 - 00:14',
    englishTranslation: 'Praise be to Allah, and peace and blessings be upon the Messenger of Allah. Today we discuss the obligatory Zakat and its status in Islam.',
    sourceDurationSec: 14.0,
    translatedDurationSec: 14.2,
    durationDifferencePercent: 1.4,
    timingStatus: 'suitable',
    isMeaningPreserved: true,
    isApproved: true,
  },
  {
    id: 'trans_2',
    arabicText: 'والزكاة عبادة مالية واجبة ترتبط بشروط محددة كالنصاب والحول، وتختلف تماماً عن الصدقة التطوعية.',
    timestamp: '00:14 - 00:32',
    englishTranslation: 'Zakat is an obligatory financial act of worship tied to specific conditions such as Nisab and Hawl, and it differs completely from voluntary charity (Sadaqah).',
    shorterAlternative: 'Zakat is an obligatory worship with set conditions like Nisab, unlike voluntary Sadaqah.',
    sourceDurationSec: 18.0,
    translatedDurationSec: 21.6,
    durationDifferencePercent: 20.0,
    timingStatus: 'needs_improvement',
    isMeaningPreserved: true,
    isApproved: false,
  },
  {
    id: 'trans_3',
    arabicText: 'فلا يُكتفى بمجرد التبرع، بل يُشترط إيصالها لمصارفها الشرعية الثمانية المحددة في كتاب الله.',
    timestamp: '00:32 - 00:48',
    englishTranslation: 'It is not sufficient merely to donate; rather, it must be directed to its eight legitimate categories ordained in the Book of Allah.',
    sourceDurationSec: 16.0,
    translatedDurationSec: 16.4,
    durationDifferencePercent: 2.5,
    timingStatus: 'suitable',
    isMeaningPreserved: true,
    isApproved: true,
  },
];

export const TimingReviewScreen: React.FC<TimingReviewScreenProps> = ({
  video,
  dubbingMode,
  onBackToReview,
  onBackToHome,
}) => {
  const [segments, setSegments] = useState<TranslationSegment[]>(INITIAL_TRANSLATION_SEGMENTS);
  const [activeSegmentId, setActiveSegmentId] = useState<string>('trans_2');
  const [activePlayingAudioId, setActivePlayingAudioId] = useState<string | null>(null);
  const [audioTrack, setAudioTrack] = useState<AudioTrackOption>('dubbed');
  const [showSubtitles, setShowSubtitles] = useState<boolean>(true);
  const [pacing, setPacing] = useState<DubbingPacing>('natural_fast');
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [meaningViolationWarning, setMeaningViolationWarning] = useState<string | null>(null);

  const activeSegment = segments.find((s) => s.id === activeSegmentId) || segments[0];
  const approvedCount = segments.filter((s) => s.isApproved).length;
  const hasViolations = segments.some((s) => !s.isMeaningPreserved);

  // Play audio simulation
  const handlePlayAudio = (segmentId: string) => {
    if (activePlayingAudioId === segmentId) {
      setActivePlayingAudioId(null);
    } else {
      setActivePlayingAudioId(segmentId);
      setActiveSegmentId(segmentId);
    }
  };

  // Update English Translation and check Meaning Lock
  const handleUpdateTranslation = (segmentId: string, newEnglishText: string) => {
    // If Segment 2 is modified and difference between Zakat and Sadaqah is removed
    let preserved = true;
    let missingText: string | undefined = undefined;

    if (segmentId === 'trans_2') {
      const lower = newEnglishText.toLowerCase();
      const hasDiff = lower.includes('differs') || lower.includes('unlike') || lower.includes('voluntary') || lower.includes('sadaqah');
      if (!hasDiff) {
        preserved = false;
        missingText = 'حُذف التمييز بين فريضة الزكاة وصدقة التطوع في الترجمة الإنجليزية.';
        setMeaningViolationWarning('تم حذف تفريق الزكاة عن الصدقة التطوعية. يلزم الحفاظ على هذا المعنى الشرعي لاعتماد الدبلجة.');
      } else {
        setMeaningViolationWarning(null);
      }
    }

    setSegments((prev) =>
      prev.map((seg) => {
        if (seg.id !== segmentId) return seg;

        // Recalculate duration roughly based on word count
        const wordCount = newEnglishText.trim().split(/\s+/).length;
        const estDuration = Math.max(8, Number((wordCount * 0.42).toFixed(1)));
        const diffPercent = Number((((estDuration - seg.sourceDurationSec) / seg.sourceDurationSec) * 100).toFixed(1));
        const newStatus = Math.abs(diffPercent) <= 5 ? 'suitable' : Math.abs(diffPercent) <= 15 ? 'needs_improvement' : 'needs_adjustment';

        return {
          ...seg,
          englishTranslation: newEnglishText,
          translatedDurationSec: estDuration,
          durationDifferencePercent: diffPercent,
          timingStatus: newStatus,
          isMeaningPreserved: preserved,
          missingMeaningText: missingText,
          isApproved: preserved && newStatus === 'suitable',
        };
      })
    );
  };

  // Apply Shorter Alternative (Key Feature)
  const handleApplyShorterAlternative = (segmentId: string) => {
    setSegments((prev) =>
      prev.map((seg) => {
        if (seg.id !== segmentId || !seg.shorterAlternative) return seg;

        return {
          ...seg,
          englishTranslation: seg.shorterAlternative,
          translatedDurationSec: 18.2,
          durationDifferencePercent: 1.1,
          timingStatus: 'suitable',
          isMeaningPreserved: true,
          missingMeaningText: undefined,
          isApproved: true,
        };
      })
    );
    setMeaningViolationWarning(null);
  };

  // Restore meaning if violated
  const handleRestoreMeaning = () => {
    setSegments((prev) =>
      prev.map((seg) =>
        seg.id === 'trans_2' ? { ...INITIAL_TRANSLATION_SEGMENTS[1], isApproved: true } : seg
      )
    );
    setMeaningViolationWarning(null);
  };

  // Smart Re-generate
  const handleRegenerate = (segmentId: string) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === segmentId ? { ...s, isRegenerating: true } : s))
    );

    setTimeout(() => {
      setSegments((prev) =>
        prev.map((s) => {
          if (s.id !== segmentId) return s;
          if (segmentId === 'trans_2') {
            return {
              ...s,
              englishTranslation: s.shorterAlternative || s.englishTranslation,
              translatedDurationSec: 18.2,
              durationDifferencePercent: 1.1,
              timingStatus: 'suitable',
              isMeaningPreserved: true,
              isApproved: true,
              isRegenerating: false,
            };
          }
          return {
            ...s,
            isRegenerating: false,
            isApproved: true,
          };
        })
      );
    }, 1000);
  };

  // Toggle Segment Approval
  const handleToggleApproval = (segmentId: string) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === segmentId ? { ...s, isApproved: !s.isApproved } : s))
    );
  };

  // Global Approve & Open Export Dialog
  const handleApproveAllAndExport = () => {
    if (hasViolations) return;
    // Mark all as approved
    setSegments((prev) => prev.map((s) => ({ ...s, isApproved: true })));
    setIsExportModalOpen(true);
  };

  return (
    <div className="flex min-h-[calc(100vh-180px)] flex-col selection:bg-brand-100 selection:text-brand-900">
      
      {/* 1. Global Header */}

      {/* 2. Top Bar & Breadcrumb */}
      <div className="w-full border-b border-slate-200/80 bg-white py-3.5 px-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4">
          
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <button
              type="button"
              onClick={onBackToHome}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium p-1.5 rounded-lg hover:bg-slate-100"
            >
              <ArrowRight className="w-4 h-4" />
              <span>الرئيسية</span>
            </button>

            <span className="text-slate-300">/</span>

            <button
              type="button"
              onClick={onBackToReview}
              className="text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium p-1.5 rounded-lg hover:bg-slate-100"
            >
              مراجعة المصطلحات (الشاشة 3)
            </button>

            <span className="text-slate-300">/</span>

            <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
              <span>مراجعة الترجمة والمطابقة الزمنية</span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-800 border border-brand-200/70">
                الشاشة 4
              </span>
            </h2>
          </div>

          {/* Top Actions: Mode + Status Counter + Primary Export CTA */}
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-block text-xs text-slate-500 font-medium">
              المقاطع المعتمدة: <strong className="text-brand-900 font-bold">{approvedCount} من {segments.length}</strong>
            </span>

            <button
              type="button"
              disabled={hasViolations}
              onClick={handleApproveAllAndExport}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold shadow-sm transition-all ${
                hasViolations
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-200'
                  : 'bg-brand-800 hover:bg-brand-700 text-white cursor-pointer active:scale-98 shadow-brand-900/10'
              }`}
            >
              <Download className="w-4 h-4 text-amber-300" />
              <span>اعتماد التوقيت وتصدير الفيديو</span>
            </button>
          </div>

        </div>
      </div>

      {/* 3. Main Workspace: Two-Column Responsive Layout (1440 × 900 Optimized) */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        
        {/* High Risk Warning Banner if Meaning Lock was violated in translation */}
        {hasViolations && (
          <div className="mb-6">
            <HighRiskWarningBanner
              message={meaningViolationWarning || 'حُذف المعنى المحمي في الترجمة الإنجليزية. لا يمكن اعتماد التوقيت وتصدير الفيديو قبل إعادة المعنى.'}
              onRestore={handleRestoreMeaning}
            />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
          
          {/* ========================================================
              RIGHT SIDE (الجانب الأيمن): Video Player + Dubbing Metrics
              ======================================================== */}
          <div className="lg:col-span-5 space-y-6 order-1 lg:order-1">
            
            {/* 1. Video Dubbing Player */}
            <VideoDubbingPlayer
              video={video}
              activeSegment={activeSegment}
              audioTrack={audioTrack}
              onChangeAudioTrack={setAudioTrack}
              showSubtitles={showSubtitles}
              onToggleSubtitles={() => setShowSubtitles((prev) => !prev)}
            />

            {/* 2. Timing Summary & Pacing Metrics Card */}
            <TimingSummaryCard
              segments={segments}
              dubbingMode={dubbingMode}
              pacing={pacing}
              onChangePacing={setPacing}
            />

          </div>

          {/* ========================================================
              LEFT SIDE (الجانب الأيسر): Timeline + Translation Segments
              ======================================================== */}
          <div className="lg:col-span-7 space-y-5 order-2 lg:order-2">
            
            {/* 1. Interactive Visual Timeline Bar */}
            <InteractiveTimelineBar
              segments={segments}
              activeSegmentId={activeSegmentId}
              onSelectSegment={setActiveSegmentId}
              totalDurationSec={48}
            />

            {/* 2. Translation Segments Header */}
            <div className="flex items-center justify-between px-1">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  مقاطع الترجمة والتزامن الصوتي
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  قارن أوقات الحديث، واختر البدائل الأقصر عند تجاوز زمن المقطع الأصلي
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700">
                  {segments.length} مقاطع
                </span>
              </div>
            </div>

            {/* 3. Translation Segments Cards List */}
            <div className="space-y-4">
              {segments.map((segment) => (
                <TranslationSegmentCard
                  key={segment.id}
                  segment={segment}
                  isPlaying={activePlayingAudioId === segment.id}
                  isSelected={activeSegmentId === segment.id}
                  onPlay={handlePlayAudio}
                  onSelect={setActiveSegmentId}
                  onUpdateTranslation={handleUpdateTranslation}
                  onApplyShorterAlternative={handleApplyShorterAlternative}
                  onRegenerate={handleRegenerate}
                  onToggleApproval={handleToggleApproval}
                />
              ))}
            </div>

            {/* Bottom Reminder Banner */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-brand-700 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                تقوم خوارزميات بلاغ بتطابق زمن مخارج الحروف بين العربية والإنجليزية لضمان عدم وجود سكتات صوتية غير مبررة، مع حماية المعاني العقدية والمصطلحات المعتمدة في الشاشة السابقة.
              </p>
            </div>

            {/* Return to screen 3 navigation button */}
            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={onBackToReview}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-bold transition-all"
              >
                <ArrowRight className="w-4 h-4" />
                <span>العودة إلى مراجعة المصطلحات (الشاشة 3)</span>
              </button>

              <button
                type="button"
                disabled={hasViolations}
                onClick={handleApproveAllAndExport}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-800 hover:bg-brand-700 text-white text-xs font-bold shadow-premium transition-all active:scale-98"
              >
                <span>اعتماد التوقيت وتصدير الفيديو المدبلج</span>
                <Download className="w-4 h-4 text-amber-300" />
              </button>
            </div>

          </div>

        </div>

      </main>

      {/* Export Success Modal Dialog */}
      <ExportSuccessModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        onBackToHome={onBackToHome}
        videoName={video.name}
      />

      {/* Footer */}
      <footer className="w-full py-6 mt-auto border-t border-slate-200/60 bg-white/40 text-center text-xs text-slate-400">
        <p>منصة بلاغ (BALAGH) — دبلجة ذكية واعية بالسياق والمصطلحات الإسلامية © 2026</p>
      </footer>

    </div>
  );
};
