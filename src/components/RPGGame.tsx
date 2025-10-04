import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../lib/auth'
import { GameState, GameMessage } from '../types/game'
import { 
  createInitialGameState, 
  performSkillCheck, 
  generateAIResponse, 
  isGameComplete,
  generateCompletionMessage 
} from '../lib/gameLogic'

const RPGGame: React.FC = () => {
  const { user, signOut } = useAuth()
  const [gameState, setGameState] = useState<GameState>(createInitialGameState())
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

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

  const handlePlayerAction = async (action: string) => {
    if (isProcessing || gameState.isGameComplete) return

    setIsProcessing(true)

    // Add player message
    const playerMessage: GameMessage = {
      id: `player-${Date.now()}`,
      type: 'player',
      content: action,
      timestamp: new Date()
    }

    // Perform skill check
    const rollResult = performSkillCheck(gameState.character.skill)
    
    // Generate AI response
    const aiResponse = generateAIResponse(action, rollResult, gameState.currentScene)
    
    // Add AI message with roll result
    const aiMessage: GameMessage = {
      id: `ai-${Date.now()}`,
      type: 'ai',
      content: aiResponse,
      timestamp: new Date(),
      rollResult
    }

    // Update game state
    const newSuccesses = rollResult.success ? gameState.successes + 1 : gameState.successes
    const gameComplete = isGameComplete(newSuccesses)

    setGameState(prev => ({
      ...prev,
      messages: [...prev.messages, playerMessage, aiMessage],
      successes: newSuccesses,
      isGameComplete: gameComplete
    }))

    // Add completion message if game is complete
    if (gameComplete) {
      setTimeout(() => {
        const completionMessage: GameMessage = {
          id: `completion-${Date.now()}`,
          type: 'ai',
          content: generateCompletionMessage(),
          timestamp: new Date()
        }
        
        setGameState(prev => ({
          ...prev,
          messages: [...prev.messages, completionMessage]
        }))
      }, 1000)
    }

    setIsProcessing(false)
    setInputValue('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim()) {
      handlePlayerAction(inputValue.trim())
    }
  }

  const resetGame = () => {
    setGameState(createInitialGameState())
    setInputValue('')
    setIsProcessing(false)
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
          {isProcessing && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'rgba(255, 255, 255, 0.6)',
              fontStyle: 'italic'
            }}>
              <div style={{
                width: '20px',
                height: '20px',
                border: '2px solid rgba(255, 215, 0, 0.3)',
                borderTop: '2px solid #ffd700',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              The AI Gamemaster is thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        {!gameState.isGameComplete && (
          <form onSubmit={handleSubmit} style={{
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '1.5rem',
            display: 'flex',
            gap: '1rem'
          }}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Describe your action (e.g., 'I try to hack the terminal')"
              disabled={isProcessing}
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
              disabled={isProcessing || !inputValue.trim()}
              style={{
                background: isProcessing || !inputValue.trim() 
                  ? 'rgba(255, 255, 255, 0.1)' 
                  : 'rgba(78, 205, 196, 0.2)',
                border: `1px solid ${isProcessing || !inputValue.trim() 
                  ? 'rgba(255, 255, 255, 0.2)' 
                  : 'rgba(78, 205, 196, 0.5)'}`,
                color: isProcessing || !inputValue.trim() 
                  ? 'rgba(255, 255, 255, 0.4)' 
                  : '#4ecdc4',
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                borderRadius: '8px',
                cursor: isProcessing || !inputValue.trim() ? 'not-allowed' : 'pointer'
              }}
            >
              {isProcessing ? '⏳' : '🎲 Roll'}
            </button>
          </form>
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
