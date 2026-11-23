import type { ReactNode } from 'react'

export function scoreColor(s: number | null | undefined): string {
  if (s == null) return 'var(--text-3)'
  if (s >= 80) return 'var(--good)'
  if (s >= 60) return 'var(--warn)'
  return 'var(--bad)'
}

export function scoreWord(s: number): string {
  if (s >= 85) return 'отлично'
  if (s >= 70) return 'хорошо'
  if (s >= 55) return 'неплохо'
  return 'есть над чем работать'
}

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  return (
    <span className="score-badge" style={{ color: scoreColor(score) }} aria-label={score == null ? 'Нет оценки' : `Оценка ${score} из 100`}>
      {score ?? '—'}
    </span>
  )
}

export function Ring({ score }: { score: number | null }) {
  const r = 50
  const c = 2 * Math.PI * r
  const v = score ?? 0
  return (
    <div className="ring" role="img" aria-label={score == null ? 'Нет общей оценки' : `Общая оценка ${score} из 100`}>
      <svg width="112" height="112" viewBox="0 0 112 112" aria-hidden>
        <circle cx="56" cy="56" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="10" />
        <circle cx="56" cy="56" r={r} fill="none" stroke={scoreColor(score)} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${(c * v) / 100} ${c}`} />
      </svg>
      <div className="ring-label" aria-hidden><div><b>{score ?? '—'}</b><div className="small muted">из 100</div></div></div>
    </div>
  )
}

const paths: Record<string, ReactNode> = {
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>,
  text: <><path d="M4 6h16M4 12h16M4 18h10" /></>,
  bolt: <><path d="M13 3 5 14h6l-1 7 8-11h-6l1-7z" /></>,
  play: <><path d="M8 5v14l11-7z" /></>,
  check: <><path d="m5 12 5 5 9-10" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  retry: <><path d="M4 12a8 8 0 1 0 3-6.2M4 4v4h4" /></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></>,
}

export function Icon({ name, size = 20 }: { name: keyof typeof paths | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {paths[name]}
    </svg>
  )
}

export function plural(n: number, one: string, few: string, many: string): string {
  const n10 = n % 10, n100 = n % 100
  if (n10 === 1 && n100 !== 11) return one
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return few
  return many
}
