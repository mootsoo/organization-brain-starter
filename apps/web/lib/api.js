// Server-side data access for the Next.js pages.
//
// INTERNAL_API_URL is used inside Docker Compose (service name `api`).
// NEXT_PUBLIC_API_URL is the address the browser uses and is also the
// fallback when the app runs outside Compose.

const serverApiUrl =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const REQUEST_TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS || 8000);

async function getJson(path) {
  const response = await fetch(`${serverApiUrl}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export function getOverview() {
  return getJson("/api/v1/overview");
}

export function getTender(id) {
  return getJson(`/api/v1/tenders/${encodeURIComponent(id)}`);
}
