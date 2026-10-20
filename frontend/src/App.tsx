import { useEffect, useState } from 'react'
import './App.css'
import { listCards } from './api'
import { CardList, type ListState } from './components/CardList'
import { strings } from './strings'

export default function App() {
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

  const retry = () => {
    setList({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  return (
    <main className="app">
      <h1>{strings.appTitle}</h1>
      <CardList state={list} onRetry={retry} />
    </main>
  )
}
