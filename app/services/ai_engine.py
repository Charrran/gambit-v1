import instructor
from groq import AsyncGroq
from google import genai
from typing import List, Any, Optional
from pydantic import BaseModel, Field
from app.core.config import settings

class GeneratedOption(BaseModel):
    edge_id: str = Field(..., description="The unique ID of the specific narrative choice.")
    text: str = Field(..., description="The dynamically generated, flavorful choice text.")

class TurnNarrative(BaseModel):
    flavor_text: str = Field(..., description="A tense, 2-paragraph narrative description of the situation.")
    options: List[GeneratedOption] = Field(..., description="A list of MCQ options for the player.")

class EndingComparison(BaseModel):
    player_summary: str = Field(..., description="A summary of the player's unique story path.")
    canonical_summary: str = Field(..., description="A summary of what happened historically in 1995.")
    divergence_analysis: str = Field(..., description="An analysis of how the player's choices changed the course of history.")
    final_score: str = Field(..., description="A creative title for the ending based on the player's performance.")

class AIEngine:
    """
    Advanced AI Director (The Memory Bank).
    - Groq: Rapid-fire MCQ and narrative generation (Llama 3).
    - Gemini: Deep context processing for Canonical endings.
    """
    def __init__(self):
        # Groq Client (Fast MCQ Generation)
        self.groq_client = instructor.from_groq(
            AsyncGroq(api_key=settings.groq_api_key),
            mode=instructor.Mode.JSON
        )
        
        # Gemini Client (Dedicated to Deep Context Canonical Analysis via new google-genai SDK)
        self.gemini_client = instructor.from_genai(
            genai.Client(api_key=settings.gemini_api_key)
        )

    async def generate_spotlight_turn(self, premise: str, required_role: str, db_choices: list, player_alignments: List[str] = None) -> TurnNarrative:
        """
        Generates a tailored narrative turn using Groq.
        Incorporate player traits to influence option flavor.
        """
        traits_context = f"This player has developed the following traits: {', '.join(player_alignments)}." if player_alignments else "This player is currently a blank slate."
        
        choices_context = ""
        for i, choice in enumerate(db_choices):
            edge_id = choice['edge_id']
            action_intent = choice['action_intent']
            choices_context += f"- Option {i+1} | Edge ID: '{edge_id}' | Narrative Directive: {action_intent}\n"

        system_prompt = f"""You are an elite screenwriter for a gritty political thriller based on the 1995 Viceroy Rebellion.
Character Context: {required_role}. {traits_context}
Current Scenario: {premise}

TASK:
1. Write a 2-paragraph narrative beat. The first paragraph is descriptive; the second is introspective for {required_role}, strongly colored by their TRAITS.
2. Generate immersive MCQ choices. If the player is 'Authoritarian', their options should sound more demanding; if 'Pragmatic', they should sound more calculated.

STRICT ID MAPPING RULES:
You MUST use the exact Edge IDs provided. Map your generated text to these IDs:
{choices_context}"""

        response = await self.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Begin the turn narrative and present the choices."}
            ],
            response_model=TurnNarrative,
            max_retries=2,
        )
        
        # Deterministic Safety Injection
        for i, option in enumerate(response.options):
            if i < len(db_choices):
                option.edge_id = db_choices[i]['edge_id']

        return response

    async def generate_canonical_comparison(self, session_history: List[dict], global_capital: int) -> EndingComparison:
        """
        Uses Gemini 2.0 (New SDK) via Instructor to compare the player's path with history.
        """
        history_text = "\n".join([f"Node: {h['node']} | Role: {h['role']} | Choice Made: {h['choice']}" for h in session_history])
        
        comparison_prompt = f"""
        ACT AS A HISTORIAN ANALYZING THE 'VICEROY REBELLION' OF 1995.
        
        SESSION HISTORY LOGS:
        {history_text}
        FINAL POLITICAL CAPITAL: {global_capital}
        
        TASK:
        Compare the events above (Player Choices) against the actual history of NTR, Chandrababu Naidu, and Lakshmi Parvathi.
        
        Return an analysis comparing the player summary vs reality.
        """
        
        return self.gemini_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": comparison_prompt}],
            response_model=EndingComparison,
        )

ai_engine = AIEngine()
