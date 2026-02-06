"""Persona System (RFC-0007, RFC-0008)

Personas are social masks that bias behavior:
- Role (guide, trickster, observer)
- Tone (calm, playful, formal)
- Preferred actions
- Taboos/avoids
"""
from .models import Persona
from .selector import PersonaSelector
from .scoring import score_persona
