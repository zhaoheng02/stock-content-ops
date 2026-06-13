// In production (Vercel) the API is same-origin, so default to "" (relative /api/*).
// For local dev against the Python server, set VITE_API_BASE_URL=http://127.0.0.1:8787
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
