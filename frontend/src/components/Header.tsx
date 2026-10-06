import React from 'react';
import { Sparkles, ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-cyan-500/20 bg-[#0B1437]/85 backdrop-blur-xl shadow-[0_4px_20px_rgba(0,0,0,0.28)]">
      <div className="mx-auto w-full max-w-7xl px-4 py-3 sm:px-6">
        <div className="flex items-center justify-between gap-4">
          
          {/* Brand & Identity */}
          <div className="flex items-center gap-4">
            {/* Multi-petal Lotus / AI Challenge Logo Emblem */}
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500/20 via-blue-600/30 to-purple-700/40 p-[1px] shadow-glow-cyan shrink-0">
              <div className="w-full h-full rounded-xl bg-[#060B1E] flex items-center justify-center border border-cyan-400/40">
                <svg className="w-7 h-7 text-cyan-400" viewBox="0 0 48 48" fill="none">
                  <path d="M24 6 C28 14 34 18 42 24 C34 30 28 34 24 42 C20 34 14 30 6 24 C14 18 20 14 24 6 Z" stroke="url(#cyanGlow)" strokeWidth="2.2" strokeLinejoin="round"/>
                  <circle cx="24" cy="24" r="5" fill="#00F5D4" className="animate-pulse"/>
                  <defs>
                    <linearGradient id="cyanGlow" x1="6" y1="6" x2="42" y2="42" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#00F5D4"/>
                      <stop offset="0.5" stopColor="#00F2FE"/>
                      <stop offset="1" stopColor="#7928CA"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <span className="font-extrabold text-gradient-cyan text-2xl">بلاغ</span>
                  <span className="text-cyan-500/40 font-light text-sm">|</span>
                  <span className="text-xs uppercase tracking-widest text-cyan-300/80 font-bold pt-0.5">BALAGH</span>
                </h1>
                
                <span className="hidden md:inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-[11px] font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(0,245,212,0.15)]">
                  <Sparkles className="w-3 h-3 text-cyan-400 animate-pulse" />
                  دبلجة واعية بالسياق والمصطلحات
                </span>
              </div>

              <p className="text-xs font-medium text-slate-300/90 mt-0.5 flex items-center gap-1.5">
                <span className="text-cyan-400">"نُبلّغ  "</span>
              </p>
            </div>
          </div>

          {/* AI Challenge Branding & Status Indicator */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-900/80 border border-slate-700/60 text-[11px] text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي</span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-xs text-cyan-300">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400"></span>
              </span>
              <span className="font-semibold text-[11px]"> MVP </span>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
};
