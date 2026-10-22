import { useEffect, useState } from 'react'
import './App.css'
import {
  ApiRequestError,
  archiveCard,
  listCards,
  logout,
  me,
  setUnauthenticatedHandler,
} from './api'
import { AuthForm } from './components/AuthForm'
import { CardEditForm } from './components/CardEditForm'
import { CardList, type ListState } from './components/CardList'
import { DraftReview } from './components/DraftReview'
import { UploadForm } from './components/UploadForm'
import { strings } from './strings'
import type { Card, Draft, User } from './types'

type View = 'list' | 'upload' | 'review' | 'edit'

// 처음 열 때 /api/auth/me 로 로그인 여부를 확인한다 (S-01).
type Auth =
  | { kind: 'checking' }
  | { kind: 'anon'; notice: string | null }
  | { kind: 'user'; user: User }

export default function App() {
  const [auth, setAuth] = useState<Auth>({ kind: 'checking' })
  const [view, setView] = useState<View>('list')
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [editing, setEditing] = useState<Card | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [list, setList] = useState<ListState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [archiving, setArchiving] = useState(false)

  // 로그인 화면으로 돌아갈 때 화면이 들고 있던 값은 버린다.
  const resetToAnon = (notice: string | null) => {
    setView('list')
    setDrafts([])
    setEditing(null)
    setNotice(null)
    setList({ kind: 'loading' })
    setAuth({ kind: 'anon', notice })
  }

  useEffect(() => {
    let cancelled = false
    me()
      .then(({ user }) => {
        if (!cancelled) setAuth({ kind: 'user', user })
      })
      .catch(() => {
        if (!cancelled) setAuth({ kind: 'anon', notice: null })
      })
    // 어느 API 든 401 이면 로그인 화면으로 보낸다.
    setUnauthenticatedHandler(() => resetToAnon(strings.sessionEnded))
    return () => {
      cancelled = true
      setUnauthenticatedHandler(null)
    }
  }, [])

  const signedIn = auth.kind === 'user'

  useEffect(() => {
    if (!signedIn) return
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
  }, [attempt, signedIn])

  const reload = () => {
    setList({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  // 정리 (R-009). 성공하면 목록을 새로 읽어 카드가 사라진 것을 보여 준다.
  // 찾을 수 없음 · 이미 정리됨(T-11)과 저장 실패(T-10)도 안내한 뒤 목록을 새로 읽어 실제 상태를 확인한다.
  const archive = async (card: Card) => {
    if (archiving) return
    setArchiving(true)
    setNotice(null)
    let message: string | undefined
    try {
      await archiveCard(card.id)
    } catch (err) {
      message =
        err instanceof ApiRequestError &&
        (err.code === 'CARD_NOT_FOUND' || err.code === 'CARD_ARCHIVED')
          ? strings.cardGone
          : strings.saveFailed
    }
    setArchiving(false)
    backToList(message)
  }

  // 저장이나 수정이 끝나면 목록으로 돌아가 새로 읽는다 (기한이 바뀌면 순서도 바뀐다).
  const backToList = (message?: string) => {
    setNotice(message ?? null)
    setView('list')
    reload()
  }

  const signOut = async () => {
    try {
      await logout()
    } catch (err) {
      if (!(err instanceof ApiRequestError && err.status === 401)) {
        setNotice(strings.authErrors.other)
        return
      }
    }
    resetToAnon(null)
  }

  if (auth.kind === 'checking') {
    return (
      <main className="app">
        <h1>{strings.appTitle}</h1>
        <p role="status">{strings.loading}</p>
      </main>
    )
  }

  if (auth.kind === 'anon') {
    return (
      <main className="app">
        <h1>{strings.appTitle}</h1>
        <AuthForm
          notice={auth.notice}
          onDone={(user) => {
            setList({ kind: 'loading' })
            setAuth({ kind: 'user', user })
          }}
        />
      </main>
    )
  }

  return (
    <main className="app">
      <h1>{strings.appTitle}</h1>
      <div className="actions user-bar">
        <span className="user-name">
          {strings.userLabel} {auth.user.login_id}
        </span>
        <button type="button" onClick={signOut}>
          {strings.logoutButton}
        </button>
      </div>
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
            busy={archiving}
            onRetry={reload}
            onArchive={archive}
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
