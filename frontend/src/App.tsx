import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DocumentWorkflow from './pages/DocumentWorkflow'
import VoiceProfilesPage from './pages/VoiceProfilesPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DocumentWorkflow />} />
          <Route path="/voice-profiles" element={<VoiceProfilesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
