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
      <section className="relative min-h-[calc(100dvh-3.5rem)] overflow-hidden px-6 py-20 lg:px-32 lg:py-32">
        <div className="relative z-10 mx-auto grid min-h-[calc(100dvh-13.5rem)] max-w-7xl items-center gap-16 lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.85fr)] lg:gap-32">
          <div className="max-w-2xl">
          <h1 className="text-5xl font-display tracking-tight leading-[1.08] md:text-6xl lg:text-7xl mb-10">
            Grounded ML questions. Adapted to you.
          </h1>
          <p className="text-lg text-muted-foreground mb-14 max-w-lg leading-relaxed">
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

      {/* Alternating Feature Sections */}
      <div className="bg-background relative z-10 border-t border-hairline">
        
        {/* Feature 1: Upload */}
        <section className="py-24 lg:py-40 px-6">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <div className="max-w-xl">
              <span className="font-mono text-accent text-sm tracking-widest uppercase mb-6 block">01 // Context</span>
              <h2 className="text-4xl lg:text-5xl font-display tracking-tight mb-8 leading-[1.1]">Map your experience to our knowledge graph.</h2>
              <p className="text-lg text-muted-foreground leading-relaxed">
                Drop in your resume. Viva extracts your core competencies, identifies the exact technical domains you've worked in, and builds a custom syllabus tailored to your actual background, not a generic rubric.
              </p>
            </div>
            <div className="relative group">
              <div className="absolute -inset-4 bg-accent/5 rounded-2xl blur-2xl group-hover:bg-accent/10 transition-colors duration-500"></div>
              <div className="bg-panel border border-hairline rounded-xl overflow-hidden shadow-2xl aspect-[16/10] relative z-10">
                <img src="/screenshots/upload.png" alt="Upload interface" className="w-full h-full object-cover object-top" />
              </div>
            </div>
          </div>
        </section>

        {/* Feature 2: Interview */}
        <section className="py-24 lg:py-40 px-6 bg-panel/50 border-y border-hairline">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <div className="relative group lg:order-first order-last">
              <div className="absolute -inset-4 bg-accent/5 rounded-2xl blur-2xl group-hover:bg-accent/10 transition-colors duration-500"></div>
              <div className="bg-panel border border-hairline rounded-xl overflow-hidden shadow-2xl aspect-[16/10] relative z-10">
                <img src="/screenshots/interview.png" alt="Live Interview interface" className="w-full h-full object-cover object-top" />
              </div>
            </div>
            <div className="max-w-xl lg:ml-auto">
              <span className="font-mono text-accent text-sm tracking-widest uppercase mb-6 block">02 // Adaptive Q&A</span>
              <h2 className="text-4xl lg:text-5xl font-display tracking-tight mb-8 leading-[1.1]">Answer dynamically generated scenarios.</h2>
              <p className="text-lg text-muted-foreground leading-relaxed">
                No static question banks. Every question is grounded in authoritative ML literature, and the system dynamically adjusts difficulty based on your real-time responses to probe your exact depth of knowledge.
              </p>
            </div>
          </div>
        </section>

        {/* Feature 3: Summary */}
        <section className="py-24 lg:py-40 px-6">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <div className="max-w-xl">
              <span className="font-mono text-accent text-sm tracking-widest uppercase mb-6 block">03 // Analysis</span>
              <h2 className="text-4xl lg:text-5xl font-display tracking-tight mb-8 leading-[1.1]">Receive a granular performance breakdown.</h2>
              <p className="text-lg text-muted-foreground leading-relaxed">
                Review your session with complete transparency. See exactly how your answers were scored against the literature, visualize your difficulty curve, and identify verified strengths alongside actionable gaps.
              </p>
            </div>
            <div className="relative group">
              <div className="absolute -inset-4 bg-accent/5 rounded-2xl blur-2xl group-hover:bg-accent/10 transition-colors duration-500"></div>
              <div className="bg-panel border border-hairline rounded-xl overflow-hidden shadow-2xl aspect-[16/10] relative z-10">
                <img src="/screenshots/summary.png" alt="Detailed Summary View" className="w-full h-full object-cover object-top" />
              </div>
            </div>
          </div>
        </section>

        {/* Feature 4: Dashboard */}
        <section className="py-24 lg:py-40 px-6 bg-panel/50 border-y border-hairline">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <div className="relative group lg:order-first order-last">
              <div className="absolute -inset-4 bg-accent/5 rounded-2xl blur-2xl group-hover:bg-accent/10 transition-colors duration-500"></div>
              <div className="bg-panel border border-hairline rounded-xl overflow-hidden shadow-2xl aspect-[16/10] relative z-10">
                <img src="/screenshots/dashboard.png" alt="Session History Dashboard" className="w-full h-full object-cover object-top" />
              </div>
            </div>
            <div className="max-w-xl lg:ml-auto">
              <span className="font-mono text-accent text-sm tracking-widest uppercase mb-6 block">04 // Track</span>
              <h2 className="text-4xl lg:text-5xl font-display tracking-tight mb-8 leading-[1.1]">Maintain a private record of your growth.</h2>
              <p className="text-lg text-muted-foreground leading-relaxed">
                Your session history stays with you. Revisit past interviews to review the literature, track your mastery over time, and prepare confidently without losing context from previous runs.
              </p>
            </div>
          </div>
        </section>
      </div>

      <section className="bg-panel py-20 overflow-hidden flex items-center justify-center relative z-10 border-t border-hairline">
        <span className="font-display text-7xl font-semibold tracking-[-0.08em] text-foreground md:text-9xl">VIVA</span>
      </section>
    </div>
  );
}
