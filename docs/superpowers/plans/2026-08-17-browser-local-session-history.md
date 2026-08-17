# Browser-local Session History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browser-local session-history dashboard that reuses the existing summary route without creating user records or backend history associations.

**Architecture:** A focused `sessionHistory` library owns the anonymous browser ID and versioned localStorage registry. Upload and summary pages write lifecycle events to it. A new HistoryPage displays local entries in a sortable table and opens existing summary URLs.

**Tech Stack:** React 19, TypeScript, React Router 7, Tailwind CSS v4, localStorage, Node test runner using the existing tsx dependency.

## Global Constraints

- Persist only a public session token, role, resume filename, created time, local status, and derived score.
- Do not add API endpoints, database fields, user rows, or session-to-user associations.
- Never persist resume contents, answers, email, or authentication material.
- Default to newest-first date order and reuse `/summary/:sessionId`.
- Preserve current tokens, fixed grid alignment, dark mode, and reduced-motion behavior.

---

### Task 1: Implement the local registry

**Files:**
- Create: `frontend/src/lib/sessionHistory.ts`
- Create: `frontend/src/lib/sessionHistory.test.ts`
- Modify: `frontend/package.json`

**Interfaces:** Produces `LocalSessionRecord`, `createSessionHistoryStore`, `recordLocalSession`, `listLocalSessions`, `markLocalSessionCompleted`, and `sortSessionsByDate`. Consumes a `Storage` instance; browser helpers use `window.localStorage` only in browser code.

- [ ] **Step 1: Write the failing test**

```ts
import assert from 'node:assert/strict';
import test from 'node:test';
import { createSessionHistoryStore, sortSessionsByDate } from './sessionHistory';

test('stores one anonymous browser identity and returns newest records first', () => {
  const data = new Map<string, string>();
  const storage = { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => data.set(key, value), removeItem: (key: string) => data.delete(key) } as Storage;
  const store = createSessionHistoryStore(storage, () => 'browser-local-id');
  store.record({ sessionId: 'older', role: 'AI/ML Engineer', resumeName: 'old.pdf', createdAt: '2026-08-01T10:00:00.000Z' });
  store.record({ sessionId: 'newer', role: 'AI/ML Engineer', resumeName: null, createdAt: '2026-08-02T10:00:00.000Z' });
  store.markCompleted('newer', 82);
  assert.equal(store.getBrowserId(), 'browser-local-id');
  assert.deepEqual(store.list().map(({ sessionId, status, overallScore }) => ({ sessionId, status, overallScore })), [{ sessionId: 'newer', status: 'completed', overallScore: 82 }, { sessionId: 'older', status: 'active', overallScore: null }]);
});

test('recovers from malformed storage and sorts without mutation', () => {
  const storage = { getItem: () => '{broken', setItem: () => undefined, removeItem: () => undefined } as Storage;
  assert.deepEqual(createSessionHistoryStore(storage, () => 'id').list(), []);
  const source = [{ createdAt: '2026-08-01T00:00:00.000Z' }, { createdAt: '2026-08-02T00:00:00.000Z' }];
  assert.equal(sortSessionsByDate(source, 'oldest')[0].createdAt, '2026-08-01T00:00:00.000Z');
  assert.equal(source[0].createdAt, '2026-08-01T00:00:00.000Z');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --import tsx --test src/lib/sessionHistory.test.ts`

