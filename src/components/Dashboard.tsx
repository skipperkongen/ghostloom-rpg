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
          <h3 style={{ 
            color: '#ffd700', 
            margin: '0 0 1rem 0',
            fontSize: '1.3rem'
          }}>
            🧙‍♂️ Character Status
          </h3>
          <p style={{ margin: '0.5rem 0', color: 'rgba(255, 255, 255, 0.9)' }}>
            <strong>Email:</strong> {user?.email}
          </p>
          <p style={{ margin: '0.5rem 0', color: 'rgba(255, 255, 255, 0.9)' }}>
            <strong>Level:</strong> Novice Adventurer
          </p>
          <p style={{ margin: '0.5rem 0', color: 'rgba(255, 255, 255, 0.9)' }}>
            <strong>Experience:</strong> 0 XP
          </p>
        </div>

        {/* Adventure Options */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            background: 'rgba(255, 107, 53, 0.1)',
            border: '1px solid rgba(255, 107, 53, 0.3)',
            borderRadius: '8px',
            padding: '1rem',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚔️</div>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#ff6b35' }}>Combat</h4>
            <p style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>
              Engage in epic battles
            </p>
          </div>

          <div style={{
            background: 'rgba(78, 205, 196, 0.1)',
            border: '1px solid rgba(78, 205, 196, 0.3)',
            borderRadius: '8px',
            padding: '1rem',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🏺</div>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#4ecdc4' }}>Quests</h4>
            <p style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>
              Embark on adventures
            </p>
          </div>

          <div style={{
            background: 'rgba(255, 215, 0, 0.1)',
            border: '1px solid rgba(255, 215, 0, 0.3)',
            borderRadius: '8px',
            padding: '1rem',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🎒</div>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#ffd700' }}>Inventory</h4>
            <p style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>
              Manage your gear
            </p>
          </div>
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
          🚪 Leave the Realm
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
