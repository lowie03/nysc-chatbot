import { useState, useCallback } from 'react'
import { askBot } from './api'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [pending, setPending] = useState(false)

  const send = useCallback(async (question) => {
    const q = question.trim()
    if (!q || pending) return

    setMessages((m) => [...m, { role: 'me', text: q }])
    setPending(true)
    try {
      const { answer, tier, sources, followups } = await askBot(q)
      setMessages((m) => [...m, { role: 'bot', text: answer, tier, sources, followups }])
    } catch {
      setMessages((m) => [...m, {
        role: 'bot',
        text: "Couldn't reach the server. Check that uvicorn is running, then ask again.",
        tier: 'REFUSE',
        sources: [],
        followups: [],
      }])
    } finally {
      setPending(false)
    }
  }, [pending])

  return { messages, pending, send }
}
