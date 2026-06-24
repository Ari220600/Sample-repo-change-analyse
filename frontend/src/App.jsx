import { useState, useEffect } from 'react'

const API = '/api/v2'  // CHANGE 1: v1 → v2 prefix

async function api(path, opts = {}) {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
  return res.status === 204 ? null : res.json()
}

function AuthForm({ onDone }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    try {
      if (mode === 'register') await api('/auth/register', { method: 'POST', body: JSON.stringify(form) })
      const { access_token } = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) })
      localStorage.setItem('token', access_token)
      onDone()
    } catch (ex) { setErr(ex.message) }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{mode === 'login' ? 'Login' : 'Register'}</h2>
      {err && <p className="err">{err}</p>}
      <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      {mode === 'register' && <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />}
      <input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
      <button type="submit">{mode === 'login' ? 'Login' : 'Register'}</button>
      <button type="button" className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
        {mode === 'login' ? 'Need an account?' : 'Have an account?'}
      </button>
    </form>
  )
}

function ItemRow({ item, onUpdate, onArchive }) {
  return (
    <div className="row" data-testid={`item-${item.id}`}>
      <span>{item.title} <small>({item.status})</small></span>
      <span>
        <select value={item.status} onChange={(e) => onUpdate(item.id, { status: e.target.value })} aria-label="status">
          <option value="open">open</option>
          <option value="done">done</option>
        </select>
        <button onClick={() => onArchive(item.id)}>Archive</button>
      </span>
    </div>
  )
}

function Dashboard() {
  const [user, setUser] = useState(null)
  const [items, setItems] = useState([])
  const [stats, setStats] = useState(null)
  const [title, setTitle] = useState('')

  const load = async () => {
    setUser(await api('/auth/me'))       // CHANGE 3
    setItems(await api('/items'))        // CHANGE 2
    setStats(await api('/items/stats'))
  }

  useEffect(() => { load().catch(() => { localStorage.removeItem('token'); window.location.reload() }) }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!title.trim()) return
    await api('/items', { method: 'POST', body: JSON.stringify({ title }) })
    setTitle('')
    load()
  }

  return (
    <div className="wrap">
      <header>
        <h1>TaskFlow v2</h1>
        <span>{user?.username}</span>
        <button onClick={() => { localStorage.removeItem('token'); window.location.reload() }}>Logout</button>
      </header>
      {stats && <p className="stats">Total: {stats.total} | Open: {stats.open} | Done: {stats.done}</p>}
      <form className="card" onSubmit={create}>
        <input placeholder="New item" value={title} onChange={(e) => setTitle(e.target.value)} />
        <button type="submit">Add</button>
      </form>
      <div className="card">
        {items.map((i) => (
          <ItemRow
            key={i.id}
            item={i}
            onUpdate={(id, d) => api(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(d) }).then(load)}
            onArchive={(id) => api(`/items/${id}/archive`, { method: 'POST' }).then(load)}
          />
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem('token'))
  return <div className="wrap">{loggedIn ? <Dashboard /> : <AuthForm onDone={() => setLoggedIn(true)} />}</div>
}
