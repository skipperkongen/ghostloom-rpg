import React, { useState } from 'react'
import { useAuth } from '../lib/auth'

const LoginScreen: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const { signIn, signUp } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      if (isLogin) {
        await signIn(email, password)
      } else {
        await signUp(email, password)
        setMessage('Check your email for the confirmation link!')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
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
        maxWidth: '400px',
        padding: '2rem',
        textAlign: 'center'
      }}>
        {/* Logo/Title */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
            ⚔️ Ghostloom
          </h1>
          <p style={{ 
            color: 'rgba(255, 255, 255, 0.7)', 
            fontSize: '1.1rem',
            margin: 0 
          }}>
            Enter the realm of endless adventures
          </p>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{ width: '100%' }}
            />
          </div>
          
          <div>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: '100%' }}
              minLength={6}
            />
          </div>

          {error && (
            <div style={{ 
              color: '#ff6b6b', 
              fontSize: '0.9rem',
              padding: '0.5rem',
              background: 'rgba(255, 107, 107, 0.1)',
              borderRadius: '6px',
              border: '1px solid rgba(255, 107, 107, 0.3)'
            }}>
              {error}
            </div>
          )}

          {message && (
            <div style={{ 
              color: '#4ecdc4', 
              fontSize: '0.9rem',
              padding: '0.5rem',
              background: 'rgba(78, 205, 196, 0.1)',
              borderRadius: '6px',
              border: '1px solid rgba(78, 205, 196, 0.3)'
            }}>
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.75rem',
              fontSize: '1.1rem',
              fontWeight: '600',
              background: 'linear-gradient(45deg, #ffd700, #ff6b35)',
              border: 'none',
              color: '#1a1a1a',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'all 0.3s ease'
            }}
          >
            {loading ? '⏳' : isLogin ? '🗡️ Enter the Realm' : '✨ Begin Adventure'}
          </button>
        </form>

        {/* Toggle between login/signup */}
        <div style={{ 
          marginTop: '1.5rem', 
          paddingTop: '1.5rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <p style={{ color: 'rgba(255, 255, 255, 0.7)', margin: '0 0 1rem 0' }}>
            {isLogin ? "New to the realm?" : "Already have an account?"}
          </p>
          <button
            onClick={() => {
              setIsLogin(!isLogin)
              setError(null)
              setMessage(null)
            }}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              color: '#ffd700',
              fontSize: '0.9rem',
              padding: '0.5rem 1rem'
            }}
          >
            {isLogin ? 'Create Account' : 'Sign In'}
          </button>
        </div>

        {/* Role-playing flavor text */}
        <div style={{ 
          marginTop: '2rem',
          fontSize: '0.8rem',
          color: 'rgba(255, 255, 255, 0.5)',
          fontStyle: 'italic'
        }}>
          "In the mystical realm of Ghostloom, every login is a step into legend..."
        </div>
      </div>
    </div>
  )
}

export default LoginScreen
