import React from 'react'
import { useAuth } from '../lib/auth'

const Dashboard: React.FC = () => {
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div className="card" style={{
        width: '100%',
        maxWidth: '600px',
        padding: '2rem',
        textAlign: 'center'
      }}>
        {/* Welcome Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
            🏰 Welcome, Adventurer!
          </h1>
          <p style={{ 
            color: 'rgba(255, 255, 255, 0.8)', 
            fontSize: '1.1rem',
            margin: 0 
          }}>
            You have successfully entered the realm of Ghostloom
          </p>
        </div>

        {/* User Info */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '8px',
          padding: '1.5rem',
          marginBottom: '2rem',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <p style={{ margin: '0.5rem 0', color: 'rgba(255, 255, 255, 0.9)' }}>
            <strong>Email:</strong> {user?.email}
          </p>
        </div>

        {/* Sign Out Button */}
        <button
          onClick={handleSignOut}
          style={{
            background: 'rgba(255, 107, 107, 0.2)',
            border: '1px solid rgba(255, 107, 107, 0.5)',
            color: '#ff6b6b',
            padding: '0.75rem 1.5rem',
            fontSize: '1rem'
          }}
        >
          🚪 Log Out
        </button>

        {/* Footer */}
        <div style={{ 
          marginTop: '2rem',
          fontSize: '0.8rem',
          color: 'rgba(255, 255, 255, 0.5)',
          fontStyle: 'italic'
        }}>
          "The adventure has only just begun..."
        </div>
      </div>
    </div>
  )
}

export default Dashboard
