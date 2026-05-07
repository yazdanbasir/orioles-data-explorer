import { useState, useEffect, useCallback, useRef } from 'react'

const SORT_CYCLE = { null: 'asc', asc: 'desc', desc: null }
const SORT_ICON  = { asc: ' ↑', desc: ' ↓', null: '' }

export default function TableView() {
  const [tables, setTables]   = useState([])
  const [table, setTable]     = useState('')
  const [columns, setColumns] = useState([])
  const [rows, setRows]       = useState([])
  const [page, setPage]       = useState(1)
  const [pages, setPages]     = useState(1)
  const [total, setTotal]     = useState(0)
  const [sort, setSort]       = useState({ col: null, dir: null })
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const sentinelRef           = useRef(null)

  useEffect(() => {
    fetch('/api/tables')
      .then(r => r.json())
      .then(data => { setTables(data); setTable(data[0] || '') })
  }, [])

  // Reset when table or sort changes
  useEffect(() => {
    setRows([])
    setPage(1)
    setHasMore(true)
  }, [table, sort])

  const fetchPage = useCallback((pageNum) => {
    if (!table || loading) return
    setLoading(true)
    const params = new URLSearchParams({ page: pageNum, limit: 50 })
    if (sort.col) { params.set('sort', sort.col); params.set('dir', sort.dir) }

    fetch(`/api/tables/${table}?${params}`)
      .then(r => r.json())
      .then(data => {
        setColumns(data.columns)
        setTotal(data.total)
        setPages(data.pages)
        setRows(prev => pageNum === 1 ? data.rows : [...prev, ...data.rows])
        setHasMore(pageNum < data.pages)
        setLoading(false)
      })
  }, [table, sort, loading])

  // Load first page whenever table/sort resets
  useEffect(() => {
    if (table) fetchPage(1)
  }, [table, sort]) // eslint-disable-line

  // Infinite scroll via IntersectionObserver on the sentinel div
  useEffect(() => {
    if (!sentinelRef.current) return
    const observer = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore && !loading) {
        setPage(prev => {
          const next = prev + 1
          fetchPage(next)
          return next
        })
      }
    }, { threshold: 0.1 })
    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [hasMore, loading, fetchPage])

  function handleTableChange(e) {
    setTable(e.target.value)
    setSort({ col: null, dir: null })
  }

  function handleSort(col) {
    setSort(prev => {
      const nextDir = prev.col === col ? SORT_CYCLE[prev.dir] : 'asc'
      return { col: nextDir ? col : null, dir: nextDir }
    })
  }

  return (
    <section className="table-section">
      <div className="table-toolbar">
        <label htmlFor="table-select">Table</label>
        <select id="table-select" className="table-select" value={table} onChange={handleTableChange}>
          {tables.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="row-count">{total.toLocaleString()} rows</span>
      </div>

      <div className="table-wrap">
        {columns.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className={sort.col === col ? 'sorted' : ''}
                  >
                    {col}{sort.col === col ? SORT_ICON[sort.dir] : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col} className={row[col] == null ? 'null-val' : ''}>
                      {row[col] ?? 'null'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Sentinel — triggers next page load when scrolled into view */}
        <div ref={sentinelRef} style={{ height: 1 }} />

        {loading && (
          <div className="loading">
            <div className="loading-dot" />
            <div className="loading-dot" />
            <div className="loading-dot" />
          </div>
        )}

      </div>
    </section>
  )
}
