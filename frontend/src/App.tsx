import { useEffect, useState } from 'react'
import './App.css'

type HealthState = 'loading' | 'ok' | 'error'

function App() {
  const [health, setHealth] = useState<HealthState>('loading')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((body: { status: string }) =>
        setHealth(body.status === 'ok' ? 'ok' : 'error'),
      )
      .catch(() => {
        if (!controller.signal.aborted) setHealth('error')
      })
    return () => controller.abort()
  }, [])

  return (
    <main className="app">
      <h1>Task Flow</h1>
      <p>
        API 연결:{' '}
        {health === 'loading' && '확인 중…'}
        {health === 'ok' && '정상'}
        {health === 'error' && '연결하지 못했습니다'}
      </p>
    </main>
  )
}

export default App
