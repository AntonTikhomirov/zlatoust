export type Skill =
  | 'tempo' | 'pauses' | 'fluency' | 'intonation' | 'loudness'
  | 'diction' | 'eye_contact' | 'gestures' | 'posture' | 'face'

export type Mode = 'free' | 'topic' | 'reading' | 'tongue_twister'

export interface Exercise {
  id: string
  kind: 'tongue_twister' | 'topic' | 'reading'
  skill: Skill
  title: string
  text: string
  how: string
}

export interface Observation { skill: Skill; level: 'good' | 'warn' | 'bad'; text: string; t: number | null }
export interface Improvement { skill: Skill; problem: string; how_to_fix: string; t: number | null }
export interface Word { w: string; s: number; e: number; f: boolean; lc: boolean }

export interface Report {
  overall: number | null
  scores: { skill: Skill; title: string; score: number }[]
  observations: Observation[]
  weakest: Skill[]
  feedback: {
    summary: string
    strengths: string[]
    improvements: Improvement[]
    next_exercise_id: string
    next_exercise_why: string
  }
  provider: 'rules' | 'ollama' | 'anthropic'
  llm_error: string | null
  transcript: string
  words: Word[]
  asr: { device: string; model: string }
}

export interface DictionOp { op: 'ok' | 'sub' | 'del' | 'ins'; ref: string | null; hyp: string | null }

export interface Metrics {
  speech: Record<string, any>
  prosody: Record<string, any>
  video: Record<string, any>
  diction: { wer: number; cer: number; accuracy: number; ops: DictionOp[]; problem_words: string[] } | null
}

export type Status = 'queued' | 'processing' | 'done' | 'error'

export interface SessionSummary {
  id: string
  created_at: string
  mode: Mode
  exercise_id: string | null
  title: string | null
  duration: number | null
  status: Status
  stage: string | null
  progress: number
  error: string | null
  overall?: number | null
}

export interface Session extends SessionSummary {
  reference_text: string | null
  metrics: Metrics | null
  report: Report | null
}

export interface Settings {
  llm_provider: 'none' | 'ollama' | 'anthropic'
  anthropic_model: string
  anthropic_key_set: boolean
  anthropic_key_hint: string
  ollama_url: string
  ollama_model: string
  whisper_model: string
  record_seconds: number
}

export interface Health { ok: boolean; gpu: boolean; video_models: boolean; llm: string; data_dir: string }

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  let r: Response
  try {
    r = await fetch(url, init)
  } catch {
    throw new Error('Нет связи с ядром приложения. Перезапустите Златоуст.')
  }
  if (!r.ok) {
    let msg = `Ошибка ${r.status}`
    try {
      const j = await r.json()
      if (typeof j.detail === 'string') msg = j.detail
    } catch { /* тело не JSON */ }
    throw new Error(msg)
  }
  return r.json()
}

const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => req<Health>('/api/health'),
  exercises: () => req<{ exercises: Exercise[]; skills: Record<Skill, string> }>('/api/exercises'),
  sessions: () => req<{ sessions: SessionSummary[] }>('/api/sessions'),
  session: (id: string) => req<Session>(`/api/sessions/${id}`),
  retry: (id: string) => req<{ ok: boolean }>(`/api/sessions/${id}/retry`, { method: 'POST' }),
  remove: (id: string) => req<{ ok: boolean }>(`/api/sessions/${id}`, { method: 'DELETE' }),
  videoUrl: (id: string) => `/api/sessions/${id}/video`,
  upload: (blob: Blob, mode: Mode, exercise?: Exercise | null, referenceText?: string) => {
    const fd = new FormData()
    fd.append('file', blob, blob.type.includes('mp4') ? 'rec.mp4' : 'rec.webm')
    fd.append('mode', mode)
    if (exercise) {
      fd.append('exercise_id', exercise.id)
      fd.append('title', exercise.title)
    }
    if (referenceText) fd.append('reference_text', referenceText)
    return req<{ id: string }>('/api/sessions', { method: 'POST', body: fd })
  },
  settings: () => req<Settings>('/api/settings'),
  saveSettings: (s: Partial<Settings> & { anthropic_api_key?: string }) =>
    req<Settings>('/api/settings', { method: 'PUT', ...json(s) }),
  testLlm: () => req<{ ok: boolean; message: string }>('/api/settings/test-llm', { method: 'POST' }),
}

export function fmtTime(t: number): string {
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function fmtDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
}

export const MODE_TITLES: Record<Mode, string> = {
  free: 'Свободная речь',
  topic: 'Речь на тему',
  reading: 'Чтение с суфлёра',
  tongue_twister: 'Скороговорка',
}

export function modeForExercise(e: Exercise): Mode {
  return e.kind === 'tongue_twister' ? 'tongue_twister' : e.kind === 'reading' ? 'reading' : 'topic'
}
