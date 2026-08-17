import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function HUD() {
  const [theme, setTheme] = useState<'L' | 'D'>('L');
  const location = useLocation();
  
  useEffect(() => {
    // Check initial theme
    if (document.documentElement.classList.contains('dark')) {
      setTheme('D');
    } else {
      setTheme('L');
    }
  }, []);
  
  const toggleTheme = () => {
    if (theme === 'L') {
      document.documentElement.classList.add('dark');
      setTheme('D');
    } else {
      document.documentElement.classList.remove('dark');
      setTheme('L');
    }
  };

  const isInterview = location.pathname.includes('/interview');
  const sessionMatch = location.pathname.match(/\/interview\/([^/]+)/) || location.pathname.match(/\/summary\/([^/]+)/);
  const sessionId = sessionMatch ? sessionMatch[1] : null;

  return (
    <header className="fixed top-0 inset-x-0 h-14 z-50 flex items-center justify-between px-6 border-b border-hairline bg-background/80 backdrop-blur-md">
      <div className="flex items-center space-x-2">
        <span className="font-display font-semibold tracking-tight text-sm">VIVA</span>
      </div>
      
      <div className="hidden md:flex flex-1 items-center justify-center">
         {/* Center space */}
      </div>

      <div className="flex items-center space-x-6 font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">
        
        <button onClick={() => location.pathname !== '/dashboard' && window.location.assign('/dashboard')} className="hover:text-foreground transition-colors cursor-pointer focus:outline-none">
          YOUR SESSION HISTORY
        </button>

        {sessionId ? (
          <div className="flex items-center space-x-2">
            <span className="flex items-center space-x-1">
              {isInterview && <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>}
              <span className={isInterview ? "text-accent" : ""}>{sessionId} · {isInterview ? 'ACTIVE' : 'COMPLETED'}</span>
            </span>
          </div>
        ) : null}
        
        <span className="hidden sm:inline">groq/llama-3.3-70b</span>
        
        {isInterview && (
          <span className="text-foreground">SIM 0.847</span>
        )}

        <button onClick={toggleTheme} className="hover:text-foreground transition-colors cursor-pointer focus:outline-none">
          THEME[{theme}]
        </button>
      </div>
    </header>
  );
}
