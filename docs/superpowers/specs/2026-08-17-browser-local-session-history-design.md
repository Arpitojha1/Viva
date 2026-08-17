# Browser-local session history

## Goal

Add a calm, scalable session-history page without writing user identity or history associations to the backend database.

## Scope

The dashboard records only this browser's Viva sessions in `localStorage` and opens the existing summary UI. It does not implement authentication, create users, alter session ownership, add API endpoints, or modify the database schema.

## Data model

Use a versioned local-storage record scoped by a generated anonymous browser ID:

```ts
type LocalSessionRecord = {
  sessionId: string;
  resumeName: string | null;
  role: string;
  createdAt: string;
  status: 'active' | 'completed';
  overallScore: number | null;
};
```

The browser ID and records remain entirely client-side. Clearing site storage clears dashboard history; records are not available on another device or browser profile.

## Flow

1. After a successful `createSession`, the upload flow stores a local record.
2. When a summary loads, it updates the matching record to `completed` and derives the overall score from its performance series.
3. `/history` renders records in a semantic table, newest first by default, with an explicit date sort control.
4. Clicking a row navigates to the existing `/summary/:sessionId` route. No second summary UI is created.
5. An empty state explains that history is private to this browser and offers a route back to upload.

## UI

The dashboard uses the existing token system, fixed grid alignment, monospace data, and bordered row list. It is dense enough for many sessions, responsive with a compact mobile row layout, and avoids a card grid. The auth panel remains an optional UI-only offer and does not gate or affect history.

## Error handling and privacy

Malformed local-storage data is discarded safely. A deleted/unavailable session remains visible with an unavailable state rather than breaking the page. No resume contents, answers, email address, or authentication material is written to local storage by this feature.

## Verification

- Unit-test local registry read/write, sorting, completion updates, malformed data recovery, and browser-ID initialization.
- Type-check and production-build the frontend.
- Verify empty, active, completed, and unavailable history rows in light and dark themes.
- Verify reduced-motion behavior remains unchanged because the dashboard uses no new motion.

## Review

No placeholders, backend dependencies, or ambiguous ownership paths remain. This is intentionally a browser-local history feature, not deferred authentication by another name.
