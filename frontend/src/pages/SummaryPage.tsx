import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { api, Summary } from '../lib/api';
import { MathText } from '../components/MathText';

export function SummaryPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedQ, setExpandedQ] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    
    const fetchSummary = async () => {
      setIsLoading(true);
      try {
        const data = await api.getSummary(sessionId);
        setSummary(data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchSummary();
  }, [sessionId]);

  if (isLoading || !summary) {
    return (
      <div className="min-h-[100dvh] pt-14 flex items-center justify-center">
        <div className="font-mono text-sm tracking-widest text-muted-foreground animate-pulse">COMPILING_REPORT...</div>
      </div>
    );
  }

  // Simple Chart calculation
  const maxDifficulty = 3;
  const chartHeight = 100;
  
  return (
    <div className="min-h-[100dvh] pt-24 px-6 pb-24 flex justify-center">
      <div className="w-full max-w-4xl space-y-12">
        
        {/* Header */}
        <div className="space-y-4 border-b border-hairline pb-8">
          <div className="font-mono text-xs text-accent uppercase tracking-widest">Session Concluded</div>
          <h1 className="text-4xl md:text-5xl font-display tracking-tight">Performance Summary</h1>
          <p className="text-muted-foreground text-lg max-w-2xl leading-relaxed">{summary.overallAssessment}</p>
        </div>

        {/* Top Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Strengths / Gaps */}
          <div className="glass-panel p-6 space-y-6">
            <div>
              <h3 className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-3 border-b border-hairline/50 pb-2">Verified Strengths</h3>
              <ul className="space-y-2">
                {summary.strengths.map(s => (
                  <li key={s} className="flex items-start space-x-2 text-sm">
                    <span className="text-green-500 mt-0.5">✓</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
               <h3 className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-3 border-b border-hairline/50 pb-2">Identified Gaps</h3>
               <ul className="space-y-2">
                 {summary.gaps.map(g => (
                   <li key={g} className="flex items-start space-x-2 text-sm">
                     <span className="text-red-500 mt-0.5">×</span>
                     <span>{g}</span>
                   </li>
                 ))}
               </ul>
            </div>
          </div>

          {/* Difficulty Trend Chart */}
          <div className="glass-panel p-6 flex flex-col">
            <h3 className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-6 border-b border-hairline/50 pb-2">Adaptive Difficulty Trend</h3>
            <div className="flex-1 relative flex items-end justify-between pt-4 pb-2">
               {/* Y-Axis lines */}
               <div className="absolute inset-x-0 bottom-2 top-4 flex flex-col justify-between pointer-events-none opacity-20">
                 <div className="border-t border-hairline w-full" />
                 <div className="border-t border-hairline w-full" />
                 <div className="border-t border-hairline w-full" />
               </div>
               
               {/* Trend Line (Simple SVG) */}
               <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                 <polyline 
                   points={summary.difficultyTrend.map((val, i) => {
                     const x = (summary.difficultyTrend.length > 1) 
                       ? (i / (summary.difficultyTrend.length - 1)) * 100 
                       : 50;
                     const y = 100 - ((val - 1) / (maxDifficulty - 1)) * 100;
                     return `${x},${y}`;
                   }).join(' ')}
                   fill="none"
                   stroke="var(--accent)"
                   strokeWidth="2"
                   vectorEffect="non-scaling-stroke"
                 />
                 {summary.difficultyTrend.map((val, i) => {
                     const x = (summary.difficultyTrend.length > 1) 
                       ? (i / (summary.difficultyTrend.length - 1)) * 100 
                       : 50;
                     const y = 100 - ((val - 1) / (maxDifficulty - 1)) * 100;
                     return (
                       <circle key={i} cx={x} cy={y} r="2" fill="var(--accent)" vectorEffect="non-scaling-stroke" />
                     );
                 })}
               </svg>
            </div>
            <div className="flex justify-between font-mono text-[10px] text-muted-foreground mt-2">
              <span>START</span>
              <span>END</span>
            </div>
          </div>

        </div>

        {/* Transcript */}
        <div className="space-y-6 pt-8">
          <h3 className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest border-b border-hairline pb-2">Full Transcript</h3>
          
          <div className="space-y-4">
            {summary.transcript.map((item, i) => (
              <div key={i} className="glass-panel overflow-hidden">
                <button 
                  onClick={() => setExpandedQ(expandedQ === item.question.id ? null : item.question.id)}
                  className="w-full text-left p-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center space-x-4 pr-4">
                    <span className="font-mono text-xs text-muted-foreground">Q.{i+1}</span>
                    <span className="font-display font-medium text-sm line-clamp-1">
                      <MathText text={item.question.text || ''} />
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 shrink-0">
                    <span className="font-mono text-[10px] uppercase border border-hairline px-2 py-0.5 rounded-full">SCORE: {item.score}</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`transition-transform ${expandedQ === item.question.id ? 'rotate-180' : ''}`}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                </button>
                
                {expandedQ === item.question.id && (
                  <div className="p-4 pt-0 border-t border-hairline/30 bg-muted/20 space-y-6 mt-2">
                    <div className="pt-4">
                      <div className="text-[10px] font-mono text-muted-foreground mb-1 uppercase">Source Grounding</div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {item.question.source.book} — {item.question.source.chapter}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] font-mono text-muted-foreground mb-2 uppercase">Your Response</div>
                      <p className="text-sm font-sans leading-relaxed text-foreground/90">{item.answer}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="pt-12 pb-8 flex justify-center">
           <button 
             onClick={() => navigate('/')}
             className="px-6 py-3 border border-hairline font-mono text-xs uppercase hover:bg-muted transition-colors"
           >
             Return to Home
           </button>
        </div>

      </div>
    </div>
  );
}
