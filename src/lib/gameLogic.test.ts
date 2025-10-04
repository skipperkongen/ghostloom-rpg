import { describe, it, expect, beforeEach } from 'vitest'
import { gameReducer, createInitialGameState } from './gameLogic'
import { GameState, GameAction } from '../types/game'

describe('gameReducer', () => {
  let initialState: GameState

  beforeEach(() => {
    initialState = createInitialGameState()
  })

  describe('INTENT_SUBMITTED', () => {
    it('should set pending intent when game is not complete and intent is not empty', () => {
      const action: GameAction = { type: 'INTENT_SUBMITTED', intent: 'hack the terminal' }
      const result = gameReducer(initialState, action)
      
      expect(result.pendingIntent).toBe('hack the terminal')
      expect(result.isGameComplete).toBe(false)
    })

    it('should ignore empty intent', () => {
      const action: GameAction = { type: 'INTENT_SUBMITTED', intent: '   ' }
      const result = gameReducer(initialState, action)
      
      expect(result.pendingIntent).toBe(null)
    })

    it('should ignore intent when game is complete', () => {
      const completedState = { ...initialState, isGameComplete: true }
      const action: GameAction = { type: 'INTENT_SUBMITTED', intent: 'hack the terminal' }
      const result = gameReducer(completedState, action)
      
      expect(result.pendingIntent).toBe(null)
    })

    it('should trim whitespace from intent', () => {
      const action: GameAction = { type: 'INTENT_SUBMITTED', intent: '  hack the terminal  ' }
      const result = gameReducer(initialState, action)
      
      expect(result.pendingIntent).toBe('hack the terminal')
    })
  })

  describe('ROLL_COMMITTED', () => {
    it('should succeed when roll <= skill', () => {
      // Set up state with pending intent
      const stateWithIntent = gameReducer(initialState, { 
        type: 'INTENT_SUBMITTED', 
        intent: 'hack the terminal' 
      })
      
      const action: GameAction = { type: 'ROLL_COMMITTED', roll: 3 } // skill is 4, so 3 <= 4
      const result = gameReducer(stateWithIntent, action)
      
      expect(result.successes).toBe(1)
      expect(result.pendingIntent).toBe(null)
      expect(result.turns).toHaveLength(1)
      expect(result.turns[0].success).toBe(true)
      expect(result.turns[0].roll).toBe(3)
      expect(result.turns[0].intent).toBe('hack the terminal')
    })

    it('should fail when roll > skill', () => {
      // Set up state with pending intent
      const stateWithIntent = gameReducer(initialState, { 
        type: 'INTENT_SUBMITTED', 
        intent: 'hack the terminal' 
      })
      
      const action: GameAction = { type: 'ROLL_COMMITTED', roll: 5 } // skill is 4, so 5 > 4
      const result = gameReducer(stateWithIntent, action)
      
      expect(result.successes).toBe(0)
      expect(result.pendingIntent).toBe(null)
      expect(result.turns).toHaveLength(1)
      expect(result.turns[0].success).toBe(false)
      expect(result.turns[0].roll).toBe(5)
    })

    it('should ignore roll when no pending intent', () => {
      const action: GameAction = { type: 'ROLL_COMMITTED', roll: 3 }
      const result = gameReducer(initialState, action)
      
      expect(result).toBe(initialState)
    })

    it('should ignore invalid roll values', () => {
      const stateWithIntent = gameReducer(initialState, { 
        type: 'INTENT_SUBMITTED', 
        intent: 'hack the terminal' 
      })
      
      // Test roll < 1
      const actionLow: GameAction = { type: 'ROLL_COMMITTED', roll: 0 }
      const resultLow = gameReducer(stateWithIntent, actionLow)
      expect(resultLow).toBe(stateWithIntent)
      
      // Test roll > 6
      const actionHigh: GameAction = { type: 'ROLL_COMMITTED', roll: 7 }
      const resultHigh = gameReducer(stateWithIntent, actionHigh)
      expect(resultHigh).toBe(stateWithIntent)
    })

    it('should complete game at 3 successes', () => {
      let state = { ...initialState, successes: 2 }
      
      // Set up pending intent
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'final hack' })
      
      // Commit successful roll
      const action: GameAction = { type: 'ROLL_COMMITTED', roll: 2 } // skill is 4, so 2 <= 4
      const result = gameReducer(state, action)
      
      expect(result.successes).toBe(3)
      expect(result.isGameComplete).toBe(true)
    })

    it('should not allow second roll for same intent', () => {
      // Set up state with pending intent
      const stateWithIntent = gameReducer(initialState, { 
        type: 'INTENT_SUBMITTED', 
        intent: 'hack the terminal' 
      })
      
      // First roll
      const firstRoll: GameAction = { type: 'ROLL_COMMITTED', roll: 3 }
      const afterFirstRoll = gameReducer(stateWithIntent, firstRoll)
      
      // Second roll should be ignored since pendingIntent is cleared
      const secondRoll: GameAction = { type: 'ROLL_COMMITTED', roll: 1 }
      const afterSecondRoll = gameReducer(afterFirstRoll, secondRoll)
      
      expect(afterSecondRoll.turns).toHaveLength(1)
      expect(afterSecondRoll.successes).toBe(1) // Only first roll counted
    })
  })

  describe('RESET', () => {
    it('should return to initial state', () => {
      // Create a modified state
      const modifiedState = gameReducer(initialState, { 
        type: 'INTENT_SUBMITTED', 
        intent: 'hack the terminal' 
      })
      const stateWithRoll = gameReducer(modifiedState, { type: 'ROLL_COMMITTED', roll: 3 })
      
      const action: GameAction = { type: 'RESET' }
      const result = gameReducer(stateWithRoll, action)
      
      expect(result.successes).toBe(0)
      expect(result.isGameComplete).toBe(false)
      expect(result.pendingIntent).toBe(null)
      expect(result.turns).toHaveLength(0)
      expect(result.messages).toHaveLength(1) // Only initial message
    })
  })

  describe('Edge cases', () => {
    it('should handle multiple successful turns', () => {
      let state = initialState
      
      // First turn
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'hack terminal' })
      state = gameReducer(state, { type: 'ROLL_COMMITTED', roll: 2 })
      
      // Second turn
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'unlock door' })
      state = gameReducer(state, { type: 'ROLL_COMMITTED', roll: 3 })
      
      expect(state.successes).toBe(2)
      expect(state.turns).toHaveLength(2)
      expect(state.turns[0].success).toBe(true)
      expect(state.turns[1].success).toBe(true)
    })

    it('should handle mixed success and failure', () => {
      let state = initialState
      
      // Successful turn
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'hack terminal' })
      state = gameReducer(state, { type: 'ROLL_COMMITTED', roll: 2 })
      
      // Failed turn
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'unlock door' })
      state = gameReducer(state, { type: 'ROLL_COMMITTED', roll: 5 })
      
      expect(state.successes).toBe(1)
      expect(state.turns).toHaveLength(2)
      expect(state.turns[0].success).toBe(true)
      expect(state.turns[1].success).toBe(false)
    })

    it('should maintain message history correctly', () => {
      let state = initialState
      
      // Submit intent and roll
      state = gameReducer(state, { type: 'INTENT_SUBMITTED', intent: 'hack terminal' })
      state = gameReducer(state, { type: 'ROLL_COMMITTED', roll: 3 })
      
      expect(state.messages).toHaveLength(3) // Initial + player + AI
      expect(state.messages[1].type).toBe('player')
      expect(state.messages[1].content).toBe('hack terminal')
      expect(state.messages[2].type).toBe('ai')
      expect(state.messages[2].content).toContain('Success')
      expect(state.messages[2].rollResult).toEqual({
        dice: 3,
        skill: 4,
        success: true
      })
    })
  })
})
