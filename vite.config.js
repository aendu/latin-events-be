import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function crawlApiPlugin() {
  return {
    name: 'crawl-events-api',
    configureServer(server) {
      server.middlewares.use('/api/refresh-events', (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.setHeader('Allow', 'POST')
          res.end('Method Not Allowed')
          return
        }
        const scriptPath = path.join(__dirname, 'scripts', 'crawl_events.py')
        const child = spawn('python3', [scriptPath], { cwd: __dirname })
        let stderr = ''
        child.stdout.on('data', (chunk) => {
          console.info('[crawler]', chunk.toString().trim())
        })
        child.stderr.on('data', (chunk) => {
          stderr += chunk.toString()
        })
        child.on('close', (code) => {
          if (code === 0) {
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ ok: true }))
          } else {
            res.statusCode = 500
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ ok: false, error: stderr || `Exited with ${code}` }))
          }
        })
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), crawlApiPlugin()],
})
