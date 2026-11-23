import { useEffect, useState } from 'react'
import { api, type SessionSummary } from '../api'
import { SessionRow } from './Home'
import { plural } from '../components'

export default function History() {
  const [items, setItems] = useState<SessionSummary[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api.sessions().then(r => setItems(r.sessions)).catch(e => setErr(e.message)) }, [])

  const done = items?.filter(s => s.status === 'done' && s.overall != null) ?? []
  const avg = done.length ? Math.round(done.reduce((a, s) => a + (s.overall ?? 0), 0) / done.length) : null
  const recent = done.slice(0, 5)
  const prev = done.slice(5, 10)
  const trend = recent.length && prev.length
    ? Math.round(recent.reduce((a, s) => a + s.overall!, 0) / recent.length - prev.reduce((a, s) => a + s.overall!, 0) / prev.length)
    : null

  return (
    <div className="stack" style={{ gap: 20 }}>
      <h1>История</h1>
      {err && <div className="alert alert-bad" role="alert">{err}</div>}
      {items && items.length > 0 && (
        <div className="facts" style={{ maxWidth: 560 }}>
          <div className="fact"><b>{items.length}</b><span className="small muted">{plural(items.length, 'запись', 'записи', 'записей')}</span></div>
          {avg != null && <div className="fact"><b>{avg}</b><span className="small muted">средняя оценка</span></div>}
          {trend != null && <div className="fact"><b>{trend > 0 ? `+${trend}` : trend}</b><span className="small muted">последние 5 против предыдущих</span></div>}
        </div>
      )}
      {items === null && !err && <p className="muted">Загружаю…</p>}
      {items && items.length === 0 && (
        <div className="card stack">
          <p>Здесь будут все ваши записи и разборы.</p>
          <div><a className="btn btn-primary" href="#/record?mode=free">Записать первую</a></div>
        </div>
      )}
      {items && items.length > 0 && (
        <div className="card list" style={{ padding: 8 }}>
          {items.map(s => <SessionRow key={s.id} s={s} />)}
        </div>
      )}
    </div>
  )
}
