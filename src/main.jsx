import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import faviconPng from './assets/favicon.png'
import faviconWebp from './assets/favicon.webp'

const ensureLink = ({ rel, type, sizes, href }) => {
  const selector = [
    `link[rel="${rel}"]`,
    type ? `[type="${type}"]` : '',
    sizes ? `[sizes="${sizes}"]` : '',
  ].join('')
  let link = document.head.querySelector(selector)
  if (!link) {
    link = document.createElement('link')
    link.rel = rel
    if (type) link.type = type
    if (sizes) link.sizes = sizes
    document.head.appendChild(link)
  }
  link.href = href
}

ensureLink({
  rel: 'icon',
  type: 'image/png',
  sizes: '192x192',
  href: faviconPng,
})
ensureLink({ rel: 'icon', type: 'image/webp', href: faviconWebp })
ensureLink({ rel: 'apple-touch-icon', type: 'image/png', href: faviconPng })

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
