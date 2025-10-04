import React from 'react'
import { AuthProvider, useAuth } from './lib/auth'
import LoginScreen from './components/LoginScreen'
import RPGGame from './components/RPGGame'

const AppContent: React.FC = () => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{
          width: '50px',
          height: '50px',
          border: '3px solid rgba(255, 215, 0, 0.3)',
          borderTop: '3px solid #ffd700',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <p style={{ color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>
          Loading your adventure...
        </p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return user ? <RPGGame /> : <LoginScreen />
}

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
