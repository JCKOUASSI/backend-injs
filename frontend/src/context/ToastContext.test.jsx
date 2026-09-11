import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ToastProvider, useToast } from '@/context/ToastContext'

function Harness() {
  const toast = useToast()
  return (
    <div>
      <button onClick={() => toast.showToast('Opération réussie', 'success')}>succès</button>
      <button onClick={() => toast.showToast('Erreur métier', 'error')}>erreur</button>
      <button onClick={() => toast.showToast('Info')}>défaut</button>
    </div>
  )
}

describe('context/ToastContext', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('affiche un toast de succès puis le retire après 6 s', () => {
    render(<ToastProvider><Harness /></ToastProvider>)

    fireEvent.click(screen.getByText('succès'))
    expect(screen.getByText('Opération réussie')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(5999))
    expect(screen.getByText('Opération réussie')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(2))
    expect(screen.queryByText('Opération réussie')).not.toBeInTheDocument()
  })

  it('utilise le type success par défaut', () => {
    render(<ToastProvider><Harness /></ToastProvider>)
    fireEvent.click(screen.getByText('défaut'))
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('peut empiler plusieurs toasts', () => {
    render(<ToastProvider><Harness /></ToastProvider>)
    fireEvent.click(screen.getByText('succès'))
    fireEvent.click(screen.getByText('défaut'))
    expect(screen.getByText('Opération réussie')).toBeInTheDocument()
    expect(screen.getByText('Info')).toBeInTheDocument()
  })
})
