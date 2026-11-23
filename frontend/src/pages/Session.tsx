import { useEffect, useMemo, useRef, useState } from 'react'
import { api, fmtDate, fmtTime, MODE_TITLES, type Session, type Skill, type Word } from '../api'
import type { Catalog } from '../App'
import { Icon, Ring, scoreColor, scoreWord } from '../components'
import { go } from '../router'

const STAGES: { key: string; label: string }[] = [
  { key: 'audio', label: 'Извлекаю звук' },
  { key: 'transcribe', label: 'Распознаю речь' },
  { key: 'voice', label: 'Анализирую темп и голос' },
  { key: 'video', label: 'Смотрю на взгляд, позу и жесты' },
  { key: 'feedback', label: 'Готовлю разбор' },
]

export default function SessionPage({ id, catalog }: { id: string; catalog: Catalog }) {
  const [s, setS] = useState<Session | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let stop = false
    let timer: ReturnType<typeof setTimeout>
    const load = async () => {
      try {
        const r = await api.session(id)
        if (stop) return
        setS(r)
        if (r.status === 'queued' || r.status === 'processing') timer = setTimeout(load, 1000)
      } catch (e) {
        if (!stop) setErr((e as Error).message)
      }
    }
    load()
    return () => { stop = true; clearTimeout(timer) }
  }, [id])

  if (err) return <div className="alert alert-bad" role="alert">{err}</div>
  if (!s) return <p className="muted">Загружаю…</p>
  if (s.status === 'queued' || s.status === 'processing') return <Processing s={s} />
  if (s.status === 'error') return (
    <div className="card stack" style={{ maxWidth: 640 }}>
      <h1>Не получилось разобрать запись</h1>
      <p className="muted">{s.error}</p>
      <div className="row">
        <button className="btn btn-primary" onClick={() => api.retry(s.id).then(() => setS({ ...s, status: 'queued', progress: 0 }))}><Icon name="retry" size={18} />Попробовать ещё раз</button>
        <a className="btn" href="#/record">Записать заново</a>
      </div>
    </div>
  )
  return <ReportView s={s} catalog={catalog} />
}

function Processing({ s }: { s: Session }) {
  const idx = s.stage ? STAGES.findIndex(x => x.key === s.stage) : -1
  return (
    <div className="card stack" style={{ maxWidth: 560, margin: '40px auto', padding: 32 }} aria-live="polite">
      <h1>Разбираю запись</h1>
      <p className="muted">{s.status === 'queued' ? 'Запись в очереди. Разбор начнётся через пару секунд.' : 'Обычно это занимает одну-две минуты. Можно не ждать: разбор появится в истории.'}</p>
      <div className="bar" role="progressbar" aria-label="Ход анализа" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(s.progress * 100)}>
        <div style={{ width: `${Math.max(3, s.progress * 100)}%` }} />
      </div>
      <ol className="steps">
        {STAGES.map((st, i) => (
          <li key={st.key} className={i < idx ? 'done' : i === idx ? 'active' : ''}>
            <span className="step-icon">{i < idx && <Icon name="check" size={14} />}</span>{st.label}
          </li>
        ))}
      </ol>
      {s.stage === 'transcribe' && <p className="hint">При первом запуске модель распознавания загружается в память — это дольше обычного.</p>}
    </div>
  )
}

