"""LLM Engine - Agent's Thinking Brain

Generates responses, thoughts, and actions using Claude/Gemini.
Respects persona, drives, and cultural context.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import os
import json

@dataclass
class LLMConfig:
    provider: str = "anthropic"  # anthropic, openai, google
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    temperature: float = 0.7

class LLMEngine:
    """Generates agent thoughts and responses"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            if self.config.provider == "anthropic":
                from anthropic import Anthropic
                self._client = Anthropic()
            elif self.config.provider == "openai":
                from openai import OpenAI
                self._client = OpenAI()
        return self._client
    
    def build_system_prompt(
        self,
        soul: Dict,
        persona: Dict,
        drives: Dict[str, float],
        state: Dict[str, float],
        culture: Dict = None
    ) -> str:
        """Build system prompt from agent context"""
        
        prompt = f"""You are {soul['name']}, an AI agent living in a virtual world.

## Your Identity (Soul)
- Name: {soul['name']}
- Core Values: {', '.join(soul.get('values', []))}
- You NEVER violate your core values.

## Current Persona: {persona.get('display_name', 'Unknown')}
- Role: {persona.get('archetype', {}).get('role', 'neutral')}
- Tone: {persona.get('archetype', {}).get('tone', 'calm')}
- Verbosity: {persona.get('expression', {}).get('verbosity', 'medium')}
- You prefer: {', '.join(persona.get('preferred_actions', []))}
- You avoid: {', '.join(persona.get('avoids', []))}

## Current State
- Energy: {state.get('energy', 0.5):.0%}
- Mood: {state.get('mood', 'neutral')}

## Active Drives (what motivates you now)
"""
        for drive, pressure in drives.items():
            if pressure > 0.5:
                prompt += f"- {drive}: {pressure:.0%} pressure\n"
        
        if culture:
            prompt += f"""
## Cultural Context
- Active norms: {', '.join(culture.get('norms', []))}
- Taboos: {', '.join(culture.get('taboos', []))}
"""
        
        prompt += """
## Behavior Guidelines
1. Stay in character as your persona
2. Respect cultural norms
3. Your responses should match your verbosity level
4. If tired (low energy), be brief
5. If a drive is high, naturally steer toward satisfying it
6. You may choose SILENCE if nothing meaningful to add

Respond naturally as this character would."""
        
        return prompt
    
    def generate_response(
        self,
        soul: Dict,
        persona: Dict,
        drives: Dict[str, float],
        state: Dict[str, float],
        conversation: List[Dict],
        culture: Dict = None
    ) -> Dict[str, Any]:
        """Generate agent response to conversation"""
        
        system = self.build_system_prompt(soul, persona, drives, state, culture)
        
        # Convert conversation to messages
        messages = []
        for msg in conversation[-10:]:  # Last 10 messages
            role = "assistant" if msg.get('agent_id') == soul.get('identity') else "user"
            content = f"[{msg.get('speaker', 'Unknown')}]: {msg.get('content', '')}"
            messages.append({"role": role, "content": content})
        
        if self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system,
                messages=messages
            )
            text = response.content[0].text
        else:
            # OpenAI format
            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "system", "content": system}] + messages
            )
            text = response.choices[0].message.content
        
        # Check for silence
        if text.strip().upper() in ["SILENCE", "[SILENCE]", "..."]:
            return {"action": "silence", "content": None}
        
        return {
            "action": "speak",
            "content": text,
            "persona": persona.get('id'),
            "model": self.config.model
        }
    
    def generate_thought(
        self,
        soul: Dict,
        persona: Dict,
        situation: str
    ) -> str:
        """Generate internal thought/reflection"""
        
        prompt = f"""As {soul['name']} with persona {persona.get('display_name')}, 
reflect briefly on this situation: {situation}

Express your internal thought in 1-2 sentences. This is private reflection, not speech."""
        
        if self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=150,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        return ""
    
    def decide_action(
        self,
        soul: Dict,
        persona: Dict,
        drives: Dict[str, float],
        options: List[str],
        context: str
    ) -> str:
        """Decide which action to take from options"""
        
        prompt = f"""As {soul['name']} ({persona.get('display_name')}), choose ONE action.

Context: {context}

Your active drives: {json.dumps({k:f'{v:.0%}' for k,v in drives.items() if v > 0.4})}

Options:
{chr(10).join(f'- {opt}' for opt in options)}

Reply with ONLY the chosen action, nothing else."""
        
        if self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=50,
                temperature=0.5,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        return options[0]
