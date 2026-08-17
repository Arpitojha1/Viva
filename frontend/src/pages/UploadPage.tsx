import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../lib/api';

export function UploadPage() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [extractedSkills, setExtractedSkills] = useState<string[] | null>(null);
  const [role, setRole] = useState('ml-engineer');
  const [isStarting, setIsStarting] = useState(false);
  const isStartingRef = useRef(false);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFile = async (selectedFile: File) => {
    if (selectedFile.type !== 'application/pdf') {
      alert('Please upload a PDF file.');
      return;
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      alert('File size must be under 5MB.');
      return;
    }
    
    setFile(selectedFile);
    setIsUploading(true);
    
    try {
      const res = await api.uploadResume(selectedFile);
      if (res.success) {
        setExtractedSkills(res.extractedSkills);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to parse resume');
      setFile(null);
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleStart = async () => {
    if (isStartingRef.current) return;
    isStartingRef.current = true;
    setIsStarting(true);
    try {
      const session = await api.createSession(role);
      navigate(`/interview/${session.id}`);
    } catch (error) {
      console.error(error);
      isStartingRef.current = false;
      setIsStarting(false);
    }
  };

  return (
    <div className="min-h-[100dvh] pt-14 flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl space-y-12">
        
        {/* Header */}
        <div className="space-y-4 text-center">
          <h1 className="text-3xl md:text-5xl font-display tracking-tight">System Calibration</h1>
          <p className="text-muted-foreground">Upload your resume to ground the interview context.</p>
        </div>

        {/* Role Selector */}
        <div className="space-y-4">
          <div className="text-xs font-mono uppercase tracking-widest text-muted-foreground border-b border-hairline pb-2">Target Role</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <label className={`glass-panel p-4 flex items-center space-x-3 cursor-pointer transition-colors ${role === 'ml-engineer' ? 'border-accent bg-accent/5' : 'hover:bg-muted'}`}>
              <input type="radio" name="role" value="ml-engineer" checked={role === 'ml-engineer'} onChange={() => setRole('ml-engineer')} className="hidden" />
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${role === 'ml-engineer' ? 'border-accent' : 'border-muted-foreground'}`}>
                {role === 'ml-engineer' && <div className="w-2 h-2 bg-accent rounded-full" />}
              </div>
              <span className="font-display font-medium text-sm">AI/ML Engineer</span>
            </label>
            <label className="glass-panel p-4 flex items-center space-x-3 opacity-50 cursor-not-allowed">
              <input type="radio" name="role" value="data-scientist" disabled className="hidden" />
              <div className="w-4 h-4 rounded-full border border-muted-foreground" />
              <div className="flex flex-col">
                <span className="font-display font-medium text-sm">Data Scientist</span>
                <span className="text-[10px] font-mono text-muted-foreground uppercase">Coming Soon</span>
              </div>
            </label>
            <label className="glass-panel p-4 flex items-center space-x-3 opacity-50 cursor-not-allowed">
              <input type="radio" name="role" value="backend-engineer" disabled className="hidden" />
              <div className="w-4 h-4 rounded-full border border-muted-foreground" />
              <div className="flex flex-col">
                 <span className="font-display font-medium text-sm">Backend Eng</span>
                 <span className="text-[10px] font-mono text-muted-foreground uppercase">Coming Soon</span>
              </div>
            </label>
          </div>
        </div>

        {/* Upload Area */}
        <div className="space-y-4">
           <div className="text-xs font-mono uppercase tracking-widest text-muted-foreground border-b border-hairline pb-2">Context Document</div>
           
           {!file ? (
             <label
               onDragOver={onDragOver}
               onDragLeave={onDragLeave}
               onDrop={onDrop}
               className={`block w-full border-2 border-dashed ${isDragging ? 'border-accent bg-accent/5' : 'border-hairline hover:border-muted-foreground'} glass-panel transition-colors cursor-pointer rounded-none p-12 text-center`}
             >
               <input type="file" accept=".pdf" className="hidden" onChange={onFileChange} />
               <div className="flex flex-col items-center space-y-4">
                 <div className="w-12 h-12 rounded-full border border-hairline flex items-center justify-center bg-muted">
                   <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" strokeLinejoin="miter">
                     <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                     <polyline points="17 8 12 3 7 8" />
                     <line x1="12" y1="3" x2="12" y2="15" />
                   </svg>
                 </div>
                 <div className="space-y-1">
                   <p className="font-display font-medium">Click to upload or drag and drop</p>
                   <p className="text-xs text-muted-foreground font-mono">PDF ONLY (MAX. 5MB)</p>
                 </div>
               </div>
             </label>
           ) : (
             <div className="glass-panel p-6 border-accent/30 bg-accent/5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                    <span className="font-mono text-sm truncate max-w-[200px]">{file.name}</span>
                  </div>
                  {isUploading ? (
                     <span className="font-mono text-xs text-muted-foreground animate-pulse">PARSING...</span>
                  ) : (
                     <button onClick={() => { setFile(null); setExtractedSkills(null); }} className="text-xs font-mono text-muted-foreground hover:text-foreground underline">REMOVE</button>
                  )}
                </div>

                <AnimatePresence>
                  {extractedSkills && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="pt-4 border-t border-hairline/50"
                    >
                      <div className="text-[10px] font-mono text-muted-foreground mb-3 uppercase">Entities Detected</div>
                      <div className="flex flex-wrap gap-2">
                        {extractedSkills.map(skill => (
                          <span key={skill} className="px-2 py-1 text-xs border border-hairline bg-background rounded-full">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
             </div>
           )}
        </div>

        {/* Action */}
        <div className="flex justify-end pt-8">
           <button
             disabled={!extractedSkills || isStarting}
             onClick={handleStart}
             className="px-8 py-4 bg-foreground text-background font-mono text-sm uppercase tracking-wider hover:bg-foreground/90 disabled:opacity-50 disabled:cursor-not-allowed transition-transform active:scale-95 flex items-center space-x-2"
           >
             {isStarting ? <span>INITIALIZING...</span> : <span>BEGIN INTERVIEW</span>}
             {!isStarting && (
               <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                 <line x1="5" y1="12" x2="19" y2="12" />
                 <polyline points="12 5 19 12 12 19" />
               </svg>
             )}
           </button>
        </div>

      </div>
    </div>
  );
}
