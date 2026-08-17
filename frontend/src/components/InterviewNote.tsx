import { useEffect, useRef, useState } from 'react';

const QUESTIONS = [
  'Are you prepared for the interview?',
  'How would you diagnose model drift?',
  "What's your biggest technical weakness?",
];

export function InterviewNote({ onBegin }: { onBegin: () => void }) {
  const [line, setLine] = useState(0);
  const [text, setText] = useState('');
  const [paused, setPaused] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) {
      setText(QUESTIONS[0]);
      return;
    }

    const target = QUESTIONS[line];
    if (text.length < target.length) {
      timer.current = window.setTimeout(() => setText(target.slice(0, text.length + 1)), 26);
    } else {
      timer.current = window.setTimeout(() => {
        setText('');
        setLine((current) => (current + 1) % QUESTIONS.length);
      }, 1800);
    }
    return () => window.clearTimeout(timer.current);
  }, [line, text]);

  return (
    <button
      type="button"
      onClick={onBegin}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className={`interview-note group relative block w-full max-w-[34rem] text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${paused ? 'is-paused' : ''}`}
      aria-label="Start an interview"
    >
      <span className="note-sheet note-sheet--rose" />
      <span className="note-sheet note-sheet--mauve" />
      <span className="note-clip" aria-hidden="true" />
      <span className="note-face">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Viva prompt</span>
        <span className="mt-8 block min-h-[7rem] font-display text-2xl leading-snug tracking-tight text-foreground md:text-3xl">
          {text}<span className="note-cursor" aria-hidden="true">_</span>
        </span>
        <span className="mt-10 flex items-center justify-between border-t border-hairline pt-4 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>Tap to begin</span><span>01—03</span>
        </span>
      </span>
    </button>
  );
}
