import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { HeroScene } from '../components/HeroScene';
import StrokeText from '../components/StrokeText';
import WarpText from '../components/WarpText';

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

  return (
    <div className="relative w-full">
      {/* Hero Section */}
      <section className="relative h-[100dvh] flex items-center px-6 lg:px-24">
        <HeroScene />

        
        <div className="relative z-10 max-w-3xl">
          <h1 className="text-5xl md:text-7xl font-display tracking-tight leading-[1.1] mb-6">
            Interview questions grounded in real ML textbooks, adapted to you.
          </h1>
          <p className="text-lg text-muted-foreground mb-10 max-w-xl">
            A specialized RAG screening system that retrieves authoritative machine learning literature and tailors adaptive scenarios to your experience.
          </p>
          <button 
            onClick={() => navigate('/upload')}
            className="px-8 py-4 bg-foreground text-background font-mono text-sm uppercase tracking-wider hover:bg-foreground/90 transition-transform active:scale-95"
          >
            Start Interview
          </button>
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
      <section className="py-32 px-6 lg:px-24 border-t border-hairline bg-panel relative z-10">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="glass-panel p-8 flex flex-col items-start hover:-translate-y-1 transition-transform duration-300">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">01</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Upload Resume</h3>
             <p className="text-sm text-muted-foreground">System extracts key skills and maps them to our ML knowledge graph.</p>
          </div>
          <div className="glass-panel p-8 flex flex-col items-start hover:-translate-y-1 transition-transform duration-300">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">02</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Adaptive Q&A</h3>
             <p className="text-sm text-muted-foreground">Answer questions with live scoring that adjusts subsequent difficulty.</p>
          </div>
          <div className="glass-panel p-8 flex flex-col items-start hover:-translate-y-1 transition-transform duration-300">
             <div className="w-10 h-10 border border-hairline rounded-full flex items-center justify-center mb-6">
                <span className="font-mono text-xs text-muted-foreground">03</span>
             </div>
             <h3 className="text-xl font-display tracking-tight mb-2">Detailed Summary</h3>
             <p className="text-sm text-muted-foreground">Receive a comprehensive breakdown of strengths, gaps, and citation sources.</p>
          </div>
        </div>
      </section>

      {/* VIVA Warp Text Footer */}
      <section className="bg-foreground text-background py-16 overflow-hidden flex items-center justify-center relative z-10 border-t border-hairline">
        <WarpText
          text="VIVA"
          color="#f8fafc"
          warpStrength={0.08}
          warpScale={1.7}
          speed={0.55}
          pointerInfluence={0.42}
          pointerStrength={0.38}
          refraction={0.018}
          ripple
          fontSize="clamp(5rem, 15vw, 15rem)"
          fontWeight={800}
          style={{ height: '320px', width: '100%' }}
        />
      </section>
    </div>
  );
}
