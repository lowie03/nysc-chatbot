const API_BASE = import.meta.env.VITE_API_URL ?? ''   // '' = same origin (Render)

export async function askBot(question) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error(`Server returned ${res.status}`)
  return res.json()   // { answer, tier }
}
