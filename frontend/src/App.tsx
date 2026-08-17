/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { HUD } from './components/HUD';
import { LandingPage } from './pages/LandingPage';
import { UploadPage } from './pages/UploadPage';
import { InterviewPage } from './pages/InterviewPage';
import { SummaryPage } from './pages/SummaryPage';

export default function App() {
  return (
    <Router>
      <HUD />
      <main className="pt-14 min-h-[100dvh] hud-grid">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/interview/:sessionId" element={<InterviewPage />} />
          <Route path="/summary/:sessionId" element={<SummaryPage />} />
        </Routes>
      </main>
    </Router>
  );
}
