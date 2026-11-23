import { useEffect, useState } from 'react'
import { api, type Health, type Settings } from '../api'

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [key, setKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    api.settings().then(setS).catch(e => setMsg({ ok: false, text: e.message }))
    api.health().then(setHealth).catch(() => undefined)
  }, [])

  if (!s) return msg ? <div className="alert alert-bad">{msg.text}</div> : <p className="muted">Загружаю…</p>

  const save = async (test: boolean) => {
    setSaving(true)
    setMsg(null)
    try {
      const body: Partial<Settings> & { anthropic_api_key?: string } = {
        llm_provider: s.llm_provider, anthropic_model: s.anthropic_model, ollama_url: s.ollama_url,
        ollama_model: s.ollama_model, whisper_model: s.whisper_model,
      }
      if (key.trim()) body.anthropic_api_key = key.trim()
      const r = await api.saveSettings(body)
      setS(r)
      setKey('')
      if (test) {
        const t = await api.testLlm()
        setMsg({ ok: t.ok, text: t.message })
      } else setMsg({ ok: true, text: 'Сохранено.' })
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message })
    } finally {
      setSaving(false)
    }
  }

  const removeKey = async () => {
    const r = await api.saveSettings({ anthropic_api_key: '' })
    setS(r)
    setMsg({ ok: true, text: 'Ключ удалён.' })
  }

  const set = <K extends keyof Settings>(k: K, v: Settings[K]) => setS({ ...s, [k]: v })

  return (
    <div className="stack" style={{ gap: 24, maxWidth: 720 }}>
      <h1>Настройки</h1>

      <section className="card stack">
        <h2>Кто пишет разбор</h2>
        <p className="muted small">Метрики и оценки всегда считает программа. Здесь вы выбираете, кто превращает их в советы.</p>
        <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0, gap: 10 }}>
          <legend className="sr-only">Способ разбора</legend>
          {([
            ['none', 'По правилам', 'Бесплатно и без интернета. Советы из готового набора.'],
            ['ollama', 'Локальная модель (Ollama)', 'Бесплатно, работает на вашей видеокарте. Нужна установленная Ollama.'],
            ['anthropic', 'Claude API', 'Самые точные советы. Нужен ключ API, оплата по факту — около 5 центов за разбор на Opus.'],
          ] as const).map(([v, t, d]) => (
            <label key={v} className="radio-row">
              <input type="radio" name="llm" checked={s.llm_provider === v} onChange={() => set('llm_provider', v)} style={{ marginTop: 4, width: 18, height: 18, flex: 'none' }} />
              <span><b>{t}</b><br /><span className="small muted">{d}</span></span>
            </label>
          ))}
        </fieldset>

        {s.llm_provider === 'anthropic' && (
          <div className="stack" style={{ gap: 14 }}>
            <div className="field">
              <label htmlFor="key">Ключ API</label>
              <input id="key" className="input" type="password" autoComplete="off" placeholder={s.anthropic_key_set ? `Сохранён ключ ${s.anthropic_key_hint}` : 'sk-ant-…'} value={key} onChange={e => setKey(e.target.value)} />
              <span className="hint">Подписка Claude Pro ключа не даёт. Ключ создаётся на console.anthropic.com → API Keys. Он хранится только на этом компьютере.</span>
              {s.anthropic_key_set && <div><button className="btn btn-sm btn-ghost" onClick={removeKey}>Удалить сохранённый ключ</button></div>}
            </div>
            <div className="field">
              <label htmlFor="am">Модель</label>
              <select id="am" value={s.anthropic_model} onChange={e => set('anthropic_model', e.target.value)}>
                <option value="claude-opus-5-5">Claude Opus 5.5 — лучшее качество (~$0,05 за разбор)</option>
                <option value="claude-sonnet-5-5">Claude Sonnet 5.5 — баланс (~$0,03)</option>
                <option value="claude-haiku-5-5">Claude Haiku 5.5 — самый дешёвый (~$0,002)</option>
              </select>
            </div>
          </div>
        )}

        {s.llm_provider === 'ollama' && (
          <div className="grid-2">
            <div className="field">
              <label htmlFor="ou">Адрес Ollama</label>
              <input id="ou" className="input" value={s.ollama_url} onChange={e => set('ollama_url', e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="om">Модель</label>
              <input id="om" className="input" value={s.ollama_model} onChange={e => set('ollama_model', e.target.value)} />
              <span className="hint">Установка: <code>ollama pull {s.ollama_model}</code></span>
            </div>
          </div>
        )}

        <div className="row">
          <button className="btn btn-primary" disabled={saving} onClick={() => save(s.llm_provider !== 'none')}>
            {s.llm_provider === 'none' ? 'Сохранить' : 'Сохранить и проверить'}
          </button>
          {msg && <span role="status" className={msg.ok ? '' : 'chip chip-bad'} style={{ color: msg.ok ? 'var(--good)' : undefined }}>{msg.text}</span>}
        </div>
      </section>

      <section className="card stack">
        <h2>Распознавание речи</h2>
        <div className="field">
          <label htmlFor="wm">Модель Whisper</label>
          <select id="wm" value={s.whisper_model} onChange={e => set('whisper_model', e.target.value)}>
            <option value="auto">Автоматически (рекомендуется)</option>
            <option value="large-v3">large-v3 — точнее всего, нужна видеокарта</option>
            <option value="medium">medium — быстрее, чуть менее точно</option>
            <option value="small">small — для работы без видеокарты</option>
          </select>
          <span className="hint">Сейчас: {health ? (health.gpu ? 'видеокарта найдена, будет large-v3' : 'видеокарта не найдена, будет small на процессоре') : '…'}.</span>
        </div>
        <div><button className="btn" disabled={saving} onClick={() => save(false)}>Сохранить</button></div>
      </section>

      {health && (
        <section className="card stack">
          <h2>Данные</h2>
          <p className="small muted">Записи, база и модели хранятся здесь:</p>
          <code style={{ wordBreak: 'break-all' }}>{health.data_dir}</code>
        </section>
      )}
    </div>
  )
}
