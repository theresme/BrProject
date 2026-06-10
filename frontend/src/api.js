export async function fetchState() {
  const r = await fetch("/api/state", { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
