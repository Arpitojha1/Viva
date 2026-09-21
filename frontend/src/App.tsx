/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { Analytics } from '@vercel/analytics/react';
import { HUD } from './components/HUD';

const LandingPage = lazy(() => import('./pages/LandingPage').then(m => ({ default: m.LandingPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then(m => ({ default: m.UploadPage })));
const InterviewPage = lazy(() => import('./pages/InterviewPage').then(m => ({ default: m.InterviewPage })));
const SummaryPage = lazy(() => import('./pages/SummaryPage').then(m => ({ default: m.SummaryPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));

const SuspenseFallback = () => (
  <div className="min-h-[100dvh] pt-14 flex items-center justify-center">
    <div className="font-mono text-xs tracking-widest text-muted-foreground animate-pulse">LOADING_MODULE...</div>
  </div>
);

export default function App() {
  return (
    <Router>
      <HUD />
      <main className="pt-14 min-h-[100dvh] hud-grid">
        <Suspense fallback={<SuspenseFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/interview/:sessionId" element={<InterviewPage />} />
            <Route path="/summary/:sessionId" element={<SummaryPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </Suspense>
      </main>
      <SpeedInsights />
      <Analytics />
    </Router>
  );
}
