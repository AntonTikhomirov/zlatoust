import { useEffect, useState } from 'react'

export type Route =
  | { name: 'home' }
  | { name: 'record'; exerciseId?: string; mode?: string }
  | { name: 'session'; id: string }
  | { name: 'history' }
  | { name: 'settings' }

export function parse(hash: string): Route {
  const [path, q = ''] = hash.replace(/^#/, '').split('?')
  const parts = path.split('/').filter(Boolean)
  const params = new URLSearchParams(q)
  if (parts[0] === 'record') return { name: 'record', exerciseId: params.get('ex') ?? undefined, mode: params.get('mode') ?? undefined }
  if (parts[0] === 'session' && parts[1]) return { name: 'session', id: parts[1] }
  if (parts[0] === 'history') return { name: 'history' }
  if (parts[0] === 'settings') return { name: 'settings' }
  return { name: 'home' }
}

export function go(hash: string) {
  window.location.hash = hash
}

export function useRoute(): Route {
  const [r, setR] = useState(() => parse(window.location.hash))
  useEffect(() => {
    const on = () => {
      setR(parse(window.location.hash))
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return r
}
