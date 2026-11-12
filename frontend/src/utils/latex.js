import katex from 'katex'

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function renderLatex(content) {
  if (!content) return ''

  const source = String(content)
  const placeholders = []
  const hold = (html) => {
    const key = `\u0000KATEX${placeholders.length}\u0000`
    placeholders.push(html)
    return key
  }

  let processed = source
  try {
    processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
      try {
        return hold(katex.renderToString(latex, { throwOnError: false, displayMode: true }))
      } catch {
        return hold(escapeHtml(match))
      }
    })
    processed = processed.replace(/\$([^$\n]+?)\$/g, (match, latex) => {
      try {
        return hold(katex.renderToString(latex, { throwOnError: false }))
      } catch {
        return hold(escapeHtml(match))
      }
    })
  } catch {
    return escapeHtml(source).replace(/\r?\n/g, '<br>')
  }

  // 公式先占位，再转义其余文本，避免把 $a<b$ 里的 < 转成实体
  processed = escapeHtml(processed).replace(/\r?\n/g, '<br>')
  placeholders.forEach((html, index) => {
    processed = processed.split(`\u0000KATEX${index}\u0000`).join(html)
  })
  return processed
}
