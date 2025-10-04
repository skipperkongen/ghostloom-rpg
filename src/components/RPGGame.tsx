import React, { useState, useRef, useEffect, useReducer } from 'react'
import { useAuth } from '../lib/auth'
import { 
  createInitialGameState, 
  gameReducer,
  rollD6
} from '../lib/gameLogic'

const RPGGame: React.FC = () => {
  const { user, signOut } = useAuth()
  const [gameState, dispatch] = useReducer(gameReducer, createInitialGameState())
  const [intentInput, setIntentInput] = useState('')
  const [rollInput, setRollInput] = useState('')
  const [usePhysicalRoll, setUsePhysicalRoll] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const rollInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [gameState.messages])

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  const handleIntentSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (intentInput.trim() && !gameState.isGameComplete) {
      dispatch({ type: 'INTENT_SUBMITTED', intent: intentInput.trim() })
      setIntentInput('')
      // Focus roll input only if physical roll mode is enabled
      if (usePhysicalRoll) {
        setTimeout(() => rollInputRef.current?.focus(), 100)
      }
    }
  }

  const handleRollSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const roll = parseInt(rollInput)
    
    if (gameState.pendingIntent && roll >= 1 && roll <= 6) {
      dispatch({ type: 'ROLL_COMMITTED', roll })
      setRollInput('')
    }
  }

  const handleDefaultRoll = () => {
    if (gameState.pendingIntent && !usePhysicalRoll) {
      const roll = rollD6()
      dispatch({ type: 'ROLL_COMMITTED', roll })
      setRollInput('')
    }
  }

  const resetGame = () => {
    dispatch({ type: 'RESET' })
    setIntentInput('')
    setRollInput('')
  }


  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      padding: '20px'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <h1 style={{ fontSize: '2rem', margin: 0 }}>
            🎲 Ghostloom RPG
          </h1>
          <p style={{ 
            color: 'rgba(255, 255, 255, 0.7)', 
            margin: '0.25rem 0 0 0',
            fontSize: '0.9rem'
          }}>
            Welcome, {user?.email} • Skill: {gameState.character.skill} • Successes: {gameState.successes}/3
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={resetGame}
            style={{
              background: 'rgba(255, 215, 0, 0.2)',
              border: '1px solid rgba(255, 215, 0, 0.5)',
              color: '#ffd700',
              padding: '0.5rem 1rem',
              fontSize: '0.9rem'
            }}
          >
            🔄 New Game
          </button>
          <button
            onClick={handleSignOut}
            style={{
              background: 'rgba(255, 107, 107, 0.2)',
              border: '1px solid rgba(255, 107, 107, 0.5)',
              color: '#ff6b6b',
              padding: '0.5rem 1rem',
              fontSize: '0.9rem'
            }}
          >
            🚪 Log Out
          </button>
        </div>
      </div>

      {/* Game Messages */}
      <div className="card" style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: '400px',
        maxHeight: '60vh',
        overflow: 'hidden'
      }}>
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          {gameState.messages.map((message) => (
            <div
              key={message.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem'
              }}>
                <span style={{
                  fontWeight: 'bold',
                  color: message.type === 'ai' ? '#ffd700' : '#4ecdc4'
                }}>
                  {message.type === 'ai' ? '🎭 AI Gamemaster' : '👤 You'}
                </span>
                {message.rollResult && (
                  <span style={{
                    fontSize: '0.8rem',
                    color: 'rgba(255, 255, 255, 0.6)',
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px'
                  }}>
                    🎲 Rolled {message.rollResult.dice} (≤{message.rollResult.skill}) = {message.rollResult.success ? '✅ Success' : '❌ Failure'}
                  </span>
                )}
              </div>
              <div style={{
                background: message.type === 'ai' 
                  ? 'rgba(255, 215, 0, 0.1)' 
                  : 'rgba(78, 205, 196, 0.1)',
                border: `1px solid ${message.type === 'ai' 
                  ? 'rgba(255, 215, 0, 0.3)' 
                  : 'rgba(78, 205, 196, 0.3)'}`,
                borderRadius: '8px',
                padding: '1rem',
                color: 'rgba(255, 255, 255, 0.9)',
                lineHeight: '1.5'
              }}>
                {message.content}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Two-Step Input Form */}
        {!gameState.isGameComplete && (
          <div style={{
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem'
          }}>
            {/* Step 1: Intent Input */}
            <form onSubmit={handleIntentSubmit} style={{
              display: 'flex',
              gap: '1rem',
              alignItems: 'center'
            }}>
              <input
                type="text"
                value={intentInput}
                onChange={(e) => setIntentInput(e.target.value)}
                placeholder="Describe your action (e.g., 'I try to hack the terminal')"
                disabled={gameState.isGameComplete}
                style={{
                  flex: 1,
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  color: 'white',
                  fontSize: '1rem'
                }}
              />
              <button
                type="submit"
                disabled={!intentInput.trim() || gameState.isGameComplete}
                style={{
                  background: !intentInput.trim() || gameState.isGameComplete
                    ? 'rgba(255, 255, 255, 0.1)' 
                    : 'rgba(78, 205, 196, 0.2)',
                  border: `1px solid ${!intentInput.trim() || gameState.isGameComplete
                    ? 'rgba(255, 255, 255, 0.2)' 
                    : 'rgba(78, 205, 196, 0.5)'}`,
                  color: !intentInput.trim() || gameState.isGameComplete
                    ? 'rgba(255, 255, 255, 0.4)' 
                    : '#4ecdc4',
                  padding: '0.75rem 1.5rem',
                  fontSize: '1rem',
                  borderRadius: '8px',
                  cursor: !intentInput.trim() || gameState.isGameComplete ? 'not-allowed' : 'pointer'
                }}
              >
                Submit Intent
              </button>
            </form>

            {/* Step 2: Roll Action */}
            {gameState.pendingIntent && (
              <div style={{
                display: 'flex',
                gap: '1rem',
                alignItems: 'center',
                padding: '1rem',
                background: 'rgba(255, 215, 0, 0.1)',
                border: '1px solid rgba(255, 215, 0, 0.3)',
                borderRadius: '8px'
              }}>
                <div style={{ color: '#ffd700', fontWeight: 'bold' }}>
                  Pending: "{gameState.pendingIntent}"
                </div>
                
                {/* Default RNG Roll Button */}
                {!usePhysicalRoll && (
                  <button
                    type="button"
                    onClick={handleDefaultRoll}
                    disabled={gameState.isGameComplete}
                    style={{
                      background: gameState.isGameComplete
                        ? 'rgba(255, 255, 255, 0.1)' 
                        : 'rgba(78, 205, 196, 0.2)',
                      border: `1px solid ${gameState.isGameComplete
                        ? 'rgba(255, 255, 255, 0.2)' 
                        : 'rgba(78, 205, 196, 0.5)'}`,
                      color: gameState.isGameComplete
                        ? 'rgba(255, 255, 255, 0.4)' 
                        : '#4ecdc4',
                      padding: '0.75rem 1.5rem',
                      fontSize: '1rem',
                      borderRadius: '8px',
                      cursor: gameState.isGameComplete ? 'not-allowed' : 'pointer',
                      marginLeft: 'auto'
                    }}
                  >
                    🎲 Roll Dice
                  </button>
                )}

                {/* Physical Roll Input */}
                {usePhysicalRoll && (
                  <div style={{ flex: 1, display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      ref={rollInputRef}
                      type="number"
                      min="1"
                      max="6"
                      value={rollInput}
                      onChange={(e) => setRollInput(e.target.value)}
                      placeholder="1-6"
                      disabled={gameState.isGameComplete}
                      style={{
                        width: '80px',
                        background: 'rgba(255, 255, 255, 0.1)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '8px',
                        padding: '0.5rem',
                        color: 'white',
                        fontSize: '1rem',
                        textAlign: 'center'
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleRollSubmit}
                      disabled={!rollInput || gameState.isGameComplete}
                      style={{
                        background: !rollInput || gameState.isGameComplete
                          ? 'rgba(255, 255, 255, 0.1)' 
                          : 'rgba(255, 215, 0, 0.2)',
                        border: `1px solid ${!rollInput || gameState.isGameComplete
                          ? 'rgba(255, 255, 255, 0.2)' 
                          : 'rgba(255, 215, 0, 0.5)'}`,
                        color: !rollInput || gameState.isGameComplete
                          ? 'rgba(255, 255, 255, 0.4)' 
                          : '#ffd700',
                        padding: '0.5rem 1rem',
                        fontSize: '0.9rem',
                        borderRadius: '8px',
                        cursor: !rollInput || gameState.isGameComplete ? 'not-allowed' : 'pointer'
                      }}
                    >
                      Submit Roll
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Physical Roll Toggle - Only show when there's a pending intent */}
            {gameState.pendingIntent && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.9rem',
                color: 'rgba(255, 255, 255, 0.7)'
              }}>
                <input
                  type="checkbox"
                  id="usePhysicalRoll"
                  checked={usePhysicalRoll}
                  onChange={(e) => setUsePhysicalRoll(e.target.checked)}
                  style={{ margin: 0 }}
                />
                <label htmlFor="usePhysicalRoll">Use Physical Dice</label>
              </div>
            )}
          </div>
        )}

        {gameState.isGameComplete && (
          <div style={{
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '1.5rem',
            textAlign: 'center'
          }}>
            <button
              onClick={resetGame}
              style={{
                background: 'rgba(255, 215, 0, 0.2)',
                border: '1px solid rgba(255, 215, 0, 0.5)',
                color: '#ffd700',
                padding: '0.75rem 2rem',
                fontSize: '1.1rem',
                borderRadius: '8px',
                cursor: 'pointer'
              }}
            >
              🎮 Start New Adventure
            </button>
          </div>
        )}
      </div>

      {/* CSS for spinner animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default RPGGame
