function DocumentsPage() {
  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} Document History_
      </h1>
      <div className="card">
        <div className="card-header">Stored Documents</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No documents yet. Upload and analyze a document from the scanner to see it here.
        </p>
      </div>
    </div>
  )
}

export default DocumentsPage
