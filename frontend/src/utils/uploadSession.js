const STORAGE_KEY = 'upload_session'
const PDF_SESSION_KEY = 'pdf_session'

export function getUploadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const obj = JSON.parse(raw)
    if (obj && obj.session_id && obj.secret) return obj
    return null
  } catch {
    return null
  }
}

export function setUploadSession(session) {
  if (!session || !session.session_id || !session.secret) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    session_id: session.session_id,
    secret: session.secret
  }))
}

export function clearUploadSession() {
  localStorage.removeItem(STORAGE_KEY)
}

export async function ensureUploadSession(api) {
  const existing = getUploadSession()
  if (existing) return existing
  const res = await api.post('/questions/upload-session')
  const session = { session_id: res.session_id, secret: res.secret }
  setUploadSession(session)
  return session
}

export async function cleanupUploadSessionAuth(api) {
  const session = getUploadSession()
  if (!session) return
  try {
    await api.post(`/questions/upload-session/${encodeURIComponent(session.session_id)}/cleanup`)
  } catch {
    // 忽略错误，交给服务端定期清理兜底
  } finally {
    clearUploadSession()
  }
}

export async function cleanupUploadSessionNoAuth() {
  const session = getUploadSession()
  if (!session) return
  try {
    await fetch('/api/questions/upload-session/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(session)
    })
  } catch {
    // 忽略错误，交给服务端定期清理兜底
  } finally {
    clearUploadSession()
  }
}

// ========== PDF 预览会话 ==========

export function getPdfSessionId() {
  return sessionStorage.getItem(PDF_SESSION_KEY)
}

export function setPdfSessionId(sessionId) {
  if (sessionId) {
    sessionStorage.setItem(PDF_SESSION_KEY, sessionId)
  }
}

export function clearPdfSessionId() {
  sessionStorage.removeItem(PDF_SESSION_KEY)
}

export async function cleanupPdfSessionAuth(api) {
  const sessionId = getPdfSessionId()
  if (!sessionId) return
  try {
    await api.post('/pdf/session/cleanup', { session_id: sessionId })
  } catch {
    // 忽略
  } finally {
    clearPdfSessionId()
  }
}

export async function cleanupPdfSessionNoAuth() {
  const sessionId = getPdfSessionId()
  if (!sessionId) return
  try {
    await fetch('/api/pdf/session/cleanup-noauth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    })
  } catch {
    // 忽略
  } finally {
    clearPdfSessionId()
  }
}

