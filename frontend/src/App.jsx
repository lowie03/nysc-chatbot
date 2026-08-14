import { useState, useEffect, useRef } from 'react'
import { useChat } from './useChat'
import { Message } from './components'
import EmptyState from './EmptyState'
import './index.css'

function Mark() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2 2 7l10 5 10-5-10-5Z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 19V5" />
      <path d="M5 12l7-7 7 7" />
    </svg>
  )
}

function Conversation() {
  const { messages, pending, send } = useChat()
  const [draft, setDraft] = useState('')
  const logRef = useRef(null)
  const isEmpty = messages.length === 0

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, pending])

  function submit(e) {
    e.preventDefault()
    send(draft)
    setDraft('')
  }

  return (
    <>
      <div className="log" ref={logRef} role="log" aria-live="polite">
        {isEmpty ? (
          <EmptyState onPick={send} />
        ) : (
          <div className="log-inner">
            {messages.map((m, i) => <Message key={i} msg={m} onPick={send} />)}
            {pending && <div className="msg bot"><p className="dots">Checking my records</p></div>}
          </div>
        )}
      </div>

      <form className="composer" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type your question"
          aria-label="Your question"
          autoComplete="off"
        />
        <button type="submit" className="send" disabled={pending || !draft.trim()} aria-label="Send">
          <SendIcon />
        </button>
      </form>

      {isEmpty && (
        <p className="fineprint">
          Answers come from official NYSC sources. If something isn't in the data, you'll be told where to check.
        </p>
      )}
    </>
  )
}

export default function App() {
  const [sessionKey, setSessionKey] = useState(0)

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <Mark />
          <span>Corper desk</span>
        </div>
        <button className="new-question" onClick={() => setSessionKey((k) => k + 1)}>
          New question
        </button>
      </header>

      <Conversation key={sessionKey} />
    </>
  )
}
