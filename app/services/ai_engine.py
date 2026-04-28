import asyncio
import json
from typing import Any, Dict, List

import instructor
from google import genai
from groq import AsyncGroq
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.schemas import NewsHeadline

class GeneratedOption(BaseModel):
    choice_id: str = Field(..., description="The unique ID of the specific narrative choice.")
    text: str = Field(..., description="The dynamically generated, flavorful choice text.")
    subtext: str = Field(default="", description="Short note about what this reveals.")

class TurnNarrative(BaseModel):
    flavor_text: str = Field(..., description="A tense, 2-paragraph narrative description of the situation.")
    options: List[GeneratedOption] = Field(..., description="A list of MCQ options for the player.")

class AnchoredTurn(BaseModel):
    scene_framing: str = Field(..., description="Short cinematic scene framing.")
    choices: List[GeneratedOption] = Field(..., description="Exactly mapped player-facing choices.")

class EndingComparison(BaseModel):
    player_summary: str = Field(..., description="A summary of the player's unique story path.")
    canonical_summary: str = Field(..., description="A summary of what happened historically in 1995.")
    divergence_analysis: str = Field(..., description="An analysis of how the player's choices changed the course of history.")
    final_score: str = Field(..., description="A creative title for the ending based on the player's performance.")



class NewsDispatch(BaseModel):
    headlines: List[NewsHeadline] = Field(..., description="Exactly three in-world headlines.")

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
        self.raw_gemini_client = genai.Client(api_key=settings.gemini_api_key)
        self.gemini_client = instructor.from_genai(self.raw_gemini_client)

    async def generate_spotlight_turn(
        self,
        premise: str,
        required_role: str,
        db_choices: list,
        player_alignments: List[str] = None,
        anchor: Dict[str, str] | None = None,
        state_snapshot: Dict[str, Any] | None = None,
        compressed_history: List[dict] | None = None,
        pressure_tags: List[str] | None = None,
        transition_summary: str | None = None,
    ) -> TurnNarrative:
        """
        Generates a tailored narrative turn using Groq.
        Incorporate player traits, pressure tags, and transition context for state-reactive framing.
        LLMs only control narrative words — effects and mechanics are always authored.
        """
        traits_context = f"This player has developed the following traits: {', '.join(player_alignments)}." if player_alignments else "This player is currently a blank slate."
        
        choices_context = ""
        choice_lookup: Dict[str, str] = {}
        for i, choice in enumerate(db_choices):
            choice_id = choice["choice_id"]
            action_intent = choice["action_intent"]
            choice_lookup[choice_id] = action_intent
            choices_context += (
                f"- Option {i+1} | Choice ID: '{choice_id}' | Narrative Directive: {action_intent}\n"
            )

        anchor = anchor or {}
        pressure_line = ""
        if pressure_tags:
            pressure_line = f"\nActive pressure: {', '.join(pressure_tags)}. Use this to colour the framing and choice wording. Do NOT invent new mechanics from it."
        transition_line = ""
        if transition_summary:
            transition_line = f"\nContext from preceding events: {transition_summary}"

        system_prompt = self._groq_system_prompt()
        user_prompt = f"""
Chapter anchor:
Register: {anchor.get("register", "Cinematic political thriller.")}
Power map: {anchor.get("power_map", "Power is contested.")}
Undercurrent: {anchor.get("undercurrent", "Nobody is saying the whole truth.")}
Constraint: {anchor.get("constraint", "Keep choices specific and consequential.")}
{pressure_line}{transition_line}

Spotlight role: {required_role}
Character context: {traits_context}
Situation: {premise}

Authored choice intents. Preserve these exact IDs and dramatize the intent only:
{choices_context}

Important display rule:
Do not copy the authored directive wording into the player-facing text.
Rewrite each option as a fresh, character-specific tactical line that implies the same intent.

State snapshot: {json.dumps(state_snapshot or {}, ensure_ascii=True)}
Previous decisions: {json.dumps((compressed_history or [])[-6:], ensure_ascii=True)}

Return this exact JSON structure:
{{
  "scene_framing": "2-3 sentence scene setup, maximum 60 words",
  "choices": [
    {{"choice_id": "exact provided id", "text": "choice text, maximum 25 words", "subtext": "what this reveals, maximum 20 words"}}
  ]
}}
Return one choice object for every provided Choice ID and no extra choices.
"""

        try:
            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=AnchoredTurn,
                max_retries=2,
            )
            return self._reconcile_options(
                TurnNarrative(flavor_text=response.scene_framing, options=response.choices),
                db_choices,
                premise,
                required_role,
            )
        except Exception as exc:
            print(f"[WARN] Spotlight AI generation failed for {required_role}: {exc}")
            return self._build_fallback_turn(premise, required_role, db_choices)

    async def generate_poll_turn(
        self,
        premise: str,
        db_choices: list,
        anchor: Dict[str, str] | None = None,
        state_snapshot: Dict[str, Any] | None = None,
        lane_weights: Dict[str, int] | None = None,
        pressure_tags: List[str] | None = None,
        transition_summary: str | None = None,
    ) -> TurnNarrative:
        choices_context = ""
        for i, choice in enumerate(db_choices):
            choices_context += (
                f"- Option {i+1} | Choice ID: '{choice['choice_id']}' | Strategic posture: {choice['action_intent']}\n"
            )

        anchor = anchor or {}
        pressure_line = ""
        if pressure_tags:
            pressure_line = f"\nActive pressure: {', '.join(pressure_tags)}. Use this to colour poll framing and option wording only. Do NOT invent new mechanics."
        transition_line = ""
        if transition_summary:
            transition_line = f"\nContext from preceding events: {transition_summary}"

        # Derive leading lane for framing hint
        leading_lanes = sorted((lane_weights or {}).items(), key=lambda kv: kv[1], reverse=True)
        lane_hint = f"Leading lane: {leading_lanes[0][0].replace('_', ' ')}" if leading_lanes and leading_lanes[0][1] > 0 else ""

        user_prompt = f"""
Chapter poll. Faction decision.

Register: {anchor.get("register", "Controlled political urgency.")}
Power map: {anchor.get("power_map", "The faction must commit.")}
Undercurrent: {anchor.get("undercurrent", "The room knows more than it says.")}
Constraint: {anchor.get("constraint", "No filler options.")}
{pressure_line}{transition_line}
{lane_hint}

Poll situation: {premise}

Authored poll options. Preserve these exact IDs and dramatize the intent only:
{choices_context}

Important display rule:
Do not copy the authored posture wording into the player-facing text.
Rewrite each option as a fresh public resolution or political posture that implies the same intent.

Current state: {json.dumps(state_snapshot or {}, ensure_ascii=True)}
Lane weights: {json.dumps(lane_weights or {}, ensure_ascii=True)}

Return this exact JSON structure:
{{
  "scene_framing": "2-3 sentence faction setup, maximum 60 words",
  "choices": [
    {{"choice_id": "exact provided id", "text": "choice text, maximum 25 words", "subtext": "downstream meaning, maximum 20 words"}}
  ]
}}
Return one choice object for every provided Choice ID and no extra choices.
"""
        try:
            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": self._groq_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=AnchoredTurn,
                max_retries=2,
            )
            return self._reconcile_options(
                TurnNarrative(flavor_text=response.scene_framing, options=response.choices),
                db_choices,
                premise,
                "COUNCIL",
            )
        except Exception as exc:
            print(f"[WARN] Poll AI generation failed: {exc}")
            return self._build_fallback_turn(premise, "COUNCIL", db_choices)

    async def generate_canonical_comparison(
        self,
        session_history: List[dict],
        global_capital: int,
        resolved_lane: str = "",
        final_state_snapshot: Dict[str, Any] | None = None,
    ) -> EndingComparison:
        """
        Uses Gemini 2.0 (New SDK) via Instructor to compare the player's path with history.
        """
        history_text = "\n".join([f"Node: {h['node']} | Role: {h['role']} | Choice Made: {h['choice']}" for h in session_history])
        
        comparison_prompt = f"""
ACT AS A HISTORIAN ANALYZING THE EMPIRE BAY HOTEL CRISIS OF 1995 AS REPRESENTED IN GAMBIT.

Important naming rule:
Use ONLY the fictional in-game names: Raghava Rao, Govardhan Naidu, Saraswathi, and Venkatadri.
Do not use real-life names. Do not mention that names have been changed.

SESSION HISTORY LOGS:
{history_text}

FINAL POLITICAL CAPITAL: {global_capital}
RESOLVED ALTERNATE-HISTORY LANE: {resolved_lane}
FINAL STATE SNAPSHOT: {json.dumps(final_state_snapshot or {}, ensure_ascii=True)}

CANONICAL BASELINE:
In the canonical course, Govardhan Naidu consolidates the hotel camp, proves majority through procedure, and takes power. Raghava Rao's emotional legitimacy survives as a wound rather than as authority. Saraswathi remains central to the meaning of the crisis but does not openly inherit the state. Venkatadri and the family become part of the moral cost of the transfer.

TASK:
Compare the player's resolved alternate-history outcome against that canonical baseline.

Return:
- player_summary: what happened in this run
- canonical_summary: what the canonical baseline would have looked like, using only fictional names
- divergence_analysis: the specific political and emotional divergence
- final_score: a short ending title
"""
        
        try:
            return await asyncio.to_thread(
                self.gemini_client.chat.completions.create,
                model="gemini-2.0-flash",
                messages=[{"role": "user", "content": comparison_prompt}],
                response_model=EndingComparison,
            )
        except Exception:
            try:
                return await self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a political historian comparing an alternate-history playthrough to the canonical Gambit baseline. Use only fictional in-game names.",
                        },
                        {"role": "user", "content": comparison_prompt},
                    ],
                    response_model=EndingComparison,
                    max_retries=1,
                )
            except Exception:
                return EndingComparison(
                    player_summary=f"The run resolved into {resolved_lane.replace('_', ' ')}.",
                    canonical_summary="In the canonical baseline, Govardhan Naidu consolidates the hotel camp, proves majority through procedure, and takes power while Raghava Rao's symbolic authority survives as a wound.",
                    divergence_analysis="This run diverged in how legitimacy, family fracture, and institutional control were distributed before the final transfer of authority.",
                    final_score=resolved_lane.replace("_", " ").title() or "Altered Verdict",
                )

    async def generate_historian_ending(
        self,
        resolved_lane: str,
        final_state_snapshot: Dict[str, Any],
        all_flags: List[str],
        pivotal_decisions: List[dict],
    ) -> str:
        prompt = f"""
You are a historian writing thirty years after the Empire Bay Hotel crisis of 1995. The events you describe are real history: alternate history, treated with full seriousness and specificity.

Ending lane: {resolved_lane}
Key state values at conclusion: {json.dumps(final_state_snapshot, ensure_ascii=True)}
Relationship flags set: {json.dumps(all_flags, ensure_ascii=True)}
Critical choices that shaped this outcome: {json.dumps(pivotal_decisions[-8:], ensure_ascii=True)}

Write a historical summary of 4-6 sentences.

Tone: measured, slightly melancholy, specific. This is not a game recap. This is a historian describing something that happened to real people and changed a real place.

Name the specific divergence from what might have been. Describe the human cost alongside the political result. End on something that could not have been predicted from the beginning.

Do not use game language. Do not reference choices or players. Write as if this happened.
Banned phrases: "in the end", "ultimately", "would go on to", "the rest is history", "legacy of".
Return plain text only. No JSON. No preamble.
"""
        try:
            response = await asyncio.to_thread(
                self.raw_gemini_client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
            )
            if getattr(response, "text", None):
                return str(response.text)
        except Exception:
            pass

        return (
            f"The {resolved_lane.replace('_', ' ')} was remembered less as a clean verdict than as a settlement forced by exhaustion. "
            "What diverged from the expected course was not simply who held authority, but which relationships survived the transfer of it. "
            "The political result hardened quickly; the human cost remained harder to name. "
            "Only later did observers understand that the crisis had changed the grammar of power inside the party itself."
        )

    async def generate_news_headlines(
        self,
        current_node: str,
        chapter_title: str,
        in_world_date: str,
        state_axes: Dict[str, Any],
        lane_weights: Dict[str, int],
        story_flags: List[str],
        recent_history: List[dict],
    ) -> List[Dict[str, str]]:
        prompt = f"""
You are the editor of fictional newspapers covering the Empire Bay Hotel crisis as it unfolds.

Use ONLY fictional in-game names: Raghava Rao, Govardhan Naidu, Saraswathi, Venkatadri.
Do not mention game mechanics, players, AI, choices, or real-life names.

Current node: {current_node}
Chapter: {chapter_title}
Required in-world date: {in_world_date}
State axes: {json.dumps(state_axes or {}, ensure_ascii=True)}
Lane pressure: {json.dumps(lane_weights or {}, ensure_ascii=True)}
Story flags: {json.dumps(story_flags or [], ensure_ascii=True)}
Recent private decisions: {json.dumps(recent_history or [], ensure_ascii=True)}

Return exactly three in-world news items. Each body must be one short sentence.
Make them react to the current political direction without revealing private facts the press could not know.
Use the required in-world date only. Do not use today's date or any modern year.
"""
        try:
            dispatch = await asyncio.to_thread(
                self.gemini_client.chat.completions.create,
                model="gemini-2.0-flash",
                messages=[{"role": "user", "content": prompt}],
                response_model=NewsDispatch,
            )
            return dispatch.headlines[:3]
        except Exception:
            dispatch = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Return only valid JSON for fictional political news headlines."},
                    {"role": "user", "content": prompt},
                ],
                response_model=NewsDispatch,
                max_retries=1,
            )
            return dispatch.headlines[:3]

    async def generate_breakdown_aftermath(
        self,
        character_name: str,
        breakdown_option_text: str,
        relevant_state_flags: Dict[str, Any],
        scene_participants: Dict[str, str],
        relationship_flags: List[str],
    ) -> str:
        prompt = f"""
You are writing a moment in a political thriller set during the 1995 Empire Bay Hotel crisis in Andhra Pradesh.

A character has just said something they cannot take back. Write what happens in the room in the 30 seconds after that.

Character: {character_name}
What they said: {breakdown_option_text}
Their emotional state: {json.dumps(relevant_state_flags, ensure_ascii=True)}
Who else is in the room: {json.dumps(scene_participants, ensure_ascii=True)}
What this moment costs them: {json.dumps(relationship_flags, ensure_ascii=True)}

Write 4-6 sentences of prose. No dialogue. Pure interiority and physical detail.

Do not summarize what just happened. Start from the moment after.
Do not use the words: tension, silence, heavy, palpable, weight.
Write as a novelist, not a narrator.
"""
        try:
            response = await asyncio.to_thread(
                self.raw_gemini_client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
            )
            if getattr(response, "text", None):
                return str(response.text)
        except Exception:
            pass
        return "For a few seconds the room seems to rearrange itself around what was said. No one moves quickly. The cost is already visible, not in speeches, but in where each person chooses to look next."

    def _reconcile_options(
        self,
        response: TurnNarrative,
        db_choices: list,
        premise: str,
        required_role: str,
    ) -> TurnNarrative:
        choice_lookup = {choice["choice_id"]: choice for choice in db_choices}
        reconciled: List[GeneratedOption] = []

        for option in response.options:
            if option.choice_id in choice_lookup:
                reconciled.append(option)

        used_ids = {option.choice_id for option in reconciled}
        for choice in db_choices:
            if choice["choice_id"] not in used_ids:
                print(f"[WARN] AI omitted choice_id {choice['choice_id']}; using authored fallback text.")
                reconciled.append(
                    GeneratedOption(
                        choice_id=choice["choice_id"],
                        text=choice["action_intent"],
                        subtext=choice.get("subtext") or "",
                    )
                )

        response.options = reconciled[: len(db_choices)]
        if not response.flavor_text.strip():
            response.flavor_text = (
                f"{required_role} faces a pivotal moment. {premise}"
            )
        return response

    def _build_fallback_turn(self, premise: str, required_role: str, db_choices: list) -> TurnNarrative:
        return TurnNarrative(
            flavor_text=(
                f"{required_role} stands at the center of the crisis. {premise} "
                "The room is tense, and every choice will shape how history remembers this moment."
            ),
            options=[
                GeneratedOption(choice_id=choice["choice_id"], text=choice["action_intent"])
                for choice in db_choices
            ],
        )

    def _groq_system_prompt(self) -> str:
        return (
            "You are a cinematic political thriller narrator for a game set in 1990s Telugu politics. "
            "Return ONLY valid JSON. No markdown fences. No preamble. No commentary. "
            'If you cannot generate valid JSON, return {"error": "generation_failed"}.'
        )

ai_engine = AIEngine()
