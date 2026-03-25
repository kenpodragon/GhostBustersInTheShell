import { DocumentProvider, useDocument } from '../context/DocumentContext'
import InputView from '../components/InputView'

function WorkflowContent() {
  const { activeView } = useDocument()

  switch (activeView) {
    case 'input':
      return <InputView />
    case 'sections':
      return <div className="card"><p className="text-muted">Section list coming soon...</p></div>
    case 'focus':
      return <div className="card"><p className="text-muted">Focus mode coming soon...</p></div>
    case 'preview':
      return <div className="card"><p className="text-muted">Preview coming soon...</p></div>
  }
}

export default function DocumentWorkflow() {
  return (
    <DocumentProvider>
      <WorkflowContent />
    </DocumentProvider>
  )
}
