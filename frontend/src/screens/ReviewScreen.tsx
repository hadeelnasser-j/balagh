import React, { useState } from 'react';
import { TranscriptSegmentCard } from '../components/review/TranscriptSegmentCard';
import { TerminologyCard } from '../components/review/TerminologyCard';
import { MeaningLockSection } from '../components/review/MeaningLockSection';
import { HighRiskWarningBanner } from '../components/review/HighRiskWarningBanner';
import { TranscriptSegment, TerminologyItem, ProtectedMeaning, VideoMetadata, DubbingMode } from '../types';
import { Film, CheckCircle2, ArrowRight, ShieldCheck, Check, Sparkles, ArrowLeft } from 'lucide-react';

interface ReviewScreenProps {
  video: VideoMetadata;
  dubbingMode: DubbingMode;
  onBackToHome?: () => void;
  onNavigateToTimingReview?: () => void;
}

// Mock Transcript Segments
const INITIAL_SEGMENTS: TranscriptSegment[] = [
  {
    id: 'seg_1',
    startTime: '00:00',
    endTime: '00:14',
    text: 'الحمد لله والصلاة والسلام على رسول الله، نتحدث اليوم عن فريضة الزكاة ومكانتها في الإسلام.',
    confidence: 'high',
    confidencePercent: 98,
  },
  {
    id: 'seg_2',
    startTime: '00:14',
    endTime: '00:32',
    text: 'والزكاة عبادة مالية واجبة ترتبط بشروط محددة كالنصاب والحول، وتختلف تماماً عن الصدقة التطوعية.',
    confidence: 'high',
    confidencePercent: 95,
  },
  {
    id: 'seg_3',
    startTime: '00:32',
    endTime: '00:48',
    text: 'فلا يُكتفى بمجرد التبرع، بل يُشترط إيصالها لمصارفها الشرعية الثمانية المحددة في كتاب الله.',
    confidence: 'medium',
    confidencePercent: 86,
  },
];

// Mock Terminology (Exact requirements from prompt)
const INITIAL_TERMS: TerminologyItem[] = [
  {
    id: 'term_zakat',
    term: 'الزكاة',
    approvedEquivalent: 'Zakat',
    definition: 'عبادة مالية واجبة بشروط محددة',
    confidencePercent: 95,
    riskLevel: 'مرتفعة',
    reviewStatus: 'مطلوبة',
    source: 'قاموس المصطلحات المعتمد',
    status: 'pending',
  },
  {
    id: 'term_sadaqah',
    term: 'الصدقة التطوعية',
    approvedEquivalent: 'Voluntary Charity (Sadaqah)',
    definition: 'بذل المال تطوعاً وتقرباً دون اشتراط نصاب أو حول',
    confidencePercent: 92,
    riskLevel: 'متوسطة',
    reviewStatus: 'تمت',
    source: 'قاموس المصطلحات المعتمد',
    status: 'approved',
  },
];

// Mock Protected Meanings for Meaning Lock
const INITIAL_PROTECTED_MEANINGS: ProtectedMeaning[] = [
  {
    id: 'pm_1',
    text: 'الزكاة عبادة مالية واجبة',
    isViolated: false,
  },
  {
    id: 'pm_2',
    text: 'وجوبها مرتبط بشروط محددة',
    isViolated: false,
  },
  {
    id: 'pm_3',
    text: 'تختلف عن الصدقة التطوعية',
    isViolated: false,
  },
];

