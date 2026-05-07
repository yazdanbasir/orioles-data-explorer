import { useState } from 'react'

const EXAMPLES = [
  "On July 8th 2025, which pitches happened at over 95mph, who threw the pitch, how old were they, and what team did they play for?",
  "What percentage of pitches did those pitchers throw over 95mph for the season?",
  "Who are the top 10 hitters in average exit velocity on fastballs in the top half of the zone?",
  "Which percentile is Oneil Cruz in for average exit velocity amongst qualifying hitters under the age of 26?",
]

export default function QueryView() {
  const [question, setQuestion] = useState('')
  const [result, setResult]     = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [lastQuestion, setLastQuestion] = useState(null)
  const [lastSql, setLastSql]           = useState(null)

  async function ask(q) {
    const text = q ?? question
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          previous_question: lastQuestion,
          previous_sql: lastSql,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Something went wrong')
      setResult(data)
      setLastQuestion(text)
      setLastSql(data.sql)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleExample(ex) {
    setQuestion(ex)
    ask(ex)
  }

  return (
    <section className="query-section">

      {/* Input bar — primary action */}
      <div className="query-input-row">
        <input
          className="query-input"
          type="text"
          placeholder="Ask anything about the data..."
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && ask()}
        />
        <button className="query-btn" onClick={() => ask()} disabled={loading}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </div>

      {/* Suggested questions */}
      <div className="query-examples">
        <span className="query-examples-label">Sample Questions</span>
        {EXAMPLES.map(ex => (
          <button key={ex} className="example-chip" onClick={() => handleExample(ex)}>
            {ex}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <div className="query-error">{error}</div>}

      {/* Results */}
      {result && (
        <div className="query-results">
          <div className="query-sql">
            <span className="sql-label">Generated SQL</span>
            <pre>{result.sql}</pre>
          </div>

          {result.rows.length === 0 ? (
            <p className="query-empty">No results.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>{result.columns.map(c => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j} className={cell === null ? 'null-val' : ''}>
                          {cell === null ? 'null' : String(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="row-count">{result.rows.length} row{result.rows.length !== 1 ? 's' : ''}</p>
        </div>
      )}
    </section>
  )
}
