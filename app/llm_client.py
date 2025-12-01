"""LLM client abstraction with stub implementation."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import random


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def init_story(self, seed: str) -> tuple[Dict[str, Any], str]:
        """
        Initialize a new story from a seed prompt.
        
        Args:
            seed: User's initial story wish or prompt
            
        Returns:
            Tuple of (initial_state_dict, narrative_text)
        """
        pass
    
    @abstractmethod
    def continue_story(self, state: Dict[str, Any], action: str) -> tuple[Dict[str, Any], str]:
        """
        Continue the story based on user action.
        
        Args:
            state: Current state dictionary
            action: User's action/choice
            
        Returns:
            Tuple of (updated_state_dict, narrative_text)
        """
        pass


class StubLLMClient(LLMClient):
    """Stub LLM implementation for testing and development."""
    
    def __init__(self):
        """Initialize the stub client."""
        self.story_templates = [
            {
                "location": "ancient forest",
                "mood": "mysterious",
                "characters": ["wandering traveler", "wise old tree", "shadowy figure"]
            },
            {
                "location": "space station",
                "mood": "tense",
                "characters": ["crew member", "AI companion", "alien visitor"]
            },
            {
                "location": "medieval castle",
                "mood": "adventurous",
                "characters": ["knight", "wizard", "dragon"]
            }
        ]
    
    def _generate_story_context(self, seed: str) -> Dict[str, Any]:
        """Generate initial story context from seed."""
        template = random.choice(self.story_templates)
        return {
            "location": template["location"],
            "mood": template["mood"],
            "characters": template["characters"],
            "events": [],
            "inventory": []
        }
    
    def _generate_narrative(self, context: Dict[str, Any], action: str = None, is_init: bool = False) -> str:
        """Generate narrative text based on context."""
        location = context.get("location", "unknown place")
        mood = context.get("mood", "neutral")
        characters = context.get("characters", [])
        events = context.get("events", [])
        
        if is_init:
            # Initial narrative
            char_intro = random.choice(characters) if characters else "someone"
            narrative = (
                f"You find yourself in {location}. The atmosphere is {mood}. "
                f"Nearby, you notice {char_intro} looking in your direction. "
                f"The air seems to hold secrets, and every shadow tells a story. "
                f"Your journey begins here, shaped by the seed of your imagination: '{context.get('seed', 'adventure')}'."
            )
        else:
            # Continuation based on action
            event_count = len(events)
            narrative = (
                f"You {action.lower()}. "
                f"The {mood} atmosphere of {location} responds to your choice. "
            )
            
            if event_count == 0:
                narrative += (
                    f"Your actions ripple through the narrative, creating the first chapter of your tale. "
                    f"The story begins to take shape around you."
                )
            else:
                narrative += (
                    f"Each decision builds upon the last, weaving a complex tapestry of events. "
                    f"Your journey through {location} continues to unfold."
                )
            
            # Add a character interaction
            if characters:
                char = random.choice(characters)
                narrative += f" {char.title()} observes your actions with interest."
        
        # Always end with a question
        questions = [
            "What do you do next?",
            "How do you proceed?",
            "What is your next move?",
            "What path will you choose?",
            "What action do you take?",
        ]
        narrative += f"\n\n{random.choice(questions)}"
        
        return narrative
    
    def init_story(self, seed: str) -> tuple[Dict[str, Any], str]:
        """Initialize a new story from a seed."""
        context = self._generate_story_context(seed)
        
        # Build initial state
        initial_state = {
            "seed": seed,
            "round": 0,
            "context": context,
        }
        
        # Add seed to context for narrative generation
        context["seed"] = seed
        
        # Generate narrative
        narrative = self._generate_narrative(context, is_init=True)
        
        return initial_state, narrative
    
    def continue_story(self, state: Dict[str, Any], action: str) -> tuple[Dict[str, Any], str]:
        """Continue the story based on user action."""
        # Get current context or create new one
        context = state.get("context", {})
        current_round = state.get("round", 0)
        
        # Update context based on action
        events = context.get("events", [])
        events.append({
            "round": current_round,
            "action": action
        })
        context["events"] = events
        
        # Increment round
        new_round = current_round + 1
        
        # Build updated state (Markov property: fully self-contained)
        updated_state = {
            "seed": state.get("seed", ""),
            "round": new_round,
            "context": context,
        }
        
        # Generate narrative
        narrative = self._generate_narrative(context, action=action, is_init=False)
        
        return updated_state, narrative

