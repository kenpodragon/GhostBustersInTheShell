import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DocumentWorkflow from './pages/DocumentWorkflow'
import VoiceProfilesPage from './pages/VoiceProfilesPage'
import RulesConfiguratorPage from './pages/RulesConfiguratorPage'
import ReportView from './components/ReportView'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DocumentWorkflow />} />
          <Route path="/voice-profiles" element={<VoiceProfilesPage />} />
          <Route path="/rules" element={<RulesConfiguratorPage />} />
          <Route path="/report/:id" element={<ReportView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
