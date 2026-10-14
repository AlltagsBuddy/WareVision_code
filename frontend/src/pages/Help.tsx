import { useEffect, useMemo, useRef, useState } from 'react'
import { helpApi, type HelpAnswer } from '../api/client'

interface Section { id: string; heading: string; text: string }
interface Article { id: string; title: string; sections: Section[] }
interface ChatMessage { role: 'user' | 'assistant'; content: string; meta?: Omit<HelpAnswer, 'answer'> }

const EXAMPLE_QUESTIONS = [
  'Wie storniere ich eine Rechnung?',
  'Wie wandle ich ein Angebot in einen Werkstattauftrag um?',
  'Wie mache ich eine Inventur?',
  'Wie importiere ich eine E-Rechnung von einem Lieferanten?',
]

// Feste Textgröße: .card p ist im Dashboard als große Kennzahl gestylt
const TEXT_STYLE: React.CSSProperties = { margin: '0 0 0.6rem', fontSize: '0.92rem', fontWeight: 400, lineHeight: 1.5, color: 'var(--color-text)' }
const LIST_STYLE: React.CSSProperties = { margin: '0 0 0.6rem', paddingLeft: '1.3rem', fontSize: '0.92rem', lineHeight: 1.5 }

/** Fett-Markierung (**text**) als React-Elemente – ohne HTML, daher sicher. */
function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <strong key={`${keyPrefix}-${i}`}>{p.slice(2, -2)}</strong> : <span key={`${keyPrefix}-${i}`}>{p}</span>
  )
}

