function greetingForHour(hour) {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

const CARDS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="6" width="18" height="13" rx="2" />
        <path d="M3 10h18" />
        <circle cx="15.5" cy="14.5" r="1.5" />
      </svg>
    ),
    title: 'What will I be paid?',
    description: 'Federal allowance plus what your state adds.',
    question: 'How much is the NYSC allowance?',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 21s7-6.1 7-11.5A7 7 0 0 0 5 9.5C5 14.9 12 21 12 21Z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>
    ),
    title: 'Where is my camp?',
    description: 'Orientation camp address for any state.',
    question: 'Where is the orientation camp in Imo state?',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="5" y="4" width="14" height="17" rx="2" />
        <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
        <path d="M9 11h6M9 15h6M9 19h3" />
      </svg>
    ),
    title: 'What do I need to register?',
    description: 'Documents, photo rules and the call-up fee.',
    question: 'What documents do I need to register?',
  },
]

export default function EmptyState({ onPick }) {
  const greeting = greetingForHour(new Date().getHours())

  return (
    <div className="empty-state">
      <h2>{greeting}, corper.</h2>
      <p className="subtitle">Ask about registration, camp, allowance or your posting.</p>

      <div className="card-grid">
        {CARDS.map((c) => (
          <button key={c.title} className="prompt-card" onClick={() => onPick(c.question)}>
            <span className="prompt-icon">{c.icon}</span>
            <span className="prompt-title">{c.title}</span>
            <span className="prompt-desc">{c.description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
