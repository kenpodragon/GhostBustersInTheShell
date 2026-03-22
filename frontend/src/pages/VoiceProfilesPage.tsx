function VoiceProfilesPage() {
  return (
    <div>
      <h1 style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
        {'>'} Voice Profiles_
      </h1>
      <div className="card">
        <div className="card-header">Your Voice Profiles</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Create a voice profile by uploading writing samples (2000+ words recommended).
          The system will analyze your writing style and generate rules to humanize AI text
          in your voice.
        </p>
      </div>
    </div>
  )
}

export default VoiceProfilesPage
