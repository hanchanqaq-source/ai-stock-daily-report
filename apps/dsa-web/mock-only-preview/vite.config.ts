import { defineConfig, type Plugin } from 'vite'

const previewBase = '/mock-only-preview'
const blockedResponse = 'MOCK_ONLY_PREVIEW_BLOCKED'
const allowedPrefixes = [
  `${previewBase}/`,
  '/src/mocks/',
  '/@vite/',
  '/node_modules/',
] as const
const allowedExactPaths = new Set([
  previewBase,
  `${previewBase}/index.html`,
  '/@react-refresh',
  '/favicon.ico',
])
const blockedPrefixes = [
  `/src/${'api'}/`,
  `/src/${'pages'}/`,
  `/src/${'stores'}/`,
  `/src/${'components'}/`,
  `/src/${'contexts'}/`,
  `/src/${'utils'}/`,
  '/api',
] as const
const blockedExactPaths = new Set([
  '/',
  '/index.html',
  '/src/main.tsx',
  '/src/App.tsx',
])

const mockOnlyPreviewGuard = (): Plugin => ({
  name: 'mock-only-preview-guard',
  configureServer(server) {
    server.middlewares.use((request, response, next) => {
      const requestUrl = request.url ?? '/'
      const path = requestUrl.split('?', 1)[0] || '/'
      const allowed = allowedExactPaths.has(path) || allowedPrefixes.some((prefix) => path.startsWith(prefix))
      const blocked = blockedExactPaths.has(path) || blockedPrefixes.some((prefix) => path === prefix || path.startsWith(prefix))

      if (!allowed || blocked) {
        response.statusCode = 403
        response.setHeader('Content-Type', 'text/plain; charset=utf-8')
        response.end(blockedResponse)
        return
      }

      next()
    })
  },
})

export default defineConfig({
  root: '.',
  base: '/',
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    open: false,
  },
  plugins: [mockOnlyPreviewGuard()],
})