export const ReviewScreen: React.FC<ReviewScreenProps> = ({
  video,
  dubbingMode,
  onBackToHome,
  onNavigateToTimingReview,
}) => {
  const [segments, setSegments] = useState<TranscriptSegment[]>(INITIAL_SEGMENTS);
  const [terms, setTerms] = useState<TerminologyItem[]>(INITIAL_TERMS);
  const [protectedMeanings, setProtectedMeanings] = useState<ProtectedMeaning[]>(INITIAL_PROTECTED_MEANINGS);
  const [activePlayingSegmentId, setActivePlayingSegmentId] = useState<string | null>(null);
  const [isApprovedGlobally, setIsApprovedGlobally] = useState<boolean>(false);

  // Check if any protected meaning is violated
  const hasViolations = protectedMeanings.some((m) => m.isViolated);

  // Check if user text edit violated meaning lock
  const handleUpdateSegmentText = (segmentId: string, newText: string) => {
    setSegments((prev) =>
      prev.map((seg) => (seg.id === segmentId ? { ...seg, text: newText } : seg))
    );

    // If segment 2 is edited and the distinction between Zakat and Sadaqah is deleted
    if (segmentId === 'seg_2') {
      const containsDifference = newText.includes('تختلف') || newText.includes('الصدقة التطوعية') || newText.includes('الصدقة');
      if (!containsDifference) {
        setProtectedMeanings((prev) =>
          prev.map((m) =>
            m.id === 'pm_3' ? { ...m, isViolated: true } : m
          )
        );
      } else {
        setProtectedMeanings((prev) =>
          prev.map((m) =>
            m.id === 'pm_3' ? { ...m, isViolated: false } : m
          )
        );
      }
    }
  };

  // Toggle violation simulation for testing
  const handleToggleViolation = (meaningId: string) => {
    setProtectedMeanings((prev) =>
      prev.map((m) =>
        m.id === meaningId ? { ...m, isViolated: !m.isViolated } : m
      )
    );
  };

  // Restore protected meaning
  const handleRestoreMeanings = () => {
    setProtectedMeanings((prev) =>
      prev.map((m) => ({ ...m, isViolated: false }))
    );
    // Restore text of segment 2 if needed
    setSegments((prev) =>
      prev.map((seg) =>
        seg.id === 'seg_2' ? { ...seg, text: INITIAL_SEGMENTS[1].text } : seg
      )
    );
  };

  // Play segment simulation
  const handlePlaySegment = (segmentId: string) => {
    if (activePlayingSegmentId === segmentId) {
      setActivePlayingSegmentId(null);
    } else {
      setActivePlayingSegmentId(segmentId);
    }
  };

  // Term actions
  const handleApproveTerm = (termId: string) => {
    if (hasViolations) return; // Prevent approval when meaning lock is violated
    setTerms((prev) =>
      prev.map((t) => (t.id === termId ? { ...t, status: 'approved' } : t))
    );
  };

  const handleEditTerm = (termId: string) => {
    const updatedEquivalent = prompt('أدخل المقابل المعتمد الجديد للمصطلح:', 'Zakah');
    if (updatedEquivalent) {
      setTerms((prev) =>
        prev.map((t) =>
          t.id === termId ? { ...t, approvedEquivalent: updatedEquivalent, status: 'pending' } : t
        )
      );
    }
  };

  const handleSendForReview = (termId: string) => {
    setTerms((prev) =>
      prev.map((t) =>
        t.id === termId ? { ...t, status: 'sent_for_review', reviewStatus: 'قيد المراجعة' } : t
      )
    );
    alert('تم إرسال المصطلح إلى اللجنة الشرعية واللغوية للتدقيق.');
  };

  return (
    <div className="flex min-h-[calc(100vh-180px)] flex-col selection:bg-brand-100 selection:text-brand-900">
      
      {/* Header */}

      {/* Breadcrumb / Top Bar */}
      <div className="w-full border-b border-slate-200/80 bg-white py-3.5 px-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {onBackToHome && (
              <button
                type="button"
                onClick={onBackToHome}
                className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium p-1.5 rounded-lg hover:bg-slate-100"
              >
                <ArrowRight className="w-4 h-4" />
                <span>الرئيسية</span>
              </button>
            )}

            <span className="text-slate-300">/</span>

            <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
              <span>مراجعة النص والمصطلحات</span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-800 border border-brand-200/70">
                الشاشة 3
              </span>
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium">
              النمط المعتمد: <strong className="text-brand-900">{dubbingMode === 'faithful' ? 'الأمينة' : dubbingMode === 'timed' ? 'الزمنية' : 'المبسطة'}</strong>
            </span>

            <button
              type="button"
              disabled={hasViolations}
              onClick={() => {
                setIsApprovedGlobally(true);
                if (onNavigateToTimingReview) {
                  onNavigateToTimingReview();
                }
              }}
              className={`inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs sm:text-sm font-bold shadow-sm transition-all ${
                hasViolations
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-200'
                  : isApprovedGlobally
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer'
                  : 'bg-brand-800 hover:bg-brand-700 text-white cursor-pointer active:scale-98 shadow-brand-900/10'
              }`}
            >
              <Check className="w-4 h-4" />
              <span>{isApprovedGlobally ? 'الانتقال لمراجعة التوقيت (الشاشة 4)' : 'اعتماد المراجعة والمتابعة'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Container: Clean Two-Column Desktop Layout (1440 × 900 Optimized) */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        
        {/* High Risk Warning Banner: Shown prominently if meaning lock is violated */}
        {hasViolations && (
          <div className="mb-6">
            <HighRiskWarningBanner
              message="حُذف المعنى المحمي: تختلف الزكاة عن الصدقة التطوعية. لا يمكن اعتماد هذا المقطع قبل إعادة المعنى."
              onRestore={handleRestoreMeanings}
            />
          </div>
        )}

        {/* Global approval success confirmation */}
        {isApprovedGlobally && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs sm:text-sm shadow-subtle animate-in fade-in">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>تم اعتماد تدقيق النص والمصطلحات بنجاح، المحتوى جاهز للمرحلة التالية (مراجعة الترجمة والمطابقة الزمنية).</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[11px] font-semibold text-emerald-700 bg-white px-2.5 py-1 rounded-lg border border-emerald-200">
                معتمد شرعياً ولغوياً
              </span>
              {onNavigateToTimingReview && (
                <button
                  type="button"
                  onClick={onNavigateToTimingReview}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs shadow-sm transition-all active:scale-98"
                >
                  <span>مراجعة الترجمة والتوقيت (الشاشة 4)</span>
                  <ArrowLeft className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
          
          {/* ========================================================
              RIGHT SIDE (الجانب الأيمن): Video Preview + Terminology + Meaning Lock
              ======================================================== */}
          <div className="lg:col-span-5 space-y-6 order-1 lg:order-1">
            
            {/* 1. Video Preview Card */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-subtle p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Film className="w-4 h-4 text-brand-700" />
                  <h3 className="text-sm font-bold text-slate-800">
                    معاينة الفيديو الأصلي
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-100">
                  {video.name}
                </span>
              </div>

              {/* Video Player */}
              <div className="mx-auto w-full max-w-[800px] rounded-xl overflow-hidden bg-slate-950 aspect-video relative shadow-inner border border-slate-800">
                <video
                  src={video.previewUrl}
                  controls
                  className="w-full h-full object-contain"
                  playsInline
                />
              </div>

              <div className="mt-3 flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
                <span>المشغل متزامن مع المقاطع النصية</span>
                <span className="font-mono text-slate-700 font-semibold">00:48 دقيقة</span>
              </div>
            </div>

            {/* 2. Terminology Section: "المصطلحات المكتشفة" */}
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-600" />
                  <h3 className="text-base font-bold text-slate-900">
                    المصطلحات المكتشفة
                  </h3>
                </div>
                <span className="text-xs text-slate-500 font-medium">
                  {terms.length} مصطلحات
                </span>
              </div>

              {terms.map((term) => (
                <TerminologyCard
                  key={term.id}
                  term={term}
                  isApprovalDisabled={hasViolations}
                  onApprove={handleApproveTerm}
                  onEdit={handleEditTerm}
                  onSendForReview={handleSendForReview}
                />
              ))}
            </div>

            {/* 3. Meaning Lock Section: "قفل المعنى | Meaning Lock" */}
            <div>
              <MeaningLockSection
                meanings={protectedMeanings}
                onToggleViolationTest={handleToggleViolation}
              />
            </div>

          </div>

          {/* ========================================================
              LEFT SIDE (الجانب الأيسر): Timed Arabic Transcript Segments
              ======================================================== */}
          <div className="lg:col-span-7 space-y-4 order-2 lg:order-2">
            
            <div className="flex items-center justify-between px-1">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  المقاطع النصية المفرغة والمؤقتة
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  يمكنك الاستماع لكل مقطع وتعديل النصوص مباشرة قبل التوليد الصوتي
                </p>
              </div>

              <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700">
                {segments.length} مقاطع
              </span>
            </div>

            {/* Segments List */}
            <div className="space-y-3.5">
              {segments.map((segment) => (
                <TranscriptSegmentCard
                  key={segment.id}
                  segment={segment}
                  isPlaying={activePlayingSegmentId === segment.id}
                  onPlay={handlePlaySegment}
                  onUpdateText={handleUpdateSegmentText}
                />
              ))}
            </div>

            {/* Meaning lock reminder footer banner */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-brand-700 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                يراقب نظام <strong>قفل المعنى (Meaning Lock)</strong> التعديلات النصية تلقائياً لضمان عدم حذف أي دلالة عقدية أو فقهية أساسية أثناء التحرير.
              </p>
            </div>

          </div>

        </div>

      </main>

      {/* Footer */}
      <footer className="w-full py-6 mt-auto border-t border-slate-200/60 bg-white/40 text-center text-xs text-slate-400">
        <p>منصة بلاغ (BALAGH) — دبلجة ذكية واعية بالسياق والمصطلحات الإسلامية © 2026</p>
      </footer>

    </div>
  );
};
