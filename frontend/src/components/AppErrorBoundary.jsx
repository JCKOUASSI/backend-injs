import { Component } from 'react'

/**
 * Garde-fou de rendu de l'application (aperçu intégré).
 *
 * Sans lui, une erreur de rendu vide silencieusement la racine React et
 * l'utilisateur voit une page blanche sans information (la console du
 * navigateur n'est pas accessible dans l'iframe d'aperçu). Ce composant
 * affiche l'erreur, et la rapporte automatiquement aux logs du serveur
 * (requête GET journalisée par Django sous /api/__client_error__) afin que
 * le diagnostic ne dépende pas d'une capture d'écran.
 */
function rapporterErreur(message, pile, pileComposants) {
  try {
    const payload = {
      message: String(message || ''),
      stack: String(pile || '').slice(0, 3000),
      componentStack: String(pileComposants || '').slice(0, 1500),
      href: typeof window !== 'undefined' ? window.location.href : '',
      bundle: typeof document !== 'undefined'
        ? Array.from(document.scripts).map((s) => s.src).filter(Boolean).join(' | ').slice(0, 500)
        : '',
    }
    const donnees = btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
    fetch(`/api/__client_error__?d=${encodeURIComponent(donnees)}`, {
      method: 'GET',
      keepalive: true,
    }).catch(() => {})
  } catch {
    // Diagnostic best-effort : ne jamais masquer l'erreur initiale.
  }
}

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { erreur: null, pile: '', pileComposants: '' }
  }

  static getDerivedStateFromError(erreur) {
    return { erreur }
  }

  componentDidCatch(erreur, infos) {
    const pile = erreur?.stack || ''
    const pileComposants = infos?.componentStack || ''
    console.error('Erreur de rendu INJS-LMD :', erreur, infos)
    this.setState({ pile, pileComposants })
    rapporterErreur(erreur?.message || String(erreur), pile, pileComposants)
  }

  render() {
    if (!this.state.erreur) return this.props.children
    const message = this.state.erreur?.message || String(this.state.erreur)
    const { pile, pileComposants } = this.state
    return (
      <div
        role="alert"
        style={{
          margin: '40px auto',
          maxWidth: 560,
          padding: '20px 24px',
          background: '#fdecec',
          border: '1px solid #f3b4b4',
          borderRadius: 10,
          color: '#8a1f1f',
          fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
          fontSize: 14,
          lineHeight: 1.5,
          textAlign: 'left',
        }}
      >
        <strong style={{ fontSize: 15 }}>L&apos;application a rencontré une erreur.</strong>
        <p style={{ margin: '10px 0' }}>
          Rechargez la page (Ctrl+Maj+R / Cmd+Maj+R). Si le problème persiste,
          transmettez le message ci-dessous à l&apos;équipe technique :
        </p>
        <pre
          style={{
            margin: 0,
            padding: 10,
            background: '#fff',
            border: '1px solid #f3b4b4',
            borderRadius: 6,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {message}
        </pre>
        <details open style={{ marginTop: 10 }}>
          <summary style={{ cursor: 'pointer' }}>Détail technique (pile JS)</summary>
          <pre
            style={{
              margin: '8px 0 0',
              padding: 10,
              background: '#fff',
              border: '1px solid #f3b4b4',
              borderRadius: 6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: 220,
              overflow: 'auto',
            }}
          >
            {pile || '(pile JS indisponible)'}
            {pileComposants ? `\n\n--- composants ---\n${pileComposants}` : ''}
          </pre>
        </details>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{
            marginTop: 14,
            padding: '8px 18px',
            border: 'none',
            borderRadius: 6,
            background: '#8a1f1f',
            color: '#fff',
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          Recharger la page
        </button>
      </div>
    )
  }
}