Expected: FAIL because `./sessionHistory` does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
export type LocalSessionRecord = { sessionId: string; role: string; resumeName: string | null; createdAt: string; status: 'active' | 'completed'; overallScore: number | null; };
export function createSessionHistoryStore(storage: Storage, makeId = crypto.randomUUID) {
  // Read viva.browser-id.v1 and viva.session-history.v1 defensively.
  // Upsert records by sessionId and return sorted copied arrays.
}
```

Add the package script `"test": "node --import tsx --test src/lib/sessionHistory.test.ts"`.

- [ ] **Step 4: Run test and type-check to verify green**

Run: `npm test && npm run lint`

Expected: both commands PASS.

- [ ] **Step 5: Commit**

Run: `git add frontend/src/lib/sessionHistory.ts frontend/src/lib/sessionHistory.test.ts frontend/package.json && git commit -m "feat: add browser-local session registry"`

### Task 2: Record existing session lifecycle events

**Files:**
- Modify: `frontend/src/pages/UploadPage.tsx`
- Modify: `frontend/src/pages/SummaryPage.tsx`
- Test: `frontend/src/lib/sessionHistory.test.ts`

**Interfaces:** Upload consumes `recordLocalSession({ sessionId, role, resumeName, createdAt })`. Summary consumes `markLocalSessionCompleted(sessionId, score)`. Both produce only local metadata and leave API requests unchanged.

- [ ] **Step 1: Extend the failing test**

```ts
test('upserts a repeated public session token', () => {
  const store = createSessionHistoryStore(memoryStorage(), () => 'id');
  const record = { sessionId: 'token', role: 'AI/ML Engineer', resumeName: 'cv.pdf', createdAt: '2026-08-02T10:00:00.000Z' };
  store.record(record); store.record(record);
  assert.equal(store.list().length, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`

Expected: FAIL until `record` upserts by `sessionId`.

- [ ] **Step 3: Add the lifecycle calls**

```ts
const session = await api.createSession(role);
recordLocalSession({ sessionId: session.id, role: session.role, resumeName: file?.name ?? null, createdAt: new Date().toISOString() });
navigate(`/interview/${session.id}`);
```

In SummaryPage, calculate `Math.round(total / performanceSeries.length)` only when the series is non-empty, then call `markLocalSessionCompleted(sessionId, score)`. Never save summary, transcript, assessment, or answers.

- [ ] **Step 4: Run test and type-check to verify green**

Run: `npm test && npm run lint`

Expected: both commands PASS.

- [ ] **Step 5: Commit**

Run: `git add frontend/src/pages/UploadPage.tsx frontend/src/pages/SummaryPage.tsx frontend/src/lib/sessionHistory.test.ts && git commit -m "feat: record local session lifecycle"`

### Task 3: Create the history page and route

**Files:**
- Create: `frontend/src/pages/HistoryPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/HUD.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:** Consumes `listLocalSessions()` and `LocalSessionRecord`. Produces `/history`, date sorting, an explicit empty state, and row navigation to `/summary/:sessionId`.

- [ ] **Step 1: Write the failing rendering-support test**

```ts
test('sorts active and completed records by date in either direction', () => {
  const records = [{ sessionId: 'a', createdAt: '2026-08-01T00:00:00.000Z' }, { sessionId: 'b', createdAt: '2026-08-02T00:00:00.000Z' }];
  assert.deepEqual(sortSessionsByDate(records, 'newest').map((record) => record.sessionId), ['b', 'a']);
  assert.deepEqual(sortSessionsByDate(records, 'oldest').map((record) => record.sessionId), ['a', 'b']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`

Expected: FAIL until `sortSessionsByDate` accepts both directions.

- [ ] **Step 3: Implement page, route, and navigation**

```tsx
<Route path="/history" element={<HistoryPage />} />

<table>
  <thead><tr><th>Session</th><th>Resume</th><th>Date</th><th>Score</th><th>Status</th></tr></thead>
  <tbody>{rows.map((record) => (
    <tr key={record.sessionId} onClick={() => navigate(`/summary/${record.sessionId}`)} />
  ))}</tbody>
</table>
```

Use a real date-sort button with `aria-pressed`, an empty-state link to `/upload`, and a HUD History link outside interview routes. Use desktop table borders with compact mobile grid rows. Do not create a card grid or second summary UI.

- [ ] **Step 4: Run automated verification**

Run: `npm test && npm run lint && npm run build`

Expected: all commands PASS.

- [ ] **Step 5: Run visual verification**

1. Open `/history` with empty local storage; confirm its empty state makes no API call.
2. Add two records through upload or browser storage; confirm newest-first and oldest-first sorting.
3. Click a row and confirm the existing `/summary/:sessionId` page opens.
4. Compare light and dark screenshots; verify content aligns to the 64px grid.
5. Enable reduced motion; confirm the page adds no animation.

- [ ] **Step 6: Commit**

Run: `git add frontend/src/pages/HistoryPage.tsx frontend/src/App.tsx frontend/src/components/HUD.tsx frontend/src/index.css frontend/src/lib/sessionHistory.ts frontend/src/lib/sessionHistory.test.ts && git commit -m "feat: add local session history dashboard"`

## Self-review

- Spec coverage: registry, anonymous browser scope, no database identity, local lifecycle tracking, date sorting, existing-summary reuse, empty state, light/dark, and reduced motion all have explicit tasks.
- Placeholder scan: no TBD/TODO markers or undefined interfaces remain.
- Type consistency: pages consume the exact record and helper names introduced by Task 1.
