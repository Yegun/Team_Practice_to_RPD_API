import { useEffect, useState } from 'react'
import './App.css'
import { listCards } from './api'
import { CardEditForm } from './components/CardEditForm'
import { CardList, type ListState } from './components/CardList'
import { DraftReview } from './components/DraftReview'
import { UploadForm } from './components/UploadForm'
import { strings } from './strings'
import type { Card, Draft } from './types'

type View = 'list' | 'upload' | 'review' | 'edit'

export default function App() {
  const [view, setView] = useState<View>('list')
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [editing, setEditing] = useState<Card | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [list, setList] = useState<ListState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    listCards()
      .then(({ items }) => {
        if (!cancelled) setList({ kind: 'ready', items })
      })
      .catch(() => {
        if (!cancelled) setList({ kind: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  const reload = () => {
    setList({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  // 저장이나 수정이 끝나면 목록으로 돌아가 새로 읽는다 (기한이 바뀌면 순서도 바뀐다).
  const backToList = (message?: string) => {
    setNotice(message ?? null)
    setView('list')
    reload()
  }

  return (
    <main className="app">
      <h1>{strings.appTitle}</h1>
      {view === 'upload' ? (
        <UploadForm
          onDone={(items) => {
            setDrafts(items)
            setView('review')
          }}
          onCancel={() => setView('list')}
        />
      ) : view === 'review' ? (
        <DraftReview drafts={drafts} onBack={() => setView('list')} onSaved={() => backToList()} />
      ) : view === 'edit' && editing ? (
        <CardEditForm
          card={editing}
          onCancel={() => setView('list')}
          onDone={(message) => backToList(message)}
        />
      ) : (
        <>
          <div className="actions">
            <button
              type="button"
              className="primary"
              onClick={() => {
                setNotice(null)
                setView('upload')
              }}
            >
              {strings.addPhoto}
            </button>
          </div>
          {notice && (
            <p role="status" className="notice">
              {notice}
            </p>
          )}
          <CardList
            state={list}
            onRetry={reload}
            onEdit={(card) => {
              setNotice(null)
              setEditing(card)
              setView('edit')
            }}
          />
        </>
      )}
    </main>
  )
}
