'use client';
import SupportForm from '../components/SupportForm';

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden">

      {/* Animated background orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />
      <div className="bg-orb bg-orb-3" />

      {/* Grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Top nav bar */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="font-bold text-lg tracking-tight text-white">TechNova</span>
        </div>

        {/* Live status badge */}
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot" />
          <span className="text-emerald-400 font-medium">AI Online</span>
          <span className="text-white/30 mx-1">·</span>
          <span className="text-white/50">24/7 Support</span>
        </div>
      </nav>

      {/* Hero section */}
      <div className="relative z-10 text-center px-4 pt-10 pb-6 max-w-3xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-medium mb-6">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Powered by Claude AI
        </div>

        <h1 className="text-5xl font-bold mb-4 leading-tight">
          <span className="text-white">How can we </span>
          <span className="gradient-text">help you today?</span>
        </h1>
        <p className="text-white/50 text-lg max-w-xl mx-auto">
          Our AI resolves most issues in under 5 minutes — no waiting, no queues.
        </p>

        {/* Stats row */}
        <div className="flex items-center justify-center gap-8 mt-8 mb-2">
          {[
            { value: '<5 min', label: 'Avg. Response' },
            { value: '99.9%', label: 'Uptime' },
            { value: '24/7', label: 'Availability' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-2xl font-bold gradient-text">{stat.value}</div>
              <div className="text-xs text-white/40 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <div className="relative z-10 px-4 pb-16">
        <SupportForm apiEndpoint="/api/support/submit" />
      </div>

      {/* Bottom channels note */}
      <div className="relative z-10 text-center pb-10 px-4">
        <p className="text-white/25 text-sm">
          Also reach us via{' '}
          <span className="text-indigo-400/70 cursor-default">WhatsApp</span>
          {' '}or{' '}
          <span className="text-cyan-400/70 cursor-default">Email</span>
          {' '}— all channels connect to the same AI agent.
        </p>
      </div>
    </main>
  );
}
