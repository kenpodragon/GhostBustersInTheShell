import { DocumentProvider, useDocument } from '../context/DocumentContext'
import InputView from '../components/InputView'
import SectionListView from '../components/SectionListView'
import FocusView from '../components/FocusView'
import PreviewView from '../components/PreviewView'

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
      return <PreviewView />
  }
}

export default function DocumentWorkflow() {
  return (
    <DocumentProvider>
      <WorkflowContent />
    </DocumentProvider>
  )
}
