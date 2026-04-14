import asyncio
import os
import sys

# Ensure local imports work
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from app.services.ai_engine import ai_engine

async def verify_ai_director():
    """
    Verifies that the AI Director correctly generates structured narrative turns.
    Requires a valid GROQ_API_KEY in the .env.
    """
    print("--- GAMBIT AI DIRECTOR VERIFICATION ---")
    
    # Mock data for Node 1
    premise = (
        "Chief Minister Raghava Rao has released a new cabinet list. "
        "Govardhan Naidu's loyalists have been purged, replaced by Saraswathi's allies. "
        "The party is fracturing in the shadows."
    )
    role = "Raghava Rao"
    choices = [
        {
            "target_node_id": "regent_02_hotel_lockdown", 
            "action_intent": "Isolate the dissenting ministers and refuse to meet them."
        }
    ]

    print(f"[*] Requesting narrative generation for Spotlight Role: {role}...")
    
    try:
        # Generate the turn
        narrative = await ai_engine.generate_spotlight_turn(premise, role, choices)
        
        print("\n[+] AI GENERATED NARRATIVE:")
        print(f"--------------------------------------------------")
        print(narrative.flavor_text)
        print(f"--------------------------------------------------")
        
        print("\n[+] GENERATED OPTIONS (MCQs):")
        for opt in narrative.options:
            print(f"    - ID: {opt.edge_id}")
            print(f"      Text: {opt.text}")
            
        # Validation checks
        if len(narrative.options) > 0 and narrative.options[0].edge_id == "regent_02_hotel_lockdown":
            print("\n[++] VERIFICATION SUCCESS: AI correctly synchronized graph IDs with narrative text.")
        else:
            print("\n[!] VERIFICATION FAILED: Option ID mismatch.")

    except Exception as e:
        print(f"\n[!] AI DIRECTOR ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_ai_director())