function ReportView({ s, catalog }: { s: Session; catalog: Catalog }) {
  const rep = s.report!
  const m = s.metrics!
  const video = useRef<HTMLVideoElement>(null)
  const [now, setNow] = useState(0)
  const seek = (t: number | null) => {
    if (t == null || !video.current) return
    video.current.currentTime = Math.max(0, t - 0.5)
    video.current.play().catch(() => undefined)
    video.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  const next = catalog.byId[rep.feedback.next_exercise_id]
  const again = s.exercise_id ? `#/record?ex=${s.exercise_id}` : `#/record?mode=${s.mode}`
  const sp = m.speech
  const v = m.video

  const remove = async () => {
    if (!window.confirm('Удалить эту запись и её разбор? Отменить будет нельзя.')) return
    await api.remove(s.id)
    go('#/history')
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div>
        <a href="#/history" className="small">← История</a>
      </div>
      <section className="card report-head">
        <Ring score={rep.overall} />
        <div className="stack" style={{ gap: 8 }}>
          <div className="row small muted">
            <span>{s.title || MODE_TITLES[s.mode]}</span>·<span>{fmtDate(s.created_at)}</span>
            {s.duration && <>·<span>{Math.round(s.duration)} с</span></>}
          </div>
          <h1 style={{ fontSize: '1.6rem' }}>{rep.overall != null ? `${scoreWord(rep.overall)[0].toUpperCase()}${scoreWord(rep.overall).slice(1)}` : 'Оценки нет'}</h1>
          <p style={{ maxWidth: '70ch' }}>{rep.feedback.summary}</p>
          <div className="row">
            <span className="chip">{rep.provider === 'rules' ? 'Разбор по правилам' : rep.provider === 'anthropic' ? 'Разбор: Claude' : 'Разбор: локальная модель'}</span>
            {rep.llm_error && <span className="chip chip-warn" title={rep.llm_error}>ИИ был недоступен</span>}
          </div>
        </div>
        <div className="stack" style={{ gap: 8 }}>
          {next && <a className="btn btn-primary" href={`#/record?ex=${next.id}`}>Следующее упражнение<Icon name="arrow" size={18} /></a>}
          <a className="btn" href={again}><Icon name="retry" size={18} />Повторить</a>
        </div>
      </section>

      <div className="report-grid">
        <div className="stack" style={{ gap: 24 }}>
          <section className="card player stack">
            <h2 className="sr-only">Видео</h2>
            <video ref={video} src={api.videoUrl(s.id)} controls preload="metadata" onTimeUpdate={e => setNow(e.currentTarget.currentTime)} />
          </section>

          {m.diction && <DictionCard d={m.diction} />}

          <section className="card stack" aria-labelledby="tr-title">
            <div className="section-title" style={{ marginBottom: 0 }}>
              <h2 id="tr-title">Расшифровка</h2>
            </div>
            <div className="legend">
              <span><span className="chip chip-warn">ну</span> слово-паразит</span>
              <span><span style={{ textDecoration: 'underline dotted', textUnderlineOffset: 4 }}>слово</span> распознано неуверенно</span>
              <span>Нажмите на слово, чтобы перейти к этому месту</span>
            </div>
            <Transcript words={rep.words} now={now} onSeek={seek} />
          </section>
        </div>

        <div className="stack" style={{ gap: 24 }}>
          <section className="card stack" aria-labelledby="sk-title">
            <h2 id="sk-title">Навыки</h2>
            {rep.scores.slice().sort((a, b) => a.score - b.score).map(x => (
              <div className="skill-row" key={x.skill} style={{ color: scoreColor(x.score) }}>
                <span style={{ color: 'var(--text)' }}>{x.title}</span>
                <div className="bar" aria-hidden><div style={{ width: `${x.score}%` }} /></div>
                <span className="skill-num">{x.score}<span className="sr-only"> из 100</span></span>
              </div>
            ))}
          </section>

          {rep.feedback.improvements.length > 0 && (
            <section className="card stack" aria-labelledby="imp-title">
              <h2 id="imp-title">Что улучшить</h2>
              <ul className="tips">
                {rep.feedback.improvements.map((i, k) => (
                  <li className="tip" key={k}>
                    <div>
                      <div className="row" style={{ gap: 8, justifyContent: 'space-between', flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                        <span>{i.problem}</span>
                        {i.t != null && <button className="time-chip" onClick={() => seek(i.t)} aria-label={`Перейти к ${fmtTime(i.t)}`}>{fmtTime(i.t)}</button>}
                      </div>
                      {i.how_to_fix && <p className="tip-fix small">{i.how_to_fix}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {rep.feedback.strengths.length > 0 && (
            <section className="card stack" aria-labelledby="good-title">
              <h2 id="good-title">Что получилось</h2>
              <ul className="tips">
                {rep.feedback.strengths.map((t, k) => <li className="tip good" key={k}><span>{t}</span></li>)}
              </ul>
            </section>
          )}

          <section className="card stack" aria-labelledby="facts-title">
            <h2 id="facts-title">В цифрах</h2>
            <div className="facts">
              {sp.syllables_per_sec != null && <Fact v={Number(sp.syllables_per_sec).toFixed(1)} l="слога в секунду" />}
              {sp.words_per_min != null && <Fact v={`${Math.round(sp.words_per_min)}`} l="слов в минуту" />}
              {sp.fillers_per_min != null && <Fact v={Number(sp.fillers_per_min).toFixed(1)} l="паразитов в минуту" />}
              {sp.pause_ratio != null && <Fact v={`${Math.round(sp.pause_ratio * 100)}%`} l="времени на паузы" />}
              {m.prosody.pitch_std_st != null && <Fact v={Number(m.prosody.pitch_std_st).toFixed(1)} l="разброс тона, полутона" />}
              {v.eye_contact_ratio != null && <Fact v={`${Math.round(v.eye_contact_ratio * 100)}%`} l="взгляд в камеру" />}
              {v.gesture_active_ratio != null && <Fact v={`${Math.round(v.gesture_active_ratio * 100)}%`} l="времени с жестами" />}
            </div>
            <p className="hint">Распознавание: {rep.asr.model} на {rep.asr.device === 'cuda' ? 'видеокарте' : 'процессоре'}.{v.video === false && ' Видео не проанализировано.'}</p>
          </section>

          <details className="card">
            <summary>Все замечания программы</summary>
            <ul className="tips" style={{ marginTop: 14 }}>
              {rep.observations.map((o, k) => (
                <li key={k} className={`tip ${o.level === 'good' ? 'good' : ''}`}>
                  <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                    <span><b>{catalog.skills[o.skill as Skill]}.</b> {o.text}</span>
                    {o.t != null && <button className="time-chip" onClick={() => seek(o.t)}>{fmtTime(o.t)}</button>}
                  </div>
                </li>
              ))}
            </ul>
          </details>
          <div><button className="btn btn-sm btn-ghost" onClick={remove}><Icon name="trash" size={16} />Удалить запись</button></div>
        </div>
      </div>
    </div>
  )
}

function Fact({ v, l }: { v: string; l: string }) {
  return <div className="fact"><b>{v.replace('.', ',')}</b><span className="small muted">{l}</span></div>
}

function Transcript({ words, now, onSeek }: { words: Word[]; now: number; onSeek: (t: number) => void }) {
  const items = useMemo(() => words.map((w, i) => ({ ...w, gap: i > 0 ? w.s - words[i - 1].e : 0 })), [words])
  if (!words.length) return <p className="muted">Речь не распознана.</p>
  return (
    <p className="transcript">
      {items.map((w, i) => (
        <span key={i}>
          {w.gap >= 1 && <span className="pause" aria-label={`пауза ${w.gap.toFixed(1)} секунды`}>· {w.gap.toFixed(1).replace('.', ',')} с ·</span>}
          <span
            className={`w${w.f ? ' filler' : ''}${w.lc ? ' lc' : ''}${now >= w.s && now <= w.e + 0.1 ? ' now' : ''}`}
            role="button" tabIndex={0}
            onClick={() => onSeek(w.s + 0.5)}
            onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSeek(w.s + 0.5))}
          >{w.w}</span>{' '}
        </span>
      ))}
    </p>
  )
}

function DictionCard({ d }: { d: NonNullable<NonNullable<Session['metrics']>['diction']> }) {
  return (
    <section className="card stack" aria-labelledby="dic-title">
      <div className="section-title" style={{ marginBottom: 0 }}>
        <h2 id="dic-title">Дикция</h2>
        <span className="chip" style={{ color: scoreColor(d.accuracy * 100) }}>Совпало {Math.round(d.accuracy * 100)}% текста</span>
      </div>
      <p className="diff transcript">
        {d.ops.filter(o => o.op !== 'ins').map((o, i) => (
          <span key={i}>
            <span className={o.op} title={o.op === 'sub' ? `Услышано: «${o.hyp}»` : o.op === 'del' ? 'Не прозвучало' : undefined}>{o.ref}</span>
            {o.op === 'sub' && <span className="small muted"> ({o.hyp})</span>}{' '}
          </span>
        ))}
      </p>
      <p className="hint">Красным — слова, которые программа не услышала так, как написано. В скобках — что услышала. Распознавание иногда ошибается само: проверьте по видео.</p>
    </section>
  )
}
