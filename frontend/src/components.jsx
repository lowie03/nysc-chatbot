function Source({ source }) {
  if (source.url) {
    return (
      <a className="source" href={source.url} target="_blank" rel="noreferrer">
        {source.label}
      </a>
    )
  }
  if (source.phone) {
    return <a className="source" href={`tel:${source.phone}`}>{source.label}</a>
  }
  return <span className="source">{source.label}</span>
}

function Sources({ sources }) {
  if (!sources || sources.length === 0) return null
  return (
    <div className="sources">
      {sources.map((s, i) => <Source key={i} source={s} />)}
    </div>
  )
}

function Followups({ followups, onPick }) {
  if (!followups || followups.length === 0) return null
  return (
    <div className="followups">
      {followups.map((f) => (
        <button key={f.label} className="chip" onClick={() => onPick(f.query)}>{f.label}</button>
      ))}
    </div>
  )
}

export function Message({ msg, onPick }) {
  if (msg.role === 'me') return <div className="msg me">{msg.text}</div>

  return (
    <div className="msg bot">
      <p>{msg.text}</p>
      <Sources sources={msg.sources} />
      <Followups followups={msg.followups} onPick={onPick} />
    </div>
  )
}
