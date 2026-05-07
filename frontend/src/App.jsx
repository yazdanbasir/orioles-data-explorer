import { useState } from 'react'
import SchemaView from './components/SchemaView'
import TableView from './components/TableView'
import QueryView from './components/QueryView'
import oriolesLogo from './assets/orioles.png'

export default function App() {
  const [tab, setTab] = useState('data')

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <h1><span>BAL</span> · Data Explorer</h1>
        <img src={oriolesLogo} alt="Orioles" className="header-logo" />
        <nav className="tab-nav">
          <button className="tab-btn" onClick={() => setTab('data')} disabled={tab === 'data'}>
            Data
          </button>
          <button className="tab-btn" onClick={() => setTab('query')} disabled={tab === 'query'}>
            Query
          </button>
          <button className="tab-btn" onClick={() => setTab('schema')} disabled={tab === 'schema'}>
            Schema
          </button>
        </nav>
      </header>

      <main className={`content-area${tab === 'query' ? ' content-area--scroll' : ''}`}>
        {tab === 'query'  && <QueryView />}
        {tab === 'schema' && <SchemaView />}
        {tab === 'data'   && <TableView />}
      </main>
    </div>
  )
}
