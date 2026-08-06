const serverApiUrl =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

async function getJson(path) {
  const response = await fetch(`${serverApiUrl}${path}`, {
    cache: "no-store",
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
  return getJson(`/api/v1/tenders/${id}`);
}
