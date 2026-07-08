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

  let safeContent = escapeHtml(content)

  try {
    const placeholders = []
    const hold = (html) => {
      const key = `\u0000KATEX${placeholders.length}\u0000`
      placeholders.push(html)
      return key
    }

    // 先处理块级公式 $$...$$，避免被行内正则吞掉
    safeContent = safeContent.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
      try {
        return hold(katex.renderToString(latex, { throwOnError: false, displayMode: true }))
      } catch {
        return match
      }
    })

    // 再处理行内公式 $...$
    safeContent = safeContent.replace(/\$([^$\n]+?)\$/g, (match, latex) => {
      try {
        return hold(katex.renderToString(latex, { throwOnError: false }))
      } catch {
        return match
      }
    })

    placeholders.forEach((html, i) => {
      safeContent = safeContent.split(`\u0000KATEX${i}\u0000`).join(html)
    })

    return safeContent
  } catch {
    return safeContent
  }
}
