export async function askBot(question) {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error(`Server returned ${res.status}`)
  return res.json()   // { answer, tier }
}
