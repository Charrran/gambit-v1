Listed directory Gambit
Viewed README.md:1-94
Viewed requirements.txt:1-11
Listed directory app
Viewed package.json:1-32
Viewed unified_frontend.md:1-800

## GAMBIT: THE REGENT REBELLION

**Gambit** is a premium, AI-driven multiplayer narrative strategy engine designed for high-stakes political thrillers and alternate history simulations. It blends author-driven deterministic plotlines with real-time AI orchestration to create a "guided-dynamic" storytelling experience.

---

## Core Architecture

Gambit operates on a three-tier narrative architecture:

1.  **The Narrative Graph (Neo4j)**: A persistent graph database containing "Episode Nodes" and "Leads-To" relationships. It acts as the "Fixed History" of the world.
2.  **The AI Director (Groq/Gemini)**: An LLM-based layer that interprets the current narrative state, injects cinematic flavor, and generates context-aware choices for players.
3.  **The Memory Bank (Redis)**: A lightning-fast session manager that tracks player alignments, flags, and hidden variables, ensuring every decision has ripples across the episode.

---

## Technology Stack

### Backend (The Engine)
*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous Python)
*   **Database**: [Neo4j](https://neo4j.com/) (Path-based storytelling)
*   **State Management**: [Redis](https://redis.io/) (Session persistence & flag tracking)
*   **AI Orchestration**: [Groq](https://groq.com/) & [Google Gemini](https://ai.google.dev/) (via [Instructor](https://github.com/jxnl/instructor) for structured output)
*   **Communication**: WebSockets (Real-time narrative delivery)

### Frontend (The Interface)
*   **Framework**: React 19 + Vite
*   **Styling**: Tailwind CSS 4.0
*   **Animations**: Framer Motion (Cinematic transitions & film grain overlays)
*   **Icons**: Lucide React

---

## 🚀 Getting Started

### 1. Infrastructure Setup
You will need active instances of **Neo4j** and **Redis**. Create a `.env` file in the root:

```env
# Narrative Graph
NEO4J_URI=neo4j+s://your-id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Session State
REDIS_URL=redis://your-upstash-url

# Intelligence
GROQ_API_KEY=gsk_your_key
GEMINI_API_KEY=your_gemini_key
```

### 2. Backend Installation
```bash
# Install dependencies
python -m venv venv
source venv/bin/activate  # Or .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# Seed the narrative graph (Episode 1: The Regent Rebellion)
python seed_db.py

# Start the engine
uvicorn app.main:app --reload
```

### 3. Frontend Installation
```bash
cd gambit-frontend
npm install
npm run dev
```

---

## The Game Loop

1.  **The Lobby**: Up to 4 players join a session. The host selects an episode.
2.  **Role Reveal**: Players are assigned secret roles (e.g., *The Strategist*, *The Undecided*, *The Patriarch*).
3.  **The Prologue**: A cinematic setup establishes the crisis context.
4.  **The WebSocket Loop**:
    *   **NARRATIVE_BEAT**: All players receive the latest scene description and visual cues.
    *   **SPOTLIGHT_CHOICE**: The engine targets a specific role for a decision. Only that player sees the available choices.
    *   **DECISION**: The player's choice is sent back to the engine, processed by the AI Director, and committed to the Memory Bank.
5.  **The Climax**: The narrative graph terminates based on the accumulated flags in Redis, delivering a unique historical outcome.

---
