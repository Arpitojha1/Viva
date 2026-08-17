import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, Summary } from '../lib/api';

type SessionData = {
  id: string;
  summary: Summary | null;
  error?: boolean;
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const stored = localStorage.getItem('viva_sessions');
        const sessionIds: string[] = stored ? JSON.parse(stored) : [];

        if (sessionIds.length === 0) {
          setSessions([]);
          setIsLoading(false);
          return;
        }

        const results = await Promise.allSettled(
          sessionIds.map(id => api.getSummary(id))
        );

        const loadedSessions = sessionIds.map((id, index) => {
          const result = results[index];
          if (result.status === 'fulfilled') {
            return { id, summary: result.value };
          } else {
            return { id, summary: null, error: true };
          }
        });

        // Reverse to show most recent first
        setSessions(loadedSessions.reverse());
      } catch (err) {
        console.error('Failed to load session history', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-[100dvh] pt-14 flex items-center justify-center">
        <div className="font-mono text-sm tracking-widest text-muted-foreground animate-pulse">LOADING_HISTORY...</div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] pt-24 px-6 pb-24 flex justify-center">
      <div className="w-full max-w-5xl space-y-12">
        
        {/* Header */}
        <div className="space-y-4 border-b border-hairline pb-8">
          <h1 className="text-4xl md:text-5xl font-display tracking-tight">Your Session History</h1>
          <p className="text-muted-foreground text-lg max-w-2xl leading-relaxed">
            A locally stored record of your completed interviews.
          </p>
        </div>

        {sessions.length === 0 ? (
          <div className="glass-panel p-12 text-center flex flex-col items-center justify-center space-y-6">
            <div className="w-16 h-16 border border-hairline rounded-full flex items-center justify-center text-muted-foreground opacity-50">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
              </svg>
            </div>
            <div className="space-y-2">
              <h3 className="font-display text-xl">No history yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Complete your first interview to see a detailed breakdown of your performance, verified strengths, and identified gaps.
              </p>
            </div>
            <button 
              onClick={() => navigate('/upload')}
              className="mt-4 px-6 py-3 bg-foreground text-background font-mono text-xs uppercase tracking-wider hover:bg-foreground/90 transition-transform active:scale-95"
            >
              Start an Interview
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => navigate(`/summary/${session.id}`)}
                className="workflow-card glass-panel p-6 flex flex-col items-start text-left w-full relative group overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {session.error || !session.summary ? (
                  <div className="flex-1 flex flex-col items-start justify-center text-muted-foreground w-full py-8">
                    <span className="font-mono text-xs uppercase mb-2">Session {session.id.slice(0, 8)}</span>
                    <span className="text-sm">Summary data unavailable.</span>
                  </div>
                ) : (
                  <>
                    <div className="w-full flex justify-between items-start mb-6 pb-4 border-b border-hairline/50">
                      <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                        ID: {session.id.slice(0, 8)}
                      </span>
                      <div className="flex items-center space-x-1 text-accent">
                        <span className="font-mono text-xs">VIEW</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="group-hover:translate-x-1 transition-transform">
                          <line x1="5" y1="12" x2="19" y2="12" />
                          <polyline points="12 5 19 12 12 19" />
                        </svg>
                      </div>
                    </div>
                    
                    <h3 className="text-lg font-display tracking-tight mb-3 line-clamp-2 pr-4">
                      {session.summary.overallAssessment.split('.')[0]}.
                    </h3>
                    
                    <div className="mt-auto pt-4 flex flex-wrap gap-2 w-full">
                      <span className="font-mono text-[9px] uppercase border border-hairline px-2 py-1 rounded-full text-green-500 bg-green-500/10">
                        {session.summary.strengths.length} STRENGTHS
                      </span>
                      <span className="font-mono text-[9px] uppercase border border-hairline px-2 py-1 rounded-full text-red-400 bg-red-400/10">
                        {session.summary.gaps.length} GAPS
                      </span>
                    </div>
                  </>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
