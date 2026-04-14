# ♟️ Gambit: The Regent Rebellion Engine

Gambit is an episodic, deterministic multiplayer narrative strategy engine. It uses Neo4j for its path-based narrative graph, Redis (Memory Bank) for session state, and Groq (AI Director) for cinematic storytelling.

---

## 🚀 Quick Start

### 1. Environment Setup
Create a `.env` file in the root directory with the following credentials:

```env
# Infrastructure
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
REDIS_URL=redis://your-upstash-url

# AI Director
GROQ_API_KEY=gsk_your_key
GEMINI_API_KEY=your_gemini_key
```

### 2. Install Dependencies
```bash
python -m venv venv
./venv/Scripts/activate  # Windows
pip install -r requirements.txt
pip install groq         # If not in requirements
```

### 3. Seed the Narrative Graph
Before playing, populate the Neo4j database with "Episode 1: The Regent Rebellion":
```bash
python seed_db.py
```

---

## 🛠️ Testing the Game Loop

### Step 1: Start the Engine
```bash
uvicorn app.main:app --reload
```

### Step 2: Create a Lobby
Use `curl` or Postman to create a game session:
```bash
curl -X POST http://localhost:8000/lobby/create
```
**Response**: Note the `session_id` (e.g., `8866ba4c`).

### Step 3: Join Players
Join 2 to 4 players to the lobby:
```bash
curl -X POST http://localhost:8000/lobby/8866ba4c/join \
     -H "Content-Type: application/json" \
     -d '{"player_id": "player_1"}'
```

### Step 4: Start the Game
Assign roles and activate the session:
```bash
curl -X POST http://localhost:8000/lobby/8866ba4c/start
```

### Step 5: Connect to the WebSocket Loop
Connect players to the live game loop. You can use a tool like [wscat](https://github.com/nmoinvaz/wscat) or a browser-based WebSocket tester.

**Endpoint**: `ws://localhost:8000/ws/play/8866ba4c/player_1`

#### WebSocket Protocol:
1.  **Signal Readiness**: Optional. You may send `{"type": "READY"}` after connecting.
2.  **Receive Narrative**: Each client receives a `NARRATIVE_BEAT` whenever the scene changes.
3.  **The Spotlight**: If it is your role's turn, you will receive a `SPOTLIGHT_CHOICE` message containing interactive options.
4.  **Make a Decision**: Send the `choice_id` you received in the scene payload:
    ```json
    {
      "type": "DECISION",
      "choice_id": "regent_02_open_to_press"
    }
    ```

---

## ⚖️ Mechanics Reminder
- **The Memory Bank**: Decisions append `alignments` and `flags` to your profile in Redis.
- **Spotlight Turn**: Only the player with the `required_role` can see and send decisions.
- **Guided Determinism**: Major incidents follow an authored historical order, while the player-facing choices, flavor, and final route respond to session state in real-time.

> [!TIP]
> Use the **Neo4j Console** to visualize the `EpisodeNode` and `LEADS_TO` graph while playing to see the story paths in action!
