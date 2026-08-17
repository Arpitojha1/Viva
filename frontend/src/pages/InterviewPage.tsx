import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { api, Question } from '../lib/api';
import { MathText } from '../components/MathText';

export function InterviewPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [question, setQuestion] = useState<Question | null>(null);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showSource, setShowSource] = useState(false);
  const [difficulty, setDifficulty] = useState<'Fundamentals' | 'Intermediate' | 'Advanced'>('Fundamentals');
  const [difficultyAnim, setDifficultyAnim] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    loadQuestion(0);
  }, [sessionId]);

  const loadQuestion = async (idx: number) => {
    setIsLoading(true);
    setShowSource(false);
    setAnswer('');
    try {
      const q = await api.getNextQuestion(sessionId!, idx);
      if (!q) {
        navigate(`/summary/${sessionId}`);
        return;
      }
      setQuestion(q);
      setDifficulty(q.difficulty);
      setIndex(idx);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!answer.trim() || !question) return;
    setIsSubmitting(true);
    try {
      const res = await api.submitAnswer(sessionId!, question.id, answer);
      
      // Animate difficulty change if any
      if (res.nextDifficulty !== difficulty) {
        setDifficultyAnim(true);
        setTimeout(() => setDifficultyAnim(false), 2000);
      }
      
      await loadQuestion(index + 1);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !question) {
    return (
      <div className="min-h-[100dvh] pt-14 flex items-center justify-center">
        <div className="font-mono text-sm tracking-widest text-muted-foreground animate-pulse">FETCHING_NEXT_NODE...</div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] pt-24 px-6 pb-24 flex justify-center">
      <div className="w-full max-w-3xl space-y-8">
        
        {/* Top Meta Bar */}
        <div className="flex items-center justify-between border-b border-hairline pb-4">
          <div className="flex items-center space-x-4">
            <span className="font-mono text-sm">Q.{(index + 1).toString().padStart(2, '0')}</span>
            <div className="w-px h-4 bg-hairline" />
            <motion.div 
              animate={{ 
                scale: difficultyAnim ? [1, 1.1, 1] : 1, 
                color: difficultyAnim ? 'var(--accent)' : 'inherit' 
              }}
              className="flex items-center space-x-2"
            >
              <div className={`h-2 rounded-full ${difficulty === 'Fundamentals' ? 'w-4 bg-foreground' : difficulty === 'Intermediate' ? 'w-8 bg-accent' : 'w-12 bg-red-500'}`} />
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">{difficulty}</span>
            </motion.div>
          </div>
          <div className="text-xs font-mono text-muted-foreground">ADAPTIVE ENGINE: ONLINE</div>
        </div>

        {/* Question Area */}
        <AnimatePresence mode="wait">
          <motion.div 
            key={question?.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <h2 className="text-2xl md:text-3xl font-sans leading-relaxed">
              <MathText text={question?.text || ''} />
            </h2>

            {/* Source Citation Chip */}
            <div className="relative">
              <button 
                onClick={() => setShowSource(!showSource)}
                className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full border border-hairline bg-muted hover:bg-muted/80 transition-colors text-xs font-mono text-muted-foreground"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                <span>GROUNDING SOURCE</span>
              </button>
              
              <AnimatePresence>
                {showSource && question && (
                  <motion.div 
                    initial={{ opacity: 0, y: 5, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 5, scale: 0.95 }}
                    className="absolute top-10 left-0 w-80 p-4 glass-panel z-10 shadow-xl"
                  >
                    <div className="space-y-3">
                      <div className="text-[10px] font-mono text-muted-foreground uppercase border-b border-hairline pb-2">Retrieved Context</div>
                      <div className="space-y-1">
                        <div className="font-display font-medium text-sm">{question.source.book}</div>
                        <div className="text-xs text-muted-foreground">{question.source.chapter} — Page {question.source.page}</div>
                      </div>
                      <div className="pt-2 flex justify-between items-center text-[10px] font-mono border-t border-hairline/50">
                        <span>CONFIDENCE</span>
                        <span className="text-accent">{(question.source.similarity * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Input Area */}
        <div className="pt-8">
          <div className="relative glass-panel group focus-within:border-accent transition-colors">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Draft your response here..."
              disabled={isSubmitting}
              className="w-full min-h-[200px] bg-transparent p-6 outline-none resize-y text-base font-sans leading-relaxed disabled:opacity-50"
            />
            <div className="absolute bottom-4 right-4">
               <button 
                 onClick={handleSubmit}
                 disabled={!answer.trim() || isSubmitting}
                 className="px-6 py-2 bg-foreground text-background font-mono text-xs uppercase tracking-widest disabled:opacity-30 disabled:cursor-not-allowed hover:bg-foreground/90 transition-transform active:scale-95"
               >
                 {isSubmitting ? 'ANALYZING...' : 'SUBMIT'}
               </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
