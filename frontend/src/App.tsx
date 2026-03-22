import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import AnalyzePage from './pages/AnalyzePage'
import DocumentsPage from './pages/DocumentsPage'
import VoiceProfilesPage from './pages/VoiceProfilesPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<AnalyzePage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/voice-profiles" element={<VoiceProfilesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
