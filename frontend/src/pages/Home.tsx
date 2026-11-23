import { useEffect, useState } from 'react'
import { api, fmtDate, MODE_TITLES, type Health, type Session, type SessionSummary } from '../api'
import type { Catalog } from '../App'
import { Icon, ScoreBadge } from '../components'
import { go } from '../router'

export default function Home({ catalog }: { catalog: Catalog }) {
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null)
  const [last, setLast] = useState<Session | null>(null)
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    api.sessions().then(r => {
      setSessions(r.sessions)
      const done = r.sessions.find(s => s.status === 'done')
      if (done) api.session(done.id).then(setLast).catch(() => undefined)
    }).catch(() => setSessions([]))
    api.health().then(setHealth).catch(() => undefined)
  }, [])

  const next = last?.report ? catalog.byId[last.report.feedback.next_exercise_id] : catalog.byId['talk-intro']
  const twister = catalog.exercises.filter(e => e.kind === 'tongue_twister')
  const randomTwister = () => twister[Math.floor(Math.random() * twister.length)]

  return (
    <>
      <section className="hero">
        <div>
          <h1>Минута на камеру — и честный разбор</h1>
          <p className="hero-lead">Запишите короткую речь. Златоуст посчитает темп, паузы, слова-паразиты, интонацию, взгляд и жесты и скажет, что улучшить в первую очередь.</p>
          <a className="btn btn-primary btn-lg" href="#/record?mode=free"><Icon name="mic" />Записать минуту</a>
        </div>
        {next && (
          <div className="card next-card stack" aria-labelledby="next-title">
            <span className="chip chip-accent" style={{ alignSelf: 'flex-start' }}>{last ? 'Следующее по плану' : 'С чего начать'}</span>
            <h2 id="next-title">{next.title}</h2>
            <p className="muted">{next.text}</p>
            {last?.report?.feedback.next_exercise_why && <p className="small muted">{last.report.feedback.next_exercise_why}</p>}
            <div><a className="btn" href={`#/record?ex=${next.id}`}>Начать упражнение<Icon name="arrow" size={18} /></a></div>
          </div>
        )}
      </section>

      <h2 className="sr-only">Режимы тренировки</h2>
      <div className="modes">
        <button className="mode-card" onClick={() => go('#/record?mode=free')}>
          <span className="mode-icon"><Icon name="mic" /></span>
          <h3>Свободная речь</h3>
          <p className="muted small">Говорите на любую тему или на случайную, которую предложит приложение.</p>
        </button>
        <button className="mode-card" onClick={() => go('#/record?ex=read-intonation')}>
          <span className="mode-icon"><Icon name="text" /></span>
          <h3>Чтение с суфлёра</h3>
          <p className="muted small">Свой или готовый текст на экране. Тренирует интонацию, дикцию и взгляд в камеру.</p>
        </button>
        <button className="mode-card" onClick={() => go(`#/record?ex=${randomTwister().id}`)}>
          <span className="mode-icon"><Icon name="bolt" /></span>
          <h3>Скороговорка</h3>
          <p className="muted small">Короткий текст для дикции. Сравним с оригиналом и покажем, какие слова прозвучали нечётко.</p>
        </button>
      </div>

      <section aria-labelledby="recent-title">
        <div className="section-title">
          <h2 id="recent-title">Последние записи</h2>
          {sessions && sessions.length > 0 && <a href="#/history">Вся история</a>}
        </div>
        {sessions === null && <p className="muted">Загружаю…</p>}
        {sessions && sessions.length === 0 && (
          <div className="card"><p className="muted">Записей пока нет. Первая займёт минуту, а разбор будет готов через одну-две.</p></div>
        )}
        {sessions && sessions.length > 0 && (
          <div className="card list" style={{ padding: 8 }}>
            {sessions.slice(0, 5).map(s => <SessionRow key={s.id} s={s} />)}
          </div>
        )}
      </section>

      {health && (
        <p className="small muted" style={{ marginTop: 24 }}>
          Распознавание речи: {health.gpu ? 'на видеокарте' : 'на процессоре (медленнее)'} · Разбор: {health.llm === 'anthropic' ? 'Claude' : health.llm === 'ollama' ? 'локальная модель' : 'по правилам, без ИИ'} · <a href="#/settings">Настройки</a>
        </p>
      )}
    </>
  )
}

export function SessionRow({ s }: { s: SessionSummary }) {
  const status =
    s.status === 'done' ? null
    : s.status === 'error' ? <span className="chip chip-bad">Ошибка</span>
    : <span className="chip chip-accent">Анализ…</span>
  return (
    <a className="list-item" href={`#/session/${s.id}`}>
      <ScoreBadge score={s.overall} />
      <div>
        <div style={{ fontWeight: 600 }}>{s.title || MODE_TITLES[s.mode]}</div>
        <div className="small muted">{fmtDate(s.created_at)}{s.duration ? ` · ${Math.round(s.duration)} с` : ''}</div>
      </div>
      {status}
    </a>
  )
}
