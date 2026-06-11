import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../src/App'

describe('App', () => {
  beforeEach(() => localStorage.clear())

  it('shows login form when logged out', () => {
    render(<App />)
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('switches to register mode', () => {
    render(<App />)
    fireEvent.click(screen.getByText('Need an account?'))
    expect(screen.getByText('Register')).toBeInTheDocument()
  })

  it('stores token helper works', () => {
    localStorage.setItem('token', 'abc')
    render(<App />)
    expect(localStorage.getItem('token')).toBe('abc')
  })
})
