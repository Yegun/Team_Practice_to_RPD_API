import { useEffect, useState } from 'react'
import './App.css'
import { listCards } from './api'
import { CardList, type ListState } from './components/CardList'
import { UploadForm } from './components/UploadForm'
import { strings } from './strings'

type View = 'list' | 'upload'

export default function App() {
  const [view, setView] = useState<View>('list')
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

  return (
    <main className="app">
      <h1>{strings.appTitle}</h1>
      {view === 'upload' ? (
        <UploadForm
          onDone={() => {
            // 정리 결과 확인 화면은 US-03 에서 붙인다.
            setView('list')
          }}
          onCancel={() => setView('list')}
        />
      ) : (
        <>
          <div className="actions">
            <button type="button" className="primary" onClick={() => setView('upload')}>
              {strings.addPhoto}
            </button>
          </div>
          <CardList state={list} onRetry={reload} />
        </>
      )}
    </main>
  )
}
