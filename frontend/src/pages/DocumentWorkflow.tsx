import { DocumentProvider, useDocument } from '../context/DocumentContext'
import InputView from '../components/InputView'
import SectionListView from '../components/SectionListView'
import FocusView from '../components/FocusView'

function WorkflowContent() {
  const { activeView } = useDocument()

  switch (activeView) {
    case 'input':
      return <InputView />
    case 'sections':
      return <SectionListView />
    case 'focus':
      return <FocusView />
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
