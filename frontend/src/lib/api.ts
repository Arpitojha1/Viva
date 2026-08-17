/// <reference types="vite/client" />
// src/lib/api.ts
// Production API client — connects to the FastAPI backend.
// All mock data has been removed. Real HTTP calls to VITE_API_BASE_URL.

export type Session = {
  id: string;
  role: string;
  status: 'active' | 'completed';
};

export type Question = {
  id: string;
  text: string;
  difficulty: 'Fundamentals' | 'Intermediate' | 'Advanced';
  source: {
    book: string;
    chapter: string;
    page: number;
    similarity: number;
  };
};

export type PerformanceSeriesItem = {
  orderIndex: number;
  difficulty: 'Fundamentals' | 'Intermediate' | 'Advanced';
  questionText: string;
  answerText: string;
  numericScore: number;
  qualityScore: string;
  scoreReasoning: string;
  chunkIds: number[];
};

export type Summary = {
  overallAssessment: string;
  strengths: string[];
  gaps: string[];
  scoreDistribution: { weak: number; ok: number; strong: number };
  difficultyTrend: number[]; // 1 | 2 | 3  (Fundamentals | Intermediate | Advanced)
  transcript: {
    question: Question;
    answer: string;
    score: number;
  }[];
  performanceSeries: PerformanceSeriesItem[];
};

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:8000/api';

// Module-level resume ID — set after upload, consumed by createSession.
// Survives component re-renders but resets on full page reload (acceptable for this build).
let _pendingResumeId: number | null = null;

// Frontend role slug → backend role string
const ROLE_MAP: Record<string, string> = {
  'ml-engineer': 'AI/ML Engineer',
  'data-scientist': 'Data Scientist',
  'backend-engineer': 'Backend Engineer',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API surface — matches the shape expected by UploadPage, InterviewPage, SummaryPage
// ---------------------------------------------------------------------------
export const api = {
  /**
   * Upload a PDF resume. Stores the returned resumeId internally so that
   * createSession (which doesn't receive resumeId from the component) can use it.
   */
  async uploadResume(
    file: File
  ): Promise<{ success: boolean; extractedSkills: string[] }> {
    const form = new FormData();
    form.append('file', file);

    // No Content-Type header — browser must set it with the correct multipart boundary.
    const res = await fetch(`${BASE_URL}/resume/upload`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(
        (body as { detail?: string }).detail ?? `HTTP ${res.status}`
      );
    }

    const data = (await res.json()) as {
      success: boolean;
      extractedSkills: string[];
      resumeId: number;
    };

    // Cache for createSession
    _pendingResumeId = data.resumeId;

    return { success: data.success, extractedSkills: data.extractedSkills };
  },

  /**
   * Create an interview session for the previously uploaded resume.
   * The frontend only passes `role` (e.g. 'ml-engineer') — we retrieve the
   * resumeId from module state and map the slug to the backend's display name.
   */
  async createSession(role: string): Promise<Session> {
    if (_pendingResumeId === null) {
      throw new Error(
        'No resume uploaded. Upload a resume before starting a session.'
      );
    }

    const backendRole = ROLE_MAP[role] ?? role;

    const data = await apiFetch<Session>('/session', {
      method: 'POST',
      body: JSON.stringify({ resumeId: _pendingResumeId, role: backendRole }),
    });

    return data;
  },

  /**
   * Get the next unanswered question for this session.
   * The `_index` parameter is accepted for interface compatibility but ignored —
   * the backend tracks progress server-side using order_index + answered state.
   *
   * Returns null when the interview is complete (404 or 409 from backend).
   */
  async getNextQuestion(
    sessionId: string,
    _index: number
  ): Promise<Question | null> {
    const res = await fetch(
      `${BASE_URL}/interview/${sessionId}/next-question`
    );

    // 404 = no more unanswered questions (complete)
    // 409 = session already marked completed
    if (res.status === 404 || res.status === 409) {
      return null;
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(
        (body as { detail?: string }).detail ?? `HTTP ${res.status}`
      );
    }

    const data = (await res.json()) as {
      id: string;
      text: string;
      difficulty: string;
      source: {
        book: string;
        chapter: string;
        page: number | null;
        similarity: number;
      };
    };

    return {
      id: data.id,
      text: data.text,
      difficulty: data.difficulty as Question['difficulty'],
      source: {
        book: data.source.book,
        chapter: data.source.chapter,
        page: data.source.page ?? 0,
        similarity: data.source.similarity,
      },
    };
  },

  /**
   * Submit the candidate's answer for scoring.
   * Returns numeric score (0–100) and the next difficulty level.
   */
  async submitAnswer(
    sessionId: string,
    questionId: string,
    answer: string
  ): Promise<{
    score: number;
    nextDifficulty: 'Fundamentals' | 'Intermediate' | 'Advanced';
  }> {
    const data = await apiFetch<{
      score: number;
      nextDifficulty: string;
      hasNextQuestion: boolean;
    }>(`/interview/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ questionId, answer }),
    });

    return {
      score: data.score,
      nextDifficulty: data.nextDifficulty as Question['difficulty'],
    };
  },

  /**
   * Retrieve the session summary (generated by Groq from stored Q&A records).
   */
  async getSummary(sessionId: string): Promise<Summary> {
    return apiFetch<Summary>(`/session/${sessionId}/summary`);
  },
};
