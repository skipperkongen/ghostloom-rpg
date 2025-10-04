import { GameState, GameMessage, DiceRoll, GameAction, TurnRecord } from '../types/game'

// Generate a random number between 1 and 6 (d6)
export const rollD6 = (): number => {
  return Math.floor(Math.random() * 6) + 1
}

// Check if a roll succeeds (roll <= skill)
export const checkSuccess = (dice: number, skill: number): boolean => {
  return dice <= skill
}

// Perform a skill check
export const performSkillCheck = (skill: number): DiceRoll => {
  const dice = rollD6()
  const success = checkSuccess(dice, skill)
  return { dice, skill, success }
}

// Generate AI responses based on the action and roll result
export const generateAIResponse = (
  _playerAction: string,
  rollResult: DiceRoll,
  _currentScene: string
): string => {
  const { success } = rollResult
  
  if (success) {
    // Success responses
    const successResponses = [
      `The screen flickers to life. You gain access to the system logs. You sense someone is watching...`,
      `Your nimble fingers work the mechanism perfectly. The door slides open with a hiss.`,
      `The terminal responds to your commands. You've found what you were looking for.`,
      `Your expertise pays off. The system yields its secrets to you.`,
      `Success! Your skill has overcome the challenge. You feel a sense of accomplishment.`
    ]
    
    return successResponses[Math.floor(Math.random() * successResponses.length)]
  } else {
    // Failure responses
    const failureResponses = [
      `The terminal sparks and goes dark. Your attempt has failed, and you've drawn attention.`,
      `The door remains stubbornly locked. You hear footsteps approaching from behind.`,
      `Your attempt backfires. The system has locked you out completely.`,
      `The mechanism jams. You'll need to find another way.`,
      `Your skill isn't quite enough this time. The challenge remains unconquered.`
    ]
    
    return failureResponses[Math.floor(Math.random() * failureResponses.length)]
  }
}

// Generate initial scene description
export const generateInitialScene = (): string => {
  const scenes = [
    "You stand before a locked terminal in a dark corridor. The air hums with electronic energy. What do you do?",
    "A heavy metal door blocks your path. Strange symbols glow faintly on its surface. What do you do?",
    "You find yourself in a control room filled with blinking lights and mysterious consoles. What do you do?",
    "A security system guards the way forward. Cameras and sensors watch your every move. What do you do?",
    "You've discovered a hidden chamber with ancient technology. The air crackles with power. What do you do?"
  ]
  
  return scenes[Math.floor(Math.random() * scenes.length)]
}

// Create initial game state
export const createInitialGameState = (): GameState => {
  return {
    character: { skill: 4 }, // Default skill level
    successes: 0,
    isGameComplete: false,
    currentScene: generateInitialScene(),
    messages: [
      {
        id: 'initial',
        type: 'ai',
        content: generateInitialScene(),
        timestamp: new Date()
      }
    ],
    pendingIntent: null,
    turns: []
  }
}

// Check if game is complete (3 successes)
export const isGameComplete = (successes: number): boolean => {
  return successes >= 3
}

// Generate completion message
export const generateCompletionMessage = (): string => {
  return "🎉 Mission Complete! You have successfully overcome all challenges and proven your worth as an adventurer. The realm of Ghostloom awaits your next adventure!"
}

// Generate narrator text for a turn
export const generateTurnNarration = (
  _intent: string,
  roll: number,
  skill: number,
  success: boolean
): string => {
  const skillCheck = `Rolled ${roll} (≤${skill})`
  
  if (success) {
    const successResponses = [
      `The screen flickers to life. You gain access to the system logs. You sense someone is watching...`,
      `Your nimble fingers work the mechanism perfectly. The door slides open with a hiss.`,
      `The terminal responds to your commands. You've found what you were looking for.`,
      `Your expertise pays off. The system yields its secrets to you.`,
      `Success! Your skill has overcome the challenge. You feel a sense of accomplishment.`
    ]
    const response = successResponses[Math.floor(Math.random() * successResponses.length)]
    return `${skillCheck} = ✅ Success. ${response}`
  } else {
    const failureResponses = [
      `The terminal sparks and goes dark. Your attempt has failed, and you've drawn attention.`,
      `The door remains stubbornly locked. You hear footsteps approaching from behind.`,
      `Your attempt backfires. The system has locked you out completely.`,
      `The mechanism jams. You'll need to find another way.`,
      `Your skill isn't quite enough this time. The challenge remains unconquered.`
    ]
    const response = failureResponses[Math.floor(Math.random() * failureResponses.length)]
    return `${skillCheck} = ❌ Failure. ${response}`
  }
}

// Pure reducer function - no randomness, deterministic
export const gameReducer = (state: GameState, action: GameAction): GameState => {
  switch (action.type) {
    case 'INTENT_SUBMITTED': {
      const intent = action.intent.trim()
      
      // Ignore if game is complete or intent is empty
      if (state.isGameComplete || !intent) {
        return state
      }
      
      return {
        ...state,
        pendingIntent: intent
      }
    }
    
    case 'ROLL_COMMITTED': {
      const { roll } = action
      
      // Validate roll and pending intent
      if (!state.pendingIntent || roll < 1 || roll > 6) {
        return state
      }
      
      // Calculate success
      const success = roll <= state.character.skill
      const newSuccesses = success ? state.successes + 1 : state.successes
      const gameComplete = isGameComplete(newSuccesses)
      
      // Create turn record
      const turnRecord: TurnRecord = {
        id: `turn-${Date.now()}`,
        intent: state.pendingIntent,
        roll,
        success,
        narratorText: generateTurnNarration(state.pendingIntent, roll, state.character.skill, success),
        timestamp: new Date()
      }
      
      // Add messages for this turn
      const playerMessage: GameMessage = {
        id: `player-${Date.now()}`,
        type: 'player',
        content: state.pendingIntent,
        timestamp: new Date()
      }
      
      const aiMessage: GameMessage = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: turnRecord.narratorText,
        timestamp: new Date(),
        rollResult: {
          dice: roll,
          skill: state.character.skill,
          success
        }
      }
      
      return {
        ...state,
        successes: newSuccesses,
        isGameComplete: gameComplete,
        pendingIntent: null, // Clear pending intent
        turns: [...state.turns, turnRecord],
        messages: [...state.messages, playerMessage, aiMessage]
      }
    }
    
    case 'RESET': {
      return createInitialGameState()
    }
    
    default:
      return state
  }
}
