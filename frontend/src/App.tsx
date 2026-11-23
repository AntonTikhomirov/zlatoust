import { useEffect, useState } from 'react'
import { api, type Exercise, type Skill } from './api'
import { useRoute } from './router'
import Home from './pages/Home'
import Record from './pages/Record'
import SessionPage from './pages/Session'
import History from './pages/History'
import SettingsPage from './pages/Settings'

export interface Catalog { exercises: Exercise[]; byId: Record<string, Exercise>; skills: Record<Skill, string> }

export default function App() {
  const route = useRoute()
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [fatal, setFatal] = useState<string | null>(null)

  useEffect(() => {
    api.exercises()
      .then(r => setCatalog({ exercises: r.exercises, skills: r.skills, byId: Object.fromEntries(r.exercises.map(e => [e.id, e])) }))
      .catch(e => setFatal(e.message))
    // Пинг, чтобы ядро знало, что окно открыто.
    const t = setInterval(() => { api.health().catch(() => undefined) }, 30_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const titles: Record<string, string> = { home: 'Златоуст', record: 'Запись · Златоуст', session: 'Разбор · Златоуст', history: 'История · Златоуст', settings: 'Настройки · Златоуст' }
    document.title = titles[route.name]
  }, [route.name])

  const nav = (name: string, href: string, label: string) => (
    <a href={href} aria-current={route.name === name ? 'page' : undefined}>{label}</a>
  )

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/"><span className="brand-mark" aria-hidden>З</span>Златоуст</a>
        <nav className="nav" aria-label="Разделы">
          {nav('home', '#/', 'Главная')}
          {nav('history', '#/history', 'История')}
          {nav('settings', '#/settings', 'Настройки')}
        </nav>
      </header>
      <main>
        {fatal && <div className="alert alert-bad" role="alert">{fatal}</div>}
        {catalog && route.name === 'home' && <Home catalog={catalog} />}
        {catalog && route.name === 'record' && <Record key={`${route.exerciseId}-${route.mode}`} catalog={catalog} exerciseId={route.exerciseId} mode={route.mode} />}
        {catalog && route.name === 'session' && <SessionPage key={route.id} id={route.id} catalog={catalog} />}
        {route.name === 'history' && <History />}
        {route.name === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
