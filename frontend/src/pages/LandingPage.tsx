import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { InterviewNote } from '../components/InterviewNote';
import StrokeText from '../components/StrokeText';

gsap.registerPlugin(ScrollTrigger);

const STAGES = [
  { label: 'Ingest', desc: 'Parsing candidate resume & loading ML textbook corpus.' },
  { label: 'Embed', desc: 'Vectorizing professional experience and academic literature.' },
  { label: 'Retrieve', desc: 'Finding intersections between your background and core ML concepts.' },
  { label: 'Generate', desc: 'Synthesizing novel interview scenarios grounded in literature.' },
  { label: 'Adapt', desc: 'Calibrating difficulty in real-time based on your responses.' }
];

export function LandingPage() {
  const navigate = useNavigate();
  const stagesRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    if (!stagesRef.current) return;
    
    const ctx = gsap.context(() => {
      ScrollTrigger.create({
        trigger: stagesRef.current,
        start: 'top top',
        end: '+=400%',
        pin: true,
        scrub: true,
        snap: {
          snapTo: 1 / (STAGES.length - 1),
          duration: 0.5,
          ease: 'power2.inOut'
        },
        onUpdate: (self) => {
          const index = Math.round(self.progress * (STAGES.length - 1));
          setActiveStage(prev => (prev !== index ? index : prev));
        }
      });
    }, stagesRef);

    return () => ctx.revert();
  }, []);

  useEffect(() => {
    if (!cardsRef.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = gsap.context(() => {
      gsap.from('[data-workflow-card]', {
        y: 28,
        opacity: 0,
        duration: 0.7,
        stagger: 0.12,
        ease: 'power3.out',
        scrollTrigger: { trigger: cardsRef.current, start: 'top 82%' }
      });
    }, cardsRef);
    return () => ctx.revert();
  }, []);

  return (
    <div className="relative w-full">
      {/* Hero Section */}
      <section className="relative min-h-[calc(100dvh-3.5rem)] overflow-hidden px-6 py-16 lg:px-24 lg:py-20">
        <div className="relative z-10 mx-auto grid min-h-[calc(100dvh-13.5rem)] max-w-7xl items-center gap-14 lg:grid-cols-[minmax(0,0.95fr)_minmax(25rem,0.85fr)] lg:gap-20">
          <div className="max-w-xl">
          <h1 className="text-5xl font-display tracking-tight leading-[1.08] md:text-6xl lg:text-7xl mb-6">
            Grounded ML questions. Adapted to you.
          </h1>
          <p className="text-lg text-muted-foreground mb-10 max-w-lg">
            A specialized RAG screening system that retrieves authoritative machine learning literature and tailors adaptive scenarios to your experience.
          </p>
          <button 
            onClick={() => navigate('/upload')}
            className="px-8 py-4 bg-foreground text-background font-mono text-sm uppercase tracking-wider hover:bg-foreground/90 transition-transform active:scale-95"
          >
            Start Interview
          </button>
          </div>
          <InterviewNote onBegin={() => navigate('/upload')} />
        </div>
      </section>

      {/* GSAP Pipeline Narrative */}
      <section ref={stagesRef} className="relative h-[100dvh] bg-background border-t border-hairline flex flex-col items-center justify-center overflow-hidden">
        <div className="w-full max-w-5xl px-6 flex flex-col items-center text-center">
          <span className="font-mono text-accent text-sm tracking-widest uppercase mb-12">
            0{activeStage + 1} // Pipeline Stage
          </span>

          <div className="w-full max-w-3xl flex items-center justify-center">
            <StrokeText
              key={activeStage}
              text={STAGES[activeStage].label}
              strokeColor="var(--accent)"
              fillColor="var(--foreground)"
              strokeWidth={1.5}
              drawDuration={1.2}
              fillDelay={0.1}
              stagger={0.08}
              ease="power2.out"
              trigger="mount"
              fillMode="wipe"
              fontSize={140}
              fontWeight={700}
              letterSpacing={-2}
            />
          </div>

          <p className="text-lg md:text-xl text-muted-foreground mt-12 max-w-2xl h-16">
            {STAGES[activeStage].desc}
          </p>
        </div>
      </section>
      
      {/* Footer / Summary Cards */}
      <section ref={cardsRef} className="px-6 py-20 lg:px-24 lg:py-28 border-t border-hairline bg-panel relative z-10">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5 grid-flow-dense">
          <div data-workflow-card className="workflow-card glass-panel p-8 flex flex-col items-start">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">01</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Upload Resume</h3>
             <p className="text-sm text-muted-foreground">System extracts key skills and maps them to our ML knowledge graph.</p>
          </div>
          <div data-workflow-card className="workflow-card glass-panel p-8 flex flex-col items-start">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">02</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Adaptive Q&A</h3>
             <p className="text-sm text-muted-foreground">Answer questions with live scoring that adjusts subsequent difficulty.</p>
          </div>
          <div data-workflow-card className="workflow-card glass-panel p-8 flex flex-col items-start">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">03</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Detailed Summary</h3>
             <p className="text-sm text-muted-foreground">Receive a comprehensive breakdown of strengths, gaps, and citation sources.</p>
          </div>
        </div>
      </section>

      <section className="bg-panel py-12 overflow-hidden flex items-center justify-center relative z-10 border-t border-hairline">
        <span className="font-display text-6xl font-semibold tracking-[-0.08em] text-foreground md:text-8xl">VIVA</span>
      </section>
    </div>
  );
}
