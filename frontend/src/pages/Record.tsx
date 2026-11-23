import { useCallback, useEffect, useRef, useState } from 'react'
import { api, fmtTime, modeForExercise, type Exercise, type Mode } from '../api'
import type { Catalog } from '../App'
import { Icon } from '../components'
import { go } from '../router'

type Phase = 'starting' | 'ready' | 'countdown' | 'recording' | 'uploading' | 'error'

const DURATIONS = [30, 60, 90, 120]
const LS = { cam: 'zl.camera', mic: 'zl.mic', dur: 'zl.duration' }

function pickMime(): string {
  const c = ['video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9,opus', 'video/webm', 'video/mp4']
  return c.find(m => MediaRecorder.isTypeSupported(m)) ?? ''
}

function cameraError(e: unknown): string {
  const name = (e as DOMException)?.name
  if (name === 'NotAllowedError') return 'Нет доступа к камере или микрофону. Разрешите доступ в запросе браузера или в настройках Windows: Конфиденциальность → Камера и Микрофон.'
  if (name === 'NotFoundError') return 'Камера или микрофон не найдены. Подключите устройство и нажмите «Повторить».'
  if (name === 'NotReadableError') return 'Камера занята другой программой (Zoom, Teams, OBS). Закройте её и нажмите «Повторить».'
  return `Не удалось включить камеру: ${(e as Error)?.message ?? e}`
}

