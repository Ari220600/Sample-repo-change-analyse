import { useState, useEffect } from 'react'

const API = '/api/v1'
const token = () => localStorage.getItem('token')
const headers = () => ({ 'Content-Type': 'application/json', ...(token() ? { Authorization: `Bearer ${token()}` } : {}) })

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, { ...opts, headers: { ...headers(), ...opts.headers } })
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
      if (mode === 'register') {
        await api('/auth/register', { method: 'POST', body: JSON.stringify(form) })
      }
      const { access_token } = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) })
      localStorage.setItem('token', access_token)
      onDone()
    } catch (ex) {
      setErr(ex.message)
    }
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

function TaskRow({ task, onUpdate, onDelete }) {
  return (
    <div className="row" data-testid={`task-${task.id}`}>
      <span>{task.title} <small>({task.status})</small></span>
      <span>
        <select value={task.status} onChange={(e) => onUpdate(task.id, { status: e.target.value })} aria-label="status">
          <option value="pending">pending</option>
          <option value="in_progress">in_progress</option>
          <option value="completed">completed</option>
        </select>
        <button onClick={() => onDelete(task.id)}>Delete</button>
      </span>
    </div>
  )
}

function Dashboard() {
  const [user, setUser] = useState(null)
  const [tasks, setTasks] = useState([])
  const [stats, setStats] = useState(null)
  const [title, setTitle] = useState('')

  const load = async () => {
    setUser(await api('/users/me'))
    setTasks(await api('/tasks'))
    setStats(await api('/tasks/stats'))
  }

  useEffect(() => { load().catch(() => { localStorage.removeItem('token'); window.location.reload() }) }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!title.trim()) return
    await api('/tasks', { method: 'POST', body: JSON.stringify({ title }) })
    setTitle('')
    load()
  }

  return (
    <div className="wrap">
      <header>
        <h1>TaskFlow</h1>
        <span>{user?.username}</span>
        <button onClick={() => { localStorage.removeItem('token'); window.location.reload() }}>Logout</button>
      </header>
      {stats && <p className="stats">Total: {stats.total} | Pending: {stats.pending} | Done: {stats.completed}</p>}
      <form className="card" onSubmit={create}>
        <input placeholder="New task" value={title} onChange={(e) => setTitle(e.target.value)} />
        <button type="submit">Add</button>
      </form>
      <div className="card">
        {tasks.map((t) => (
          <TaskRow key={t.id} task={t} onUpdate={(id, d) => api(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(d) }).then(load)} onDelete={(id) => api(`/tasks/${id}`, { method: 'DELETE' }).then(load)} />
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!token())
  return <div className="wrap">{loggedIn ? <Dashboard /> : <AuthForm onDone={() => setLoggedIn(true)} />}</div>
}
