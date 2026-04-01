'use client';
import React, { useState } from 'react';

const CATEGORIES = [
  { value: 'general',    label: 'General Question',   icon: '💬', color: 'from-blue-500 to-cyan-500' },
  { value: 'technical',  label: 'Technical Support',  icon: '⚙️', color: 'from-violet-500 to-indigo-500' },
  { value: 'billing',    label: 'Billing Inquiry',     icon: '💳', color: 'from-emerald-500 to-teal-500' },
  { value: 'bug_report', label: 'Bug Report',          icon: '🐛', color: 'from-rose-500 to-pink-500' },
  { value: 'feedback',   label: 'Feedback',            icon: '⭐', color: 'from-amber-500 to-orange-500' },
];

const PRIORITIES = [
  { value: 'low',    label: 'Low',    desc: 'Not urgent',       dot: 'bg-emerald-400' },
  { value: 'medium', label: 'Medium', desc: 'Need help soon',   dot: 'bg-amber-400' },
  { value: 'high',   label: 'High',   desc: 'Urgent issue',     dot: 'bg-rose-400' },
];

export default function SupportForm({ apiEndpoint = '/api/support/submit' }) {
  const [formData, setFormData] = useState({
    name: '', email: '', subject: '', category: 'general', priority: 'medium', message: '',
  });
  const [status, setStatus]     = useState('idle');
  const [ticketId, setTicketId] = useState(null);
  const [error, setError]       = useState(null);
  const [focused, setFocused]   = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  const validate = () => {
    if (formData.name.trim().length < 2)   { setError('Name must be at least 2 characters'); return false; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { setError('Enter a valid email address'); return false; }
    if (formData.subject.trim().length < 5) { setError('Subject must be at least 5 characters'); return false; }
    if (formData.message.trim().length < 10){ setError('Message must be at least 10 characters'); return false; }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!validate()) return;
    setStatus('submitting');
    try {
      const res = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Submission failed');
      }
      const data = await res.json();
      setTicketId(data.ticket_id);
      setStatus('success');
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  // ── Success Screen ──────────────────────────────────────────────────────────
  if (status === 'success') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="glass-card rounded-3xl p-10 text-center">
          {/* Animated checkmark */}
          <div className="success-bounce inline-flex items-center justify-center w-24 h-24 rounded-full mb-6
                          bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-400 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white mb-2">Request Submitted!</h2>
          <p className="text-white/50 mb-8">Our AI is already working on your issue.</p>

          {/* Ticket ID card */}
          <div className="relative p-px rounded-2xl mb-8" style={{
            background: 'linear-gradient(135deg, #6366f1, #a78bfa, #06b6d4)',
          }}>
            <div className="rounded-2xl bg-[#0f0f1a] p-6">
              <p className="text-xs text-white/40 uppercase tracking-widest mb-2">Your Ticket ID</p>
              <p className="text-xl font-mono font-bold shimmer">{ticketId}</p>
              <p className="text-xs text-white/30 mt-2">Save this for reference</p>
            </div>
          </div>

          {/* What happens next */}
          <div className="grid grid-cols-3 gap-3 mb-8 text-sm">
            {[
              { icon: '🤖', title: 'AI Analyzes', desc: 'Instantly' },
              { icon: '📨', title: 'Response Sent', desc: 'Within 5 min' },
              { icon: '✅', title: 'Issue Resolved', desc: 'Or escalated' },
            ].map(step => (
              <div key={step.title} className="p-3 rounded-xl bg-white/5 border border-white/5">
                <div className="text-2xl mb-1">{step.icon}</div>
                <div className="font-medium text-white/80">{step.title}</div>
                <div className="text-white/40 text-xs">{step.desc}</div>
              </div>
            ))}
          </div>

          <button
            onClick={() => {
              setStatus('idle');
              setTicketId(null);
              setFormData({ name: '', email: '', subject: '', category: 'general', priority: 'medium', message: '' });
            }}
            className="px-8 py-3 rounded-xl border border-white/10 text-white/70 hover:text-white
                       hover:bg-white/5 transition-all text-sm font-medium"
          >
            Submit Another Request
          </button>
        </div>
      </div>
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────────
  const inputBase = `
    w-full px-4 py-3 rounded-xl text-white placeholder-white/25 text-sm
    bg-white/[0.05] border border-white/[0.08]
    focus:outline-none focus:border-indigo-500/60 input-glow
    transition-all duration-200
  `;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="glass-card rounded-3xl p-8 md:p-10">

        {/* Form header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Open a Support Ticket</h2>
            <p className="text-white/40 text-sm">Usually answered within 5 minutes</p>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 mb-6 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Name + Email */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
                Full Name <span className="text-indigo-400">*</span>
              </label>
              <input
                type="text" name="name" value={formData.name}
                onChange={handleChange}
                onFocus={() => setFocused('name')} onBlur={() => setFocused(null)}
                placeholder="Jane Smith"
                className={inputBase}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
                Email Address <span className="text-indigo-400">*</span>
              </label>
              <input
                type="email" name="email" value={formData.email}
                onChange={handleChange}
                onFocus={() => setFocused('email')} onBlur={() => setFocused(null)}
                placeholder="jane@company.com"
                className={inputBase}
              />
            </div>
          </div>

          {/* Subject */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
              Subject <span className="text-indigo-400">*</span>
            </label>
            <input
              type="text" name="subject" value={formData.subject}
              onChange={handleChange}
              onFocus={() => setFocused('subject')} onBlur={() => setFocused(null)}
              placeholder="Brief description of your issue"
              className={inputBase}
            />
          </div>

          {/* Category — visual card selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
              Category <span className="text-indigo-400">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setFormData(p => ({ ...p, category: cat.value }))}
                  className={`
                    p-3 rounded-xl border text-center transition-all duration-200 text-xs font-medium
                    ${formData.category === cat.value
                      ? `bg-gradient-to-br ${cat.color} border-transparent text-white shadow-lg`
                      : 'border-white/[0.08] text-white/40 hover:text-white/70 hover:bg-white/[0.05] bg-white/[0.02]'}
                  `}
                >
                  <div className="text-lg mb-1">{cat.icon}</div>
                  <div className="leading-tight">{cat.label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Priority */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
              Priority
            </label>
            <div className="flex gap-2">
              {PRIORITIES.map(p => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, priority: p.value }))}
                  className={`
                    flex-1 flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm transition-all
                    ${formData.priority === p.value
                      ? 'border-indigo-500/50 bg-indigo-500/10 text-white'
                      : 'border-white/[0.08] text-white/40 hover:text-white/60 hover:bg-white/[0.03] bg-transparent'}
                  `}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${p.dot}`} />
                  <span className="font-medium">{p.label}</span>
                  <span className={`text-xs hidden sm:block ${formData.priority === p.value ? 'text-white/50' : 'text-white/25'}`}>
                    {p.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Message */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white/50 uppercase tracking-wider">
              Message <span className="text-indigo-400">*</span>
            </label>
            <div className="relative">
              <textarea
                name="message" value={formData.message}
                onChange={handleChange}
                onFocus={() => setFocused('message')} onBlur={() => setFocused(null)}
                rows={5}
                placeholder="Describe your issue in detail — the more context, the faster our AI can help..."
                className={`${inputBase} resize-none`}
              />
              {/* Char count */}
              <div className={`absolute bottom-3 right-3 text-xs transition-colors ${
                formData.message.length < 10 ? 'text-rose-400/60' : 'text-white/20'
              }`}>
                {formData.message.length} chars
              </div>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={status === 'submitting'}
            className={`
              relative w-full py-4 px-6 rounded-xl text-white font-semibold text-sm
              overflow-hidden transition-all duration-300
              ${status === 'submitting' ? 'opacity-70 cursor-not-allowed' : 'btn-gradient'}
            `}
          >
            {status === 'submitting' ? (
              <span className="flex items-center justify-center gap-3">
                <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Sending to AI...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Submit Support Request
              </span>
            )}
          </button>

          {/* Footer note */}
          <p className="text-center text-xs text-white/20 pt-1">
            By submitting, you agree to our support terms. Average response time: &lt;5 minutes.
          </p>
        </form>
      </div>
    </div>
  );
}
