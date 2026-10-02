import { useState } from 'react'

const EXAMPLES = [
  'What is the expense ratio of HDFC Large Cap Fund?',
  'What is the ELSS lock-in period?',
  'What is the minimum SIP amount?',
]

function App() {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)

  async function send() {
    if (!question.trim() || loading) return
    const q = question.trim()
    setMessages(m => [...m, { role: 'user', text: q }])
    setQuestion('')
    setLoading(true)
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })
      const j = await r.json()
      setMessages(m => [...m, { role: 'assistant', text: j.answer, sources: j.sources || [] }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', text: 'Error contacting server. Is the backend running on port 8002?' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '30px auto', fontFamily: 'Segoe UI, Arial, sans-serif', padding: '0 16px' }}>
      <h1 style={{ color: '#1e3a8a' }}>Mutual Fund FAQ Assistant</h1>
      <p><b>Welcome!</b> Ask factual questions about our HDFC mutual fund schemes.</p>
      <ul>
        {EXAMPLES.map((e, i) => <li key={i} style={{ cursor: 'pointer' }} onClick={() => setQuestion(e)}>{e}</li>)}
      </ul>
      <p><i>Facts-only. No investment advice.</i></p>
      <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12, height: 380, overflowY: 'auto', marginBottom: 12 }}>
        {messages.map((m, i) => (
          <div key={i}>
            <div style={{ fontWeight: m.role === 'user' ? 700 : 400, marginTop: 10 }}>
              {m.role === 'user' ? 'You: ' : 'Assistant: '}{m.text}
            </div>
            {m.sources && m.sources.length > 0 && (
              <div style={{ fontSize: 13, color: '#555' }}>
                <b>Sources:</b><br />
                {m.sources.map((s, j) => <span key={j}><a href={s.source_url || '#'} target="_blank" rel="noreferrer">{s.source_url || s.filename}</a><br /></span>)}
              </div>
            )}
          </div>
        ))}
        {loading && <div><i>Thinking�</i></div>}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input style={{ flex: 1, padding: 10, borderRadius: 6, border: '1px solid #bbb' }} value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Type your question..." />
        <button style={{ padding: '10px 16px', border: 'none', background: '#2563eb', color: 'white', borderRadius: 6, cursor: 'pointer' }} onClick={send}>Ask</button>
      </div>
    </div>
  )
}

export default App
