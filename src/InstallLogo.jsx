import { useEffect, useRef, useState } from 'react'
import logo from './assets/logo.webp'

export default function InstallLogo() {
  const promptRef = useRef(null)
  const dialogRef = useRef(null)
  const busyRef = useRef(false)
  const [installed, setInstalled] = useState(() =>
    window.matchMedia('(display-mode: standalone)').matches || Boolean(navigator.standalone))
  const [canInstall, setCanInstall] = useState(false)
  const [copyStatus, setCopyStatus] = useState('')
  const pageUrl = window.location.href
  const isApple = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)

  useEffect(() => {
    const capturePrompt = (event) => {
      event.preventDefault()
      promptRef.current = event
      setCanInstall(true)
    }
    const handleInstalled = () => {
      promptRef.current = null
      setInstalled(true)
      setCanInstall(false)
    }
    window.addEventListener('beforeinstallprompt', capturePrompt)
    window.addEventListener('appinstalled', handleInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', capturePrompt)
      window.removeEventListener('appinstalled', handleInstalled)
    }
  }, [])

  const openDialog = () => {
    setCopyStatus('')
    if (window.matchMedia('(display-mode: standalone)').matches || navigator.standalone) {
      setInstalled(true)
    }
    dialogRef.current.showModal()
  }

  const handleInstall = async () => {
    if (busyRef.current) return
    const installPrompt = promptRef.current
    if (installPrompt && !installed) {
      promptRef.current = null
      setCanInstall(false)
      busyRef.current = true
      try {
        await installPrompt.prompt()
        const { outcome } = await installPrompt.userChoice
        if (outcome === 'accepted') setInstalled(true)
        return
      } catch {
        // A consumed or unavailable prompt falls back to browser instructions.
      } finally {
        busyRef.current = false
      }
    }
  }

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(pageUrl)
      setCopyStatus('Link kopiert!')
    } catch {
      setCopyStatus('Bitte den Link gedrückt halten und «Link kopieren» wählen.')
    }
  }

  return (
    <>
      <button type="button" className="brand-logo-link brand-logo-button" onClick={openDialog}
        aria-label="Latin Events Switzerland – Installieren und Teilen" aria-haspopup="dialog">
        <img src={logo} alt="Latin Events Switzerland" className="brand-logo" />
      </button>
      <dialog ref={dialogRef} className="install-dialog" aria-labelledby="install-title" aria-describedby="install-description">
        <form method="dialog" className="install-close-form">
          <button type="submit" className="install-close-button" aria-label="Schliessen">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </form>
        <h2 id="install-title">{installed ? 'App hinzugefügt' : 'Zum Home-Bildschirm hinzufügen'}</h2>
        <p id="install-description">
          {installed ? 'Du kannst Latin Events Switzerland jetzt über das App-Symbol auf deinem Home-Bildschirm öffnen.' :
            'Öffne Latin Events Switzerland direkt über ein App-Symbol auf deinem Home-Bildschirm.'}
        </p>
        {!installed && (isApple ? (
          <ol>
            <li>Öffne diese Webseite in Safari.</li>
            <li>Tippe auf «Teilen» und dann auf «Zum Home-Bildschirm».</li>
            <li>Aktiviere «Als Web-App öffnen», falls angezeigt, und tippe auf «Hinzufügen».</li>
          </ol>
        ) : (
          <>
            <ol>
              <li>Öffne das Menü deines Browsers (⋮).</li>
              <li>Wähle «App installieren» oder «Zum Startbildschirm hinzufügen» und bestätige.</li>
            </ol>
            <p>Falls diese Option fehlt, öffne diese Webseite in Chrome oder einem anderen Browser mit Installationsfunktion.</p>
          </>
        ))}
        {canInstall && !installed && (
          <p><button type="button" onClick={handleInstall}>App installieren</button></p>
        )}
        <section className="install-sharing" aria-labelledby="sharing-title">
        <h2 id="sharing-title">Sharing is caring</h2>
        <div className="install-page-link">
          <a href={pageUrl}>{pageUrl}</a>
          <button type="button" className="install-copy-button" onClick={handleCopyLink}
            aria-label="Link kopieren" title="Link kopieren">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="8" y="8" width="12" height="13" rx="2" />
              <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
            </svg>
          </button>
          <span className="install-copy-status" role="status">{copyStatus}</span>
        </div>
        </section>
        <p className="install-credit">
          made with <span className="install-credit-love" role="img" aria-label="love">❤️</span> by{' '}
          <a href="https://www.instagram.com/kramerkuenstler/" target="_blank" rel="noopener noreferrer">Ändu</a>
        </p>
      </dialog>
    </>
  )
}
