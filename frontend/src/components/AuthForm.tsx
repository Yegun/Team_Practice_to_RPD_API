import { useState, type FormEvent } from 'react'
import { ApiRequestError, NETWORK_ERROR, login, signup } from '../api'
import { strings } from '../strings'
import type { User } from '../types'

type Props = {
  // 세션이 끝나서 돌아온 경우 안내 문구를 보여 준다.
  notice?: string | null
  onDone: (user: User) => void
}

function messageFor(err: unknown): string {
  const e = strings.authErrors
  if (!(err instanceof ApiRequestError)) return e.other
  if (err.code === NETWORK_ERROR) return e.network
  if (err.code === 'INVALID_CREDENTIALS') return e.invalidCredentials
  if (err.code === 'LOGIN_ID_TAKEN') return e.loginIdTaken
  if (err.code === 'VALIDATION_ERROR') return e.invalidInput
  return e.other
}

// 로그인과 가입 화면. 실패해도 입력 칸은 그대로 둔다.
export function AuthForm({ notice, onDone }: Props) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const call = mode === 'login' ? login : signup
      const { user } = await call(loginId, password)
      onDone(user)
    } catch (err) {
      setError(messageFor(err))
      setBusy(false)
    }
  }

  const title = mode === 'login' ? strings.loginTitle : strings.signupTitle

  return (
    <form className="panel" onSubmit={submit}>
      <h2>{title}</h2>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      <label className="field">
        <span>{strings.labelLoginId}</span>
        <input
          type="text"
          autoComplete="username"
          autoCapitalize="none"
          value={loginId}
          onChange={(e) => setLoginId(e.target.value)}
        />
      </label>
      <label className="field">
        <span>{strings.labelPassword}</span>
        <input
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {mode === 'signup' && <p className="file-name">{strings.loginHelp}</p>}
      {error && (
        <p role="alert" className="notice notice-error">
          {error}
        </p>
      )}
      <div className="actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy
            ? strings.submitting
            : mode === 'login'
              ? strings.loginButton
              : strings.signupButton}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login')
            setError(null)
          }}
        >
          {mode === 'login' ? strings.toSignup : strings.toLogin}
        </button>
      </div>
    </form>
  )
}
