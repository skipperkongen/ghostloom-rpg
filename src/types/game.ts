export interface Character {
  skill: number; // 1-6
}

export interface TurnRecord {
  id: string;
  intent: string;
  roll: number;
  success: boolean;
  narratorText: string;
  timestamp: Date;
}

export interface GameState {
  character: Character;
  successes: number;
  isGameComplete: boolean;
  currentScene: string;
  messages: GameMessage[];
  pendingIntent: string | null;
  turns: TurnRecord[];
}

export interface GameMessage {
  id: string;
  type: 'ai' | 'player';
  content: string;
  timestamp: Date;
  rollResult?: {
    dice: number;
    skill: number;
    success: boolean;
  };
}

// Pure reducer actions
export type GameAction = 
  | { type: 'INTENT_SUBMITTED'; intent: string }
  | { type: 'ROLL_COMMITTED'; roll: number }
  | { type: 'RESET' }

export interface DiceRoll {
  dice: number;
  skill: number;
  success: boolean;
}
