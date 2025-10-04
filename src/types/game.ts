export interface Character {
  skill: number; // 1-6
}

export interface GameState {
  character: Character;
  successes: number;
  isGameComplete: boolean;
  currentScene: string;
  messages: GameMessage[];
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

export interface GameAction {
  type: 'player_action';
  description: string;
}

export interface DiceRoll {
  dice: number;
  skill: number;
  success: boolean;
}