/** Einfaches Markdown (Absätze, Aufzählungen, nummerierte Listen, Fett) sicher darstellen. */
export function SimpleMarkdown({ text }: { text: string }) {
  const blocks: JSX.Element[] = []
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  let list: { ordered: boolean; items: string[] } | null = null
  let para: string[] = []
  const flushPara = () => {
    if (para.length) {
      blocks.push(<p key={`p${blocks.length}`} style={TEXT_STYLE}>{renderInline(para.join(' '), `p${blocks.length}`)}</p>)
      para = []
    }
  }
  const flushList = () => {
    if (list) {
      const items = list.items.map((it, i) => <li key={i}>{renderInline(it, `li${blocks.length}-${i}`)}</li>)
      blocks.push(list.ordered
        ? <ol key={`l${blocks.length}`} style={LIST_STYLE}>{items}</ol>
        : <ul key={`l${blocks.length}`} style={LIST_STYLE}>{items}</ul>)
      list = null
    }
  }
  for (const raw of lines) {
    const line = raw.trim()
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    const numbered = line.match(/^\d+[.)]\s+(.*)$/)
    if (bullet || numbered) {
      flushPara()
      const ordered = !!numbered
      if (!list || list.ordered !== ordered) {
        flushList()
        list = { ordered, items: [] }
      }
      list.items.push((bullet || numbered)![1])
    } else if (!line) {
      flushPara()
      flushList()
    } else {
      flushList()
      para.push(line.replace(/^#+\s*/, ''))
    }
  }
  flushPara()
  flushList()
  return <>{blocks}</>
}

export default function Help() {
  const [articles, setArticles] = useState<Article[]>([])
  const [activeId, setActiveId] = useState<string>('')
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<{ id: string; article_id: string; article_title: string; heading: string; text: string }[] | null>(null)
  const [aiEnabled, setAiEnabled] = useState(false)
  const [question, setQuestion] = useState('')
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    helpApi.articles().then((a) => { setArticles(a); setActiveId(a[0]?.id || '') }).catch(() => setError('Hilfe konnte nicht geladen werden.'))
    helpApi.status().then((s) => setAiEnabled(s.ai_enabled)).catch(() => {})
  }, [])

  useEffect(() => {
    const q = search.trim()
    if (q.length < 2) { setResults(null); return }
    const t = setTimeout(() => { helpApi.search(q).then(setResults).catch(() => setResults([])) }, 250)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [chat, asking])

  const active = useMemo(() => articles.find((a) => a.id === activeId), [articles, activeId])

  const openSection = (articleId: string, sectionId?: string) => {
    setActiveId(articleId)
    setSearch('')
    if (sectionId) setTimeout(() => document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' }), 50)
  }

  const send = async (text?: string) => {
    const q = (text ?? question).trim()
    if (q.length < 2 || asking) return
    setError('')
    const history = chat.map(({ role, content }) => ({ role, content }))
    setChat((c) => [...c, { role: 'user', content: q }])
    setQuestion('')
    setAsking(true)
    try {
      const res = await helpApi.ask(q, history)
      setChat((c) => [...c, { role: 'assistant', content: res.answer, meta: { mode: res.mode, sources: res.sources, notice: res.notice } }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Die Frage konnte nicht beantwortet werden.')
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="page">
      <h1>Hilfe</h1>
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        {/* ---------- Anleitung ---------- */}
        <div style={{ flex: '2 1 520px', minWidth: 0 }}>
          <div className="toolbar">
            <input type="search" placeholder="In der Anleitung suchen…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Hilfe durchsuchen" />
          </div>
          {results ? (
            <div className="card" style={{ padding: '1rem' }}>
              <h3 style={{ marginTop: 0 }}>Suchergebnisse</h3>
              {results.length === 0 && <p className="muted">Keine Treffer. Versuche andere Begriffe oder frag den Assistenten.</p>}
              {results.map((r) => (
                <div key={r.id} style={{ marginBottom: '1rem' }}>
                  <a href={`#${r.id}`} onClick={(e) => { e.preventDefault(); openSection(r.article_id, r.id) }}>
                    <strong>{r.article_title} – {r.heading}</strong>
                  </a>
                  <div className="muted" style={{ fontSize: '0.9rem' }}>{r.text.slice(0, 220)}{r.text.length > 220 ? '…' : ''}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <nav aria-label="Inhaltsverzeichnis" style={{ flex: '0 0 200px' }}>
                {articles.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => openSection(a.id)}
                    className={a.id === activeId ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                    style={{ display: 'block', width: '100%', textAlign: 'left', marginBottom: '0.3rem' }}
                  >
                    {a.title}
                  </button>
                ))}
              </nav>
              {active && (
                <article className="card" style={{ flex: '1 1 300px', padding: '1rem 1.25rem', minWidth: 0 }}>
                  <h2 style={{ marginTop: 0 }}>{active.title}</h2>
                  {active.sections.map((s) => (
                    <section key={s.id} id={s.id} style={{ marginBottom: '1rem' }}>
                      <h3 style={{ fontSize: '1rem', marginBottom: '0.4rem', color: 'var(--color-text)', textTransform: 'none' }}>{s.heading}</h3>
                      <SimpleMarkdown text={s.text} />
                    </section>
                  ))}
                </article>
              )}
            </div>
          )}
        </div>

        {/* ---------- Assistent ---------- */}
        <aside className="card" style={{ flex: '1 1 340px', padding: '1rem', position: 'sticky', top: '1rem' }} aria-label="Hilfe-Assistent">
          <h3 style={{ marginTop: 0 }}>
            {aiEnabled ? '🤖 KI-Assistent' : '🔎 Hilfe-Assistent'}
          </h3>
          <p className="muted" style={{ fontSize: '0.82rem', marginTop: 0 }}>
            {aiEnabled
              ? 'Stell eine Frage zur Bedienung. Bitte keine Kunden- oder personenbezogenen Daten eingeben.'
              : 'Stell eine Frage – passende Abschnitte der Anleitung werden angezeigt. (KI kann ein Admin unter Einstellungen → KI-Hilfe aktivieren.)'}
          </p>
          <div style={{ maxHeight: 460, overflowY: 'auto', marginBottom: '0.75rem' }}>
            {chat.length === 0 && (
              <div>
                <p style={{ fontSize: '0.88rem' }}>Beispiele:</p>
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button key={q} type="button" className="btn-secondary btn-sm" style={{ display: 'block', marginBottom: '0.3rem', textAlign: 'left' }} onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {chat.map((m, i) => (
              <div
                key={i}
                style={{
                  margin: '0 0 0.6rem',
                  padding: '0.6rem 0.75rem',
                  borderRadius: 8,
                  background: m.role === 'user' ? 'rgba(34,211,238,0.12)' : 'rgba(255,255,255,0.05)',
                  marginLeft: m.role === 'user' ? '2rem' : 0,
                  fontSize: '0.9rem',
                }}
              >
                {m.role === 'user' ? m.content : <SimpleMarkdown text={m.content} />}
                {m.meta?.notice && <p className="muted" style={{ fontSize: '0.78rem', margin: '0.3rem 0 0' }}>{m.meta.notice}</p>}
                {m.meta && m.meta.sources.length > 0 && (
                  <div style={{ fontSize: '0.78rem', marginTop: '0.4rem' }}>
                    Siehe:{' '}
                    {m.meta.sources.map((s, j) => (
                      <a key={s.id} href={`#${s.id}`} onClick={(e) => { e.preventDefault(); openSection(s.article_id, s.id) }}>
                        {j > 0 ? ' · ' : ''}{s.title}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {asking && <p className="muted" style={{ fontSize: '0.88rem' }}>Antwort wird erstellt…</p>}
            <div ref={chatEndRef} />
          </div>
          {error && <p className="error">{error}</p>}
          <form onSubmit={(e) => { e.preventDefault(); send() }} style={{ display: 'flex', gap: '0.4rem' }}>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Deine Frage…"
              maxLength={1000}
              style={{ flex: 1 }}
              aria-label="Frage an den Assistenten"
            />
            <button type="submit" className="btn-primary" disabled={asking || question.trim().length < 2}>Fragen</button>
          </form>
          {chat.length > 0 && (
            <button type="button" className="btn-secondary btn-sm" style={{ marginTop: '0.5rem' }} onClick={() => setChat([])}>
              Neues Gespräch
            </button>
          )}
        </aside>
      </div>
    </div>
  )
}
