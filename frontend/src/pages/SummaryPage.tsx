import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { api, Summary, PerformanceSeriesItem } from '../lib/api';
import { MathText } from '../components/MathText';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceDot, Scatter } from 'recharts';

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
            <h3 className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-6 border-b border-hairline/50 pb-2">Adaptive Difficulty & Performance Trend</h3>
            <div className="flex-1 w-full min-h-[200px] pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={summary.performanceSeries} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--hairline)" vertical={false} />
                  <XAxis 
                    dataKey="orderIndex" 
                    tickFormatter={(val) => `Q${val + 1}`}
                    stroke="var(--muted-foreground)" 
                    fontSize={10} 
                    tickLine={false} 
                    axisLine={false} 
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    stroke="var(--muted-foreground)" 
                    fontSize={10} 
                    tickLine={false} 
                    axisLine={false} 
                    tickCount={5}
                  />
                  <Tooltip 
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload as PerformanceSeriesItem;
                        return (
                          <div className="bg-background/95 backdrop-blur-md p-4 text-xs space-y-3 border border-accent/30 max-w-sm shadow-2xl rounded-sm">
                            <div className="flex justify-between items-center font-mono border-b border-hairline pb-2">
                              <span className="text-muted-foreground uppercase tracking-widest text-[10px]">Q{data.orderIndex + 1} ({data.difficulty})</span>
                              <span className={`font-bold ${data.numericScore >= 90 ? 'text-green-400' : data.numericScore >= 65 ? 'text-accent' : 'text-red-400'}`}>
                                SCORE: {data.numericScore}
                              </span>
                            </div>
                            <div>
                              <div className="text-[10px] font-mono text-muted-foreground mb-1 uppercase">Question</div>
                              <div className="line-clamp-2 text-foreground/90 font-sans leading-relaxed"><MathText text={data.questionText} /></div>
                            </div>
                            <div className="font-mono text-[10px] text-muted-foreground pt-2 border-t border-hairline/30">
                              <span className="uppercase text-[9px] mb-1 block">Feedback:</span>
                              <span className="line-clamp-3">{data.scoreReasoning}</span>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="numericScore" 
                    stroke="var(--accent)" 
                    strokeWidth={2}
                    activeDot={{ r: 6, fill: "var(--accent)", stroke: "var(--background)", strokeWidth: 2 }}
                    dot={{ r: 4, fill: "var(--background)", stroke: "var(--accent)", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
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
