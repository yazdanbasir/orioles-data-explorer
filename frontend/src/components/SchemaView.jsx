import erDiagram from '../assets/er-diagram.png'

export default function SchemaView() {
  return (
    <section className="schema-section">
      <div className="schema-header">
        <h2>Schema Diagram</h2>
        <p>Relationships between the five tables in <code>orioles.db</code>.</p>
      </div>
      <div className="schema-img-wrap">
        <img src={erDiagram} alt="ER diagram" />
      </div>
    </section>
  )
}
