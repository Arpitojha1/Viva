import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3001';

const MOCK_SUMMARY = {
  overallAssessment: "Strong fundamental knowledge of machine learning concepts with some gaps in practical deployment architectures.",
  strengths: ["Gradient Descent Optimization", "Neural Network Architecture", "Overfitting Prevention"],
  gaps: ["Model Serving", "Distributed Training"],
  scoreDistribution: { weak: 1, ok: 2, strong: 5 },
  difficultyTrend: [1, 2, 2, 3, 2, 3, 3, 3],
  transcript: [
    {
      question: { id: "q1", text: "Explain how dropout prevents overfitting.", difficulty: "Intermediate", source: { book: "Deep Learning", chapter: "7.12", page: 255, similarity: 0.95 } },
      answer: "Dropout randomly zeroes out hidden units during training, acting as an ensemble method.",
      score: 95
    }
  ],
  performanceSeries: [
    { orderIndex: 1, difficulty: "Fundamentals", questionText: "What is a neural network?", answerText: "A series of layers", numericScore: 85, qualityScore: "Good", scoreReasoning: "Basic but correct", chunkIds: [] },
    { orderIndex: 2, difficulty: "Intermediate", questionText: "Explain dropout", answerText: "It zeroes out weights", numericScore: 95, qualityScore: "Excellent", scoreReasoning: "Core mechanism identified", chunkIds: [] },
    { orderIndex: 3, difficulty: "Advanced", questionText: "How does batch norm affect gradients?", answerText: "It normalizes them", numericScore: 60, qualityScore: "Fair", scoreReasoning: "Incomplete explanation", chunkIds: [] }
  ]
};

const MOCK_QUESTION = {
  id: "q123",
  text: "How would you design a recommendation system for a highly sparse dataset where user-item interactions are rare?",
  difficulty: "Advanced",
  source: {
    book: "Designing Machine Learning Systems",
    chapter: "Chapter 4: Training Data",
    page: 112,
    similarity: 0.88
  }
};

async function takeScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: 'dark' // Use dark mode
  });
  const page = await context.newPage();

  // Mock API Routes
  await page.route('**/api/session/*/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_SUMMARY)
    });
  });

  await page.route('**/api/interview/*/next-question', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_QUESTION)
    });
  });

  console.log('Capturing Upload Page...');
  await page.goto(`${BASE_URL}/upload`);
  await page.waitForTimeout(1000); // Wait for animations
  await page.screenshot({ path: 'public/screenshots/upload.png' });

  console.log('Capturing Interview Page...');
  // Force a session id to avoid redirect
  await page.goto(`${BASE_URL}/interview/mock-session-123`);
  await page.waitForTimeout(2000); // Wait for GSAP and text reveal
  await page.screenshot({ path: 'public/screenshots/interview.png' });

  console.log('Capturing Summary Page...');
  await page.goto(`${BASE_URL}/summary/mock-session-123`);
  await page.waitForTimeout(2000); // Wait for charts to render
  await page.screenshot({ path: 'public/screenshots/summary.png' });

  console.log('Capturing Dashboard Page...');
  // Set localStorage first
  await page.goto(`${BASE_URL}/`);
  await page.evaluate(() => {
    localStorage.setItem('viva_sessions', JSON.stringify(['mock-1', 'mock-2', 'mock-3']));
  });
  // The dashboard will fetch the summary for these 3 mocks and use MOCK_SUMMARY
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'public/screenshots/dashboard.png' });

  await browser.close();
  console.log('Done!');
}

takeScreenshots().catch(console.error);
