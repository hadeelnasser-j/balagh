import React from 'react';
import { Home, PlusCircle } from 'lucide-react';

interface CompletionScreenProps {
  onGoHome: () => void;
  onStartNewProject: () => void;
}

// Eight-pointed star (khatam) used as a quiet Islamic motif around the success mark.
const StarOutline: React.FC<{ className?: string; size: number }> = ({ className, size }) => (
  <svg viewBox="0 0 100 100" width={size} height={size} className={className} fill="none" aria-hidden="true">
    <rect x="18" y="18" width="64" height="64" rx="3" stroke="currentColor" strokeWidth="1.5" />
    <rect x="18" y="18" width="64" height="64" rx="3" stroke="currentColor" strokeWidth="1.5" transform="rotate(45 50 50)" />
  </svg>
);

const Ornament: React.FC = () => (
  <div className="flex items-center justify-center gap-3 text-accent-gold/70" aria-hidden="true">
    <span className="h-px w-16 bg-gradient-to-l from-accent-gold/60 to-transparent sm:w-24" />
    <StarOutline size={16} />
    <span className="h-px w-16 bg-gradient-to-r from-accent-gold/60 to-transparent sm:w-24" />
  </div>
);

const delay = (ms: number): React.CSSProperties => ({ animationDelay: `${ms}ms` });

export const CompletionScreen: React.FC<CompletionScreenProps> = ({ onGoHome, onStartNewProject }) => (
  <main
    dir="rtl"
    className="relative flex min-h-[calc(100vh-72px)] items-center justify-center overflow-hidden bg-gradient-to-b from-[#0B1437] to-[#060B1E] px-4 py-10 sm:py-16"
  >
    {/* Subtle geometric watermark and soft brand glows */}
    <div className="bg-islamic-pattern pointer-events-none absolute inset-0 opacity-70" aria-hidden="true" />
    <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-cyan-400/10 blur-3xl" aria-hidden="true" />
    <div className="pointer-events-none absolute -bottom-40 right-1/4 h-80 w-80 rounded-full bg-accent-gold/10 blur-3xl" aria-hidden="true" />

    <section
      aria-labelledby="completion-title"
      className="balagh-fade-in glass-card relative w-full max-w-2xl rounded-3xl px-6 py-10 text-center sm:px-12 sm:py-12"
    >
      {/* Success mark */}
      <div className="balagh-fade-in relative mx-auto mb-7 flex h-24 w-24 items-center justify-center" style={delay(100)}>
        <StarOutline size={96} className="absolute inset-0 text-accent-gold/50" />
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-400 shadow-glow-cyan">
          <svg viewBox="0 0 24 24" width={28} height={28} className="text-[#060B1E]" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </div>
      </div>

      <h1 id="completion-title" className="balagh-fade-in text-2xl font-extrabold leading-relaxed text-white sm:text-3xl" style={delay(200)}>
        <span aria-hidden="true">🌿 </span>
        <span className="text-gradient-cyan">جزاك الله خيرًا، وبارك الله في سعيك</span>
      </h1>

      <div className="balagh-fade-in my-7" style={delay(300)}>
        <Ornament />
      </div>

      <div className="space-y-5 text-base leading-8 text-slate-200 sm:text-[17px] sm:leading-9">
        <p className="balagh-fade-in" style={delay(400)}>
          نشكرك على مساهمتك في خدمة المحتوى الإسلامي ونشر الخير بين الناس.
        </p>
        <p className="balagh-fade-in" style={delay(500)}>
          إن حرصك على إيصال المعاني الصحيحة، والمحافظة على دقة الترجمة وتوثيق المصادر، هو عملٌ عظيم النفع، وأثره
          يمتد إلى كل من ينتفع بهذا المحتوى.
        </p>

        <figure
          className="balagh-fade-in mx-auto max-w-md rounded-2xl border border-accent-gold/30 bg-white/[0.04] px-6 py-5"
          style={delay(600)}
        >
          <figcaption className="text-sm text-slate-300">قال رسول الله ﷺ:</figcaption>
          <blockquote className="mt-2 text-xl font-bold leading-relaxed text-accent-goldLight sm:text-2xl">
            «بلّغوا عنّي ولو آية»
          </blockquote>
          <p className="mt-2 text-xs text-slate-400">رواه البخاري</p>
        </figure>

        <p className="balagh-fade-in" style={delay(700)}>
          وما تقوم به اليوم هو صورة من صور التبليغ والدعوة إلى الله بالوسائل الحديثة، نسأل الله أن يجعله في ميزان
          حسناتك وأن يبارك في وقتك وعلمك وجهدك.
        </p>

        <p
          className="balagh-fade-in rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.06] px-5 py-4 text-slate-100"
          style={delay(800)}
        >
          <span aria-hidden="true">✨ </span>
          كل ترجمة دقيقة، وكل مراجعة متأنية، وكل محتوى نافع يصل إلى الآخرين قد يكون سببًا في هدايةٍ أو علمٍ ينتفع
          به، فيستمر أجره بإذن الله.
        </p>

        <p className="balagh-fade-in" style={delay(900)}>
          نسأل الله أن يتقبل منك، وأن يجزيك خير الجزاء على مساهمتك في نشر العلم النافع وخدمة دين الإسلام.
        </p>
      </div>

      <div className="balagh-fade-in mt-9 flex flex-col-reverse gap-3 sm:flex-row sm:justify-center" style={delay(1000)}>
        <button
          type="button"
          onClick={onStartNewProject}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-transparent px-6 py-3 text-sm font-bold text-cyan-200 transition-all hover:border-cyan-300 hover:bg-cyan-400/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
        >
          <PlusCircle className="h-4 w-4" />
          بدء مشروع جديد
        </button>
        <button
          type="button"
          onClick={onGoHome}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 px-7 py-3 text-sm font-bold text-slate-950 shadow-glow-cyan transition-all hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
        >
          <Home className="h-4 w-4" />
          العودة إلى الصفحة الرئيسية
        </button>
      </div>

      <footer className="balagh-fade-in mt-9 border-t border-white/10 pt-6" style={delay(1100)}>
        <p className="text-sm font-semibold text-slate-300">
          <span aria-hidden="true">🤍 </span>
          شكرًا لك على كونك جزءًا من رسالة "بلاغ"
        </p>
      </footer>
    </section>
  </main>
);

export default CompletionScreen;