export default function Record({ catalog, exerciseId, mode: modeParam }: { catalog: Catalog; exerciseId?: string; mode?: string }) {
  const initialEx = exerciseId ? catalog.byId[exerciseId] ?? null : null
  const topics = catalog.exercises.filter(e => e.kind === 'topic')
  const [exercise, setExercise] = useState<Exercise | null>(initialEx)
  const mode: Mode = exercise ? modeForExercise(exercise) : ((modeParam as Mode) || 'free')
  const [text, setText] = useState(initialEx && initialEx.kind !== 'topic' ? initialEx.text : '')
  const [phase, setPhase] = useState<Phase>('starting')
  const [error, setError] = useState<string | null>(null)
  const [devices, setDevices] = useState<{ cams: MediaDeviceInfo[]; mics: MediaDeviceInfo[] }>({ cams: [], mics: [] })
  const [camId, setCamId] = useState(() => localStorage.getItem(LS.cam) ?? '')
  const [micId, setMicId] = useState(() => localStorage.getItem(LS.mic) ?? '')
  const [duration, setDuration] = useState(() => Number(localStorage.getItem(LS.dur)) || (initialEx?.kind === 'tongue_twister' ? 30 : 60))
  const [count, setCount] = useState(3)
  const [elapsed, setElapsed] = useState(0)
  const [level, setLevel] = useState(0)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const startedAt = useRef(0)
  const audioCtx = useRef<AudioContext | null>(null)
  const cancelled = useRef(false)

  const showPrompter = mode === 'reading' || mode === 'tongue_twister' || (mode === 'topic' && !!exercise)
  const prompterText = mode === 'topic' ? exercise?.text ?? '' : text

  // Камера и микрофон
  const startStream = useCallback(async () => {
    setPhase('starting')
    setError(null)
    streamRef.current?.getTracks().forEach(t => t.stop())
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: camId ? { ideal: camId } : undefined, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
        // Обработку звука выключаем: она искажает громкость и паузы, которые мы меряем.
        audio: { deviceId: micId ? { ideal: micId } : undefined, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      const all = await navigator.mediaDevices.enumerateDevices()
      setDevices({ cams: all.filter(d => d.kind === 'videoinput'), mics: all.filter(d => d.kind === 'audioinput') })

      audioCtx.current?.close()
      const ctx = new AudioContext()
      audioCtx.current = ctx
      const an = ctx.createAnalyser()
      an.fftSize = 1024
      ctx.createMediaStreamSource(stream).connect(an)
      const buf = new Float32Array(an.fftSize)
      const tick = () => {
        if (ctx.state === 'closed') return
        an.getFloatTimeDomainData(buf)
        let peak = 0
        for (const v of buf) peak = Math.max(peak, Math.abs(v))
        setLevel(l => Math.max(peak, l * 0.85))
        requestAnimationFrame(tick)
      }
      tick()
      setPhase('ready')
    } catch (e) {
      setError(cameraError(e))
      setPhase('error')
    }
  }, [camId, micId])

  useEffect(() => {
    startStream()
  }, [startStream])

  useEffect(() => () => {
    cancelled.current = true
    recRef.current?.state === 'recording' && recRef.current.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
    audioCtx.current?.close()
  }, [])

  const begin = () => {
    if (phase !== 'ready') return
    setCount(3)
    setPhase('countdown')
  }

  useEffect(() => {
    if (phase !== 'countdown') return
    if (count === 0) {
      startRecording()
      return
    }
    const t = setTimeout(() => setCount(c => c - 1), 800)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, count])

  const startRecording = () => {
    const stream = streamRef.current
    if (!stream) return
    chunks.current = []
    const mime = pickMime()
    const rec = new MediaRecorder(stream, { mimeType: mime || undefined, videoBitsPerSecond: 2_500_000, audioBitsPerSecond: 128_000 })
    rec.ondataavailable = e => e.data.size && chunks.current.push(e.data)
    rec.onstop = () => {
      if (cancelled.current) {
        cancelled.current = false
        return
      }
      upload(new Blob(chunks.current, { type: rec.mimeType || 'video/webm' }))
    }
    rec.start(1000)
    recRef.current = rec
    startedAt.current = performance.now()
    setElapsed(0)
    setPhase('recording')
  }

  const stop = useCallback(() => {
    if (recRef.current?.state === 'recording') recRef.current.stop()
  }, [])

  const cancel = () => {
    if (phase === 'recording') {
      cancelled.current = true
      recRef.current?.stop()
    }
    setPhase('ready')
  }

  useEffect(() => {
    if (phase !== 'recording') return
    const t = setInterval(() => {
      const s = (performance.now() - startedAt.current) / 1000
      setElapsed(s)
      if (s >= duration) stop()
    }, 200)
    return () => clearInterval(t)
  }, [phase, duration, stop])

  const upload = async (blob: Blob) => {
    setPhase('uploading')
    try {
      const { id } = await api.upload(blob, mode, exercise, mode === 'reading' || mode === 'tongue_twister' ? text : undefined)
      go(`#/session/${id}`)
    } catch (e) {
      setError(`Не удалось сохранить запись: ${(e as Error).message}`)
      setPhase('error')
    }
  }

  // Пробел — старт/стоп, Esc — отмена
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'TEXTAREA' || tag === 'INPUT' || tag === 'SELECT') return
      if (e.code === 'Space') {
        e.preventDefault()
        if (phase === 'ready') begin()
        else if (phase === 'recording') stop()
      } else if (e.code === 'Escape' && (phase === 'recording' || phase === 'countdown')) cancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const busy = phase === 'countdown' || phase === 'recording' || phase === 'uploading'
  const left = Math.max(0, duration - elapsed)
  const scrollPct = phase === 'recording' ? Math.min(1, elapsed / (duration * 0.9)) : 0

  const title = exercise?.title ?? (mode === 'reading' ? 'Чтение с суфлёра' : 'Свободная речь')

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div>
          <a href="#/" className="small">← На главную</a>
          <h1 style={{ marginTop: 4 }}>{title}</h1>
        </div>
      </div>

      <div className="rec-layout">
        <div className="stack">
          <div className="stage">
            <video ref={videoRef} autoPlay muted playsInline aria-label="Изображение с камеры" />
            {phase === 'starting' && <div className="stage-empty">Включаю камеру…</div>}
            {phase === 'error' && (
              <div className="stage-empty">
                <div className="stack" style={{ alignItems: 'center', maxWidth: 460 }}>
                  <p>{error}</p>
                  <button className="btn" onClick={startStream}><Icon name="retry" size={18} />Повторить</button>
                </div>
              </div>
            )}
            {showPrompter && prompterText && phase !== 'error' && (
              <div className="prompter" aria-live="off">
                <div className="prompter-inner" style={{ transform: `translateY(-${scrollPct * 55}%)` }}>{prompterText}</div>
              </div>
            )}
            {phase === 'countdown' && <div className="countdown" aria-live="assertive">{count || ''}</div>}
            {(phase === 'recording' || phase === 'uploading') && (
              <div className="hud">
                <span className="rec-pill">
                  {phase === 'recording' ? <><span className="rec-dot" aria-hidden />{fmtTime(elapsed)}</> : 'Сохраняю…'}
                </span>
                <div className="progress-line" role="progressbar" aria-label="Прошло времени" aria-valuemin={0} aria-valuemax={duration} aria-valuenow={Math.round(elapsed)}>
                  <div style={{ width: `${Math.min(100, (elapsed / duration) * 100)}%` }} />
                </div>
                <span className="rec-pill">−{fmtTime(left)}</span>
              </div>
            )}
          </div>

          <div className="row" style={{ justifyContent: 'center' }}>
            {phase !== 'recording' && phase !== 'countdown' && (
              <button className="btn btn-rec btn-lg" onClick={begin} disabled={phase !== 'ready'}>
                <span className="dot" aria-hidden style={{ background: '#fff' }} />Начать запись
              </button>
            )}
            {phase === 'countdown' && <button className="btn btn-lg" onClick={cancel}>Отменить</button>}
            {phase === 'recording' && (
              <>
                <button className="btn btn-primary btn-lg" onClick={stop} disabled={elapsed < 5}>
                  <span aria-hidden style={{ width: 14, height: 14, background: 'currentColor', borderRadius: 3 }} />Закончить и получить разбор
                </button>
                <button className="btn btn-lg btn-ghost" onClick={cancel}>Отменить</button>
              </>
            )}
          </div>
          <p className="small muted" style={{ textAlign: 'center' }}>
            <kbd className="kbd">Пробел</kbd> — начать или закончить, <kbd className="kbd">Esc</kbd> — отменить. Запись остановится сама через {duration} с.
          </p>
        </div>

        <aside className="stack">
          {mode === 'free' && !exercise && (
            <div className="card stack" style={{ gap: 12 }}>
              <h2>О чём говорить</h2>
              <p className="muted">Говорите о чём угодно. Если нужна идея — возьмите тему.</p>
              <button className="btn btn-sm" disabled={busy} onClick={() => setExercise(topics[Math.floor(Math.random() * topics.length)])}>Предложить тему</button>
            </div>
          )}
          {exercise && (
            <div className="card stack" style={{ gap: 10 }}>
              <h2>Задание</h2>
              {mode === 'topic' && <p>{exercise.text}</p>}
              <p className="muted small">{exercise.how}</p>
              {mode === 'topic' && (
                <div className="row">
                  <button className="btn btn-sm" disabled={busy} onClick={() => {
                    const rest = topics.filter(t => t.id !== exercise.id)
                    setExercise(rest[Math.floor(Math.random() * rest.length)])
                  }}>Другая тема</button>
                  <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => setExercise(null)}>Без темы</button>
                </div>
              )}
            </div>
          )}
          {(mode === 'reading' || mode === 'tongue_twister') && (
            <div className="card field">
              <label htmlFor="ref-text">Текст на экране</label>
              <textarea id="ref-text" value={text} onChange={e => setText(e.target.value)} disabled={busy} />
              <span className="hint">По этому тексту проверим дикцию. Можно вставить свой.</span>
            </div>
          )}

          <div className="card stack" style={{ gap: 14 }}>
            <h2>Перед записью</h2>
            <div className="field">
              <span className="label" id="dur-label">Длительность</span>
              <div className="segmented" role="group" aria-labelledby="dur-label">
                {DURATIONS.map(d => (
                  <button key={d} aria-pressed={duration === d} disabled={busy} onClick={() => { setDuration(d); localStorage.setItem(LS.dur, String(d)) }}>
                    {d < 60 ? `${d} с` : d === 60 ? '1 мин' : `${String(d / 60).replace(".", ",")} мин`}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label htmlFor="cam">Камера</label>
              <select id="cam" value={camId} disabled={busy} onChange={e => { setCamId(e.target.value); localStorage.setItem(LS.cam, e.target.value) }}>
                <option value="">По умолчанию</option>
                {devices.cams.map(d => <option key={d.deviceId} value={d.deviceId}>{d.label || 'Камера'}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="mic">Микрофон</label>
              <select id="mic" value={micId} disabled={busy} onChange={e => { setMicId(e.target.value); localStorage.setItem(LS.mic, e.target.value) }}>
                <option value="">По умолчанию</option>
                {devices.mics.map(d => <option key={d.deviceId} value={d.deviceId}>{d.label || 'Микрофон'}</option>)}
              </select>
              <div className={`meter${level > 0.95 ? ' loud' : ''}`} role="meter" aria-label="Уровень звука" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(level * 100)}>
                <div style={{ width: `${Math.min(100, level * 140)}%` }} />
              </div>
              <span className="hint">{level < 0.02 && phase === 'ready' ? 'Скажите что-нибудь — полоска должна двигаться.' : 'Говорите в обычном голосе: полоска должна доходить примерно до середины.'}</span>
            </div>
            <p className="hint">Смотрите в объектив, а не на экран. Встаньте или сядьте так, чтобы в кадре были плечи и руки.</p>
          </div>
        </aside>
      </div>
    </div>
  )
}
