import { useState } from 'react';

export function AuthOffer() {
  const [accepted, setAccepted] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return <p className="border-l-2 border-accent pl-4 text-sm text-muted-foreground">Account access is being prepared. Your interview can continue without it.</p>;
  }

  return (
    <section className="auth-offer overflow-hidden border border-glass-border bg-glass">
      <div className="grid md:grid-cols-[.8fr_1.2fr]">
        <div className="auth-offer-art min-h-56 p-7 text-background">
          <div className="relative z-10 flex h-full flex-col justify-between">
            <span className="font-display text-lg font-semibold tracking-tight">VIVA</span>
            <p className="max-w-[18rem] font-display text-2xl leading-tight">Keep every hard-won answer in one place.</p>
          </div>
        </div>
        <form onSubmit={(event) => { event.preventDefault(); if (accepted) setSubmitted(true); }} className="p-7">
          <h2 className="font-display text-xl tracking-tight">Save this interview workspace</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">Optional for now. Continue as a guest, or reserve your account for future sessions.</p>
          <label className="mt-6 block">
            <span className="sr-only">Email address</span>
            <input required type="email" placeholder="you@example.com" className="w-full border border-hairline bg-background px-3 py-2.5 text-sm outline-none transition-colors focus:border-accent" />
          </label>
          <label className="mt-3 flex cursor-pointer items-start gap-2 text-xs leading-relaxed text-muted-foreground">
            <input checked={accepted} onChange={(event) => setAccepted(event.target.checked)} type="checkbox" className="mt-0.5 accent-[var(--accent)]" />
            <span>I agree to be contacted when account access is ready.</span>
          </label>
          <div className="mt-5 flex items-center gap-4">
            <button disabled={!accepted} className="bg-foreground px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-40">Reserve access</button>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">No login required</span>
          </div>
        </form>
      </div>
    </section>
  );
}
