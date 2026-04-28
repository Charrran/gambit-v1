# Unified Frontend Code

## .gitignore
```
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

node_modules
dist
dist-ssr
*.local

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

```

## eslint.config.js
```javascript
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
])

```

## index.html
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GAMBIT</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>

```

## package.json
```json
{
  "name": "gambit-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "framer-motion": "^12.38.0",
    "lucide-react": "^1.8.0",
    "react": "^19.2.4",
    "react-dom": "^19.2.4"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.4",
    "@tailwindcss/vite": "^4.2.2",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "eslint": "^9.39.4",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.5.2",
    "globals": "^17.4.0",
    "tailwindcss": "^4.2.2",
    "vite": "^8.0.4"
  }
}

```

## README.md
```
# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

```

## vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
})

```

## src\App.css
```css
/* App.css is intentionally left blank as Tailwind is used in index.css */

```

## src\App.jsx
```jsx
import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft } from 'lucide-react';
import { LandingScreen } from './components/screens/LandingScreen';
import { CreateSessionScreen } from './components/screens/CreateSessionScreen';
import { JoinSessionScreen } from './components/screens/JoinSessionScreen';
import { EpisodeSelectScreen } from './components/screens/EpisodeSelectScreen';
import { WaitingRoomScreen } from './components/screens/WaitingRoomScreen';
import { PrologueScreen } from './components/screens/PrologueScreen';
import { RoleRevealScreen } from './components/screens/RoleRevealScreen';
import { ROLES } from './data/roles';

function App() {
  // --- STATE ---
  const [currentScreen, setCurrentScreen] = useState('landing');
  const [history, setHistory] = useState(['landing']);
  const [session, setSession] = useState(null); // { sessionId, playerName, isHost, episodeId }
  const [players, setPlayers] = useState([]);
  const [hostName, setHostName] = useState('');
  const [readyCount, setReadyCount] = useState(0);
  const [assignedRole, setAssignedRole] = useState(null);

  // --- NAVIGATION ---
  const navigate = useCallback((screen, addToHistory = true) => {
    setCurrentScreen(screen);
    if (addToHistory) {
      setHistory(prev => [...prev, screen]);
    }
  }, []);

  const goBack = useCallback(() => {
    if (history.length > 1) {
      const newHistory = [...history];
      newHistory.pop();
      const prevScreen = newHistory[newHistory.length - 1];
      setHistory(newHistory);
      setCurrentScreen(prevScreen);
    }
  }, [history]);

  // --- ACTIONS ---
  const handleSessionStarted = (sessionData) => {
    setHostName(sessionData.playerName);
    navigate('episode-select');
  };

  const handleEpisodeConfirmed = (sessionData) => {
    setSession(sessionData);
    setPlayers([{ id: 'p1', name: sessionData.playerName, isHost: true }]);
    navigate('waiting');
    
    // Mock simulation of players joining
    setTimeout(() => {
      setPlayers(prev => [...prev, { id: 'p2', name: 'Arjun Reddy', isHost: false }]);
    }, 2000);
    setTimeout(() => {
      setPlayers(prev => [...prev, { id: 'p3', name: 'Kavitha Rao', isHost: false }]);
    }, 4500);
  };

  const handleJoined = (sessionData) => {
    setSession(sessionData);
    setPlayers([
      { id: 'p0', name: 'The Host', isHost: true },
      { id: 'p1', name: sessionData.playerName, isHost: false }
    ]);
    navigate('waiting');
  };

  const handleStartGame = () => {
    navigate('prologue');
  };

  const handlePlayerReady = () => {
    // Send WebSocket message { type: "PLAYER_READY", player_id }
    // For now, mock the increment
    setReadyCount(prev => Math.min(prev + 1, players.length));
  };

  const handleBeginCrisis = () => {
    // Send WebSocket message { type: "BEGIN_CRISIS" }
    const roleKeys = Object.keys(ROLES);
    const randomRole = roleKeys[Math.floor(Math.random() * roleKeys.length)];
    setAssignedRole(randomRole);
    navigate('role');
  };

  const handleAcceptRole = () => {
    alert('→ Proceeding to main game. UI migration complete!');
  };

  // Determine if back button should be visible
  const noBackScreens = ['landing', 'waiting', 'role'];
  const showBackButton = !noBackScreens.includes(currentScreen) && history.length > 1;

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden">
      {/* Navigation Overlay */}
      <AnimatePresence>
        {showBackButton && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={goBack}
            className="fixed top-8 left-8 z-50 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase text-text-faint hover:text-text-dim transition-colors cursor-pointer"
          >
            <ChevronLeft size={14} />
            Back
          </motion.button>
        )}
      </AnimatePresence>

      {/* Screen Content */}
      <main className="relative z-10 w-full flex flex-col items-center justify-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentScreen}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="w-full flex flex-col items-center"
          >
            {currentScreen === 'landing' && (
              <LandingScreen onNavigate={navigate} />
            )}
            
            {currentScreen === 'create' && (
              <CreateSessionScreen onSessionCreated={handleSessionStarted} />
            )}
            
            {currentScreen === 'episode-select' && (
              <EpisodeSelectScreen 
                hostName={hostName} 
                onEpisodeConfirmed={handleEpisodeConfirmed} 
              />
            )}
            
            {currentScreen === 'join' && (
              <JoinSessionScreen onJoined={handleJoined} />
            )}
            
            {currentScreen === 'waiting' && (
              <WaitingRoomScreen 
                session={session} 
                players={players} 
                onStartGame={handleStartGame} 
              />
            )}

            {currentScreen === 'prologue' && (
              <PrologueScreen
                session={session}
                players={players}
                readyCount={readyCount}
                onReady={handlePlayerReady}
                onBegin={handleBeginCrisis}
              />
            )}
            
            {currentScreen === 'role' && (
              <RoleRevealScreen 
                roleKey={assignedRole} 
                onAccept={handleAcceptRole} 
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;

```

## src\index.css
```css
@import "tailwindcss";

@theme {
  --color-black: #080705;
  --color-deep: #0f0d0a;
  --color-surface: #161310;
  --color-surface2: #1e1a15;
  --color-border-primary: #2a241c;
  --color-border-secondary: #3a3228;
  --color-gold: #c9a84c;
  --color-gold-dim: #7a6430;
  --color-gold-bright: #e8c96a;
  --color-red-primary: #8b2635;
  --color-red-dim: #5a1822;
  --color-text-primary: #e8e0d0;
  --color-text-dim: #8a8070;
  --color-text-faint: #4a4438;

  --font-serif: "Cormorant Garamond", Georgia, serif;
  --font-sans: "DM Sans", sans-serif;
  --font-mono: "DM Mono", monospace;

  --animate-fade-up: fade-up 0.8s ease forwards;
  --animate-line-reveal: line-reveal 1s ease forwards;
  --animate-pulse-soft: pulse-soft 2s ease infinite;
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes line-reveal {
  from { opacity: 0; transform: scaleX(0); }
  to { opacity: 1; transform: scaleX(1); }
}

@keyframes pulse-soft {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}



@layer base {
  html, body, #root {
    height: 100%;
    background: var(--color-black);
    color: var(--color-text-primary);
    font-family: var(--font-sans);
    overflow: hidden;
  }

  /* Film grain overlay */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E");
    opacity: 0.025;
    pointer-events: none;
    z-index: 1000;
  }

  /* Vignette */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.7) 100%);
    pointer-events: none;
    z-index: 999;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }

  /* 3D Utilities */
  .perspective-1000 {
    perspective: 1000px;
  }
  
  .preserve-3d {
    transform-style: preserve-3d;
  }
  
  .backface-hidden {
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
  }
  
  .rotate-y-180 {
    transform: rotateY(180deg);
  }

  .perspective-none {
    perspective: none;
  }
}

```

## src\main.jsx
```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

```

## src\components\screens\CreateSessionScreen.jsx
```jsx
import { useState } from 'react';
import { Panel, Input, Button } from '../ui';

export const CreateSessionScreen = ({ onSessionCreated }) => {
  const [name, setName] = useState('');
  const [status, setStatus] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) {
      setStatus({ text: 'Enter your name to continue.', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ text: 'Creating session...', type: '' });

    // Mock API Call
    setTimeout(() => {
      const sessionId = Math.random().toString(36).substring(2, 8).toUpperCase();
      onSessionCreated({ sessionId, playerName: name, isHost: true });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Panel title="New Session">
        <div>
          <p className="font-serif text-[32px] font-light text-text-primary mb-1 tracking-tight">Create a lobby</p>
          <p className="text-[13px] text-text-dim leading-relaxed">You'll receive a session code to share with up to 3 others.</p>
        </div>

        <Input
          label="Your name"
          id="create-name"
          placeholder="Enter your name"
          maxLength={24}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <p className={`font-mono text-[11px] tracking-wider text-center min-h-[16px] ${
          status.type === 'error' ? 'text-red-primary' : status.type === 'success' ? 'text-gold' : 'text-text-faint'
        }`}>
          {status.text}
        </p>

        <Button onClick={handleCreate} disabled={loading} className="self-start">
          {loading ? 'Processing...' : 'Create Session'}
        </Button>
      </Panel>
    </div>
  );
};

```

## src\components\screens\EpisodeSelectScreen.jsx
```jsx
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, CheckCircle2 } from 'lucide-react';
import { Button } from '../ui';

const EPISODES = [
  {
    id: 'EP_01_REGENT',
    title: 'Episode 1 — The Regent Rebellion',
    subtitle: 'Empire Bay Hotel · August 1995',
    description: 'A patriarch. A strategist. A woman nobody can name. A family about to fracture. Four roles. One crisis. Fifteen minutes of alternate history.',
    status: 'AVAILABLE'
  },
  { id: 'EP_02_LOCKED', status: 'LOCKED' },
  { id: 'EP_03_LOCKED', status: 'LOCKED' },
  { id: 'EP_04_LOCKED', status: 'LOCKED' }
];

export const EpisodeSelectScreen = ({ hostName, onEpisodeConfirmed }) => {
  const [selectedId, setSelectedId] = useState('EP_01_REGENT');
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    if (!selectedId) return;
    setLoading(true);

    // Mock Lobby Creation
    setTimeout(() => {
      const mockSessionCode = Math.random().toString(36).substring(2, 8).toUpperCase();
      onEpisodeConfirmed({
        sessionId: mockSessionCode,
        playerName: hostName,
        isHost: true,
        episodeId: selectedId
      });
      setLoading(false);
    }, 1200);
  };


  return (
    <div className="w-full max-w-[900px] flex flex-col items-center">
      <div className="text-center mb-12">
        <motion.p 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-mono text-xs tracking-[0.4em] text-gold uppercase mb-3"
        >
          Select Episode
        </motion.p>
        <motion.h1 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="font-serif text-2xl italic text-text-dim"
        >
          "Each episode is a different crisis. Each crisis is a different history."
        </motion.h1>
      </div>

      <div className="flex flex-col md:flex-row items-center justify-center gap-12 w-full mb-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          onClick={() => setSelectedId('EP_01_REGENT')}
          className={`
            relative w-full max-w-[440px] p-8 border transition-all duration-300 cursor-pointer
            bg-surface border-border-primary hover:border-gold-dim hover:shadow-[0_0_30px_var(--color-gold)]/5
            ${selectedId === 'EP_01_REGENT' ? 'border-l-[4px] border-l-gold border-gold-dim' : ''}
          `}
        >
          <div className="flex justify-between items-start mb-4">
            <p className="font-mono text-[10px] tracking-[0.4em] text-gold uppercase">Episode 01</p>
            <CheckCircle2 size={18} className="text-gold" />
          </div>
          <h2 className="font-serif text-2xl text-text-primary mb-2">The Regent Rebellion</h2>
          <p className="font-mono text-[10px] tracking-[0.3em] text-gold-dim uppercase mb-6">Empire Bay Hotel · August 1995</p>
          <p className="text-base text-text-dim leading-relaxed font-light mb-2 italic">
            "A patriarch. A strategist. A woman nobody can name. A family about to fracture."
          </p>
          <div className="h-[1px] w-full bg-border-primary my-6 opacity-30" />
          <p className="text-sm text-text-faint leading-relaxed tracking-wide">
            Four roles. One crisis. Fifteen minutes of alternate history.
          </p>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col items-start gap-4"
        >
          <div className="flex items-center gap-4 opacity-30">
            <div className="w-1.5 h-1.5 bg-gold rotate-45" />
            <p className="font-mono text-[11px] tracking-[0.5em] uppercase text-gold-dim">
              COMING SOON
            </p>
          </div>
          <p className="font-serif text-sm italic text-text-faint max-w-[200px] leading-relaxed">
            New crises, new roles, and deeper betrayals are being authored.
          </p>
        </motion.div>
      </div>



      <Button 
        onClick={handleConfirm} 
        disabled={!selectedId || loading}
        className="min-w-[240px]"
      >
        {loading ? 'Securing History...' : 'Confirm Episode'}
      </Button>
    </div>
  );
};

```

## src\components\screens\JoinSessionScreen.jsx
```jsx
import { useState } from 'react';
import { Panel, Input, Button } from '../ui';

export const JoinSessionScreen = ({ onJoined }) => {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleJoin = async () => {
    if (!code || code.length < 4) {
      setStatus({ text: 'Enter a valid session code.', type: 'error' });
      return;
    }
    if (!name.trim()) {
      setStatus({ text: 'Enter your name to continue.', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ text: 'Joining session...', type: '' });

    // Mock API Call
    setTimeout(() => {
      onJoined({ sessionId: code.toUpperCase(), playerName: name, isHost: false });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Panel title="Join Session">
        <div>
          <p className="font-serif text-[32px] font-light text-text-primary mb-1 tracking-tight">Enter the code</p>
          <p className="text-[13px] text-text-dim leading-relaxed">Ask the host for the session code and enter it below.</p>
        </div>

        <div className="flex flex-col gap-5">
          <Input
            label="Session code"
            id="join-code"
            placeholder="e.g. AB12CD"
            maxLength={8}
            className="uppercase tracking-[0.2em]"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />

          <Input
            label="Your name"
            id="join-name"
            placeholder="Enter your name"
            maxLength={24}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <p className={`font-mono text-[11px] tracking-wider text-center min-h-[16px] ${
          status.type === 'error' ? 'text-red-primary' : status.type === 'success' ? 'text-gold' : 'text-text-faint'
        }`}>
          {status.text}
        </p>

        <Button onClick={handleJoin} disabled={loading} className="self-start">
          {loading ? 'Processing...' : 'Join Session'}
        </Button>
      </Panel>
    </div>
  );
};

```

## src\components\screens\LandingScreen.jsx
```jsx
import { motion } from 'framer-motion';
import { Button } from '../ui';

export const LandingScreen = ({ onNavigate }) => {
  return (
    <div className="flex flex-col items-center justify-center p-6 gap-0">
      <div className="relative">

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="font-serif text-[clamp(72px,12vw,140px)] font-bold tracking-tight leading-[0.9] text-text-primary"
        >
          GAMBIT
        </motion.h1>
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute -bottom-0.5 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-gold to-transparent"
        />
      </div>

      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.8 }}
        className="font-serif text-[clamp(13px,2vw,16px)] italic text-text-dim mt-4 tracking-wide"
      >
        A multiplayer political thriller. History is fixed. Consequences are not.
      </motion.p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.8 }}
        className="w-[1px] h-12 bg-gradient-to-b from-transparent via-border-secondary to-transparent my-10"
      />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.1, duration: 0.8 }}
        className="flex gap-4"
      >
        <Button onClick={() => onNavigate('create')}>Create Session</Button>
        <Button variant="secondary" onClick={() => onNavigate('join')}>Join Session</Button>
      </motion.div>
    </div>
  );
};

```

## src\components\screens\PrologueScreen.jsx
```jsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../ui';

const PROLOGUE_TEXT = [
  "Andhra Pradesh. August 1995.",
  "The monsoon came late that year. When it finally arrived, it came all at once.",
  "Nobody remembered the weather afterward. There were larger things to remember.",
  "---",
  "Raghava Rao built this party with his hands. Thirty years, every district, every ground that was supposed to be empty and wasn't. The crowds don't come for the party — they come for him. That is his power. That is also, in the wrong hands, his vulnerability.",
  "Govardhan Naidu has been counting votes for two years. Quietly. Correctly. He knows the number, he knows the timing, and he has made his peace with what doing this requires. The institutional man is always the last person anyone suspects — until the institutions move.",
  "Saraswathi is the person nobody in this party can officially name, which means nobody can officially stop her. She arrived at the edges of his world and moved, by increments too small to challenge individually, toward its center. She is possibly the only person still telling Raghava the truth. In a room full of people managing him, that makes her the most dangerous thing in this story.",
  "Venkatadri is family. Both camps have reached him. Both camps believe they have him. He has not decided yet — and in a crisis running on momentum, one undecided man can change everything.",
  "---",
  "The hotel is full. The constitutional clock is running.",
  "The situations are fixed. What they produce — that belongs to you.",
  "Four roles. Four private objectives. One crisis that cannot be stopped, only shaped.",
  "The game remembers every choice. Every lie. Every room you walked into and what you did there.",
  "At the end, it will tell you exactly what kind of story you made."
];

// Helper to highlight names in gold
const renderParagraph = (text) => {
  if (text === "---") {
    return <hr className="w-full border-t border-border-primary opacity-30 my-8 px-10" />;
  }

  const names = ["Raghava Rao", "Govardhan Naidu", "Saraswathi", "Venkatadri"];
  let parts = [text];

  names.forEach(name => {
    const newParts = [];
    parts.forEach(part => {
      if (typeof part === 'string') {
        const split = part.split(name);
        for (let i = 0; i < split.length; i++) {
          newParts.push(split[i]);
          if (i < split.length - 1) {
            newParts.push(<span key={name + i} className="text-gold font-medium">{name}</span>);
          }
        }
      } else {
        newParts.push(part);
      }
    });
    parts = newParts;
  });

  return <p className="font-serif text-lg md:text-[19px] text-text-primary leading-relaxed text-center max-w-[680px] mx-auto mb-5">{parts}</p>;
};

export const PrologueScreen = ({ session, players, readyCount = 0, onReady, onBegin }) => {
  const isHost = session?.isHost;
  const [hasClickReady, setHasClickReady] = useState(false);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.5
      }
    }
  };


  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
  };

  const handleReady = () => {
    setHasClickReady(true);
    onReady();
  };

  return (
    <div className="fixed inset-0 bg-[#080705] z-50 flex flex-col overflow-y-auto overflow-x-hidden scrollbar-hide">
      {/* Film grain layer nested here to ensure it covers this specific screen perfectly */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-[60]" 
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E")` }} 
      />
      
      {/* Vignette */}
      <div className="fixed inset-0 pointer-events-none z-[59] bg-[radial-gradient(ellipse_at_center,transparent_40%,rgba(0,0,0,0.8)_100%)]" />

      <div className="relative z-10 w-full max-w-[800px] mx-auto px-6 py-24 flex flex-col items-center">
        <motion.div
           initial={{ opacity: 0 }}
           animate={{ opacity: 1 }}
           className="font-mono text-[10px] tracking-[0.5em] text-gold-dim uppercase mb-16"
        >
          Episode 01 · The Regent Rebellion
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center w-full"
        >
          {PROLOGUE_TEXT.map((text, i) => (
            <motion.div key={i} variants={itemVariants} className="w-full">
              {renderParagraph(text)}
            </motion.div>
          ))}
        </motion.div>

        {/* Ready Gate */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 6 }} // Approximate time for all text to stagger in
          className="mt-20 w-full flex flex-col items-center gap-8"
        >
          <div className="w-full flex flex-col items-center gap-3">
            <hr className="w-full border-t border-border-primary" />
            <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-text-faint">
              {readyCount} / {players.length || 4} players ready
            </p>
          </div>

          <div className="flex flex-col items-center gap-4">
            <Button
              variant={hasClickReady ? 'ghost' : 'primary'}
              onClick={handleReady}
              disabled={hasClickReady}
            >
              {hasClickReady ? 'Waiting for others...' : "I'm Ready"}
            </Button>

            {isHost && readyCount >= (players.length || 1) && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <Button 
                  onClick={onBegin} 
                  className="bg-gold text-black font-serif italic text-lg px-12"
                >
                  Begin the Crisis →
                </Button>
              </motion.div>
            )}

            {!isHost && hasClickReady && readyCount >= (players.length || 1) && (
              <p className="font-mono text-[10px] tracking-[0.2em] text-text-faint animate-pulse">
                Waiting for host to begin...
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

```

## src\components\screens\RoleRevealScreen.jsx
```jsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../ui';
import { ROLES } from '../../data/roles';

export const RoleRevealScreen = ({ roleKey, onAccept }) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const role = ROLES[roleKey];

  if (!role) return null;

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-[420px]">
      <div className="text-center">
        <p className="font-mono text-[9px] tracking-[0.4em] uppercase text-gold-dim mb-2">Your Role</p>
        <h2 className="font-serif text-[28px] font-light text-text-primary tracking-tight">Your fate is sealed.</h2>
      </div>

      <div 
        className="w-full aspect-[2/3] max-h-[480px] perspective-1000 cursor-pointer"
        onClick={() => setIsFlipped(true)}
      >
        <motion.div
          animate={{ rotateY: isFlipped ? 180 : 0 }}
          transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
          className="relative w-full h-full preserve-3d"
        >
          {/* Card Back */}
          <div className="absolute inset-0 backface-hidden bg-surface border border-border-primary flex flex-col items-center justify-center gap-4 overflow-hidden">
            <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[repeating-linear-gradient(45deg,transparent,transparent_20px,var(--color-gold)_20px,var(--color-gold)_21px)]" />
            <div className="font-serif text-[64px] font-bold text-border-secondary uppercase -tracking-wider">G</div>
            <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-text-faint">Tap to reveal your role</p>
          </div>

          {/* Card Front */}
          <div 
            className="absolute inset-0 backface-hidden bg-surface border border-border-secondary rotate-y-180 flex flex-col overflow-hidden before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-0.5 before:bg-gradient-to-r before:from-transparent before:via-gold before:to-transparent"
          >
            <div className="p-6 pb-5 border-b border-border-primary text-left">
              <p className="font-mono text-[9px] tracking-[0.35em] uppercase text-gold-dim mb-2">{role.tag}</p>
              <h3 className="font-serif text-[30px] font-semibold leading-tight text-text-primary">{role.name}</h3>
              <p className="font-serif italic text-sm text-text-dim mt-1">{role.analogue}</p>
            </div>
            
            <div className="p-6 flex-1 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
              {role.traits.map((trait, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <p className="font-mono text-[9px] tracking-[0.25em] uppercase text-text-faint">{trait.label}</p>
                  <p className="text-[13px] text-text-dim leading-relaxed">{trait.value}</p>
                </div>
              ))}
              
              <div className="mt-auto bg-deep border border-red-dim p-4 relative">
                <p className="font-mono text-[8px] tracking-[0.3em] text-red-primary mb-1.5 uppercase">⬛ CLASSIFIED</p>
                <p className="text-xs text-text-dim leading-relaxed italic">{role.secret}</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="text-center min-h-[40px]">
        {isFlipped ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.4 }}
            className="flex flex-col items-center gap-4"
          >
            <p className="font-mono text-[10px] tracking-widest text-text-faint uppercase animate-pulse-soft">
              Your briefing is classified. Do not share it.
            </p>
            <Button onClick={onAccept}>Accept This Role →</Button>
          </motion.div>
        ) : (
          <p className="font-mono text-[10px] tracking-widest text-text-faint uppercase animate-pulse-soft">
            Tap the card to reveal
          </p>
        )}
      </div>
    </div>
  );
};

```

## src\components\screens\WaitingRoomScreen.jsx
```jsx
import { motion } from 'framer-motion';
import { Button } from '../ui';
import { User, Copy } from 'lucide-react';

export const WaitingRoomScreen = ({ session, players, onStartGame }) => {
  const slots = Array.from({ length: 4 }, (_, i) => players[i] || null);
  const isHost = session?.isHost;
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(session.sessionId);
    // Add visual feedback if possible, but keeping it simple for now
  };

  return (
    <div className="relative w-full max-w-[680px]">
      {/* Background Atmosphere Layer */}
      <div className="absolute -inset-20 pointer-events-none overflow-hidden -z-10">
        <motion.div 
          animate={{ 
            x: [-20, 20, -20],
            y: [-10, 10, -10],
          }}
          transition={{ 
            duration: 20, 
            repeat: Infinity, 
            ease: "linear" 
          }}
          className="w-full h-full opacity-[0.03] flex items-center justify-center"
        >
           {/* Abstract architectural silhouette (Hotel outline) */}
           <svg viewBox="0 0 800 600" className="w-[120%] h-[120%] text-gold fill-current">
              <path d="M100 500 L100 200 L200 150 L300 180 L400 120 L500 180 L600 150 L700 200 L700 500 Z" />
              <rect x="150" y="250" width="40" height="60" />
              <rect x="250" y="270" width="40" height="60" />
              <rect x="350" y="230" width="40" height="60" />
              <rect x="450" y="270" width="40" height="60" />
              <rect x="550" y="250" width="40" height="60" />
           </svg>
        </motion.div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col gap-6"
      >
        <div className="flex items-end justify-between pb-5 border-b border-border-primary">
          <div>
            <p className="font-mono text-[9px] tracking-[0.35em] uppercase text-gold-dim mb-1.5">Waiting Room</p>
            <h2 className="font-serif text-[42px] font-light leading-none tracking-tight">
              The <span className="text-gold italic">Empire Bay</span><br />Hotel
            </h2>
          </div>
          
          <div 
            onClick={copyToClipboard}
            className="group bg-deep border border-border-secondary p-3 px-5 text-center cursor-pointer hover:border-gold-dim transition-all duration-300 hover:shadow-[0_0_15px_rgba(201,168,76,0.1)]"
          >
            <p className="font-mono text-[9px] tracking-[0.4em] uppercase text-text-faint mb-1 group-hover:text-gold-dim transition-colors">Session Code</p>
            <div className="flex items-center gap-2">
              <p className="font-mono text-xl font-medium tracking-widest text-gold">{session.sessionId}</p>
              <Copy size={14} className="text-text-faint group-hover:text-gold transition-colors" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {slots.map((player, i) => (
            <div 
              key={i}
              className={`
                bg-surface/60 backdrop-blur-sm border p-4 flex items-center gap-4 relative transition-all duration-300
                ${player ? 'border-border-secondary' : 'border-border-primary/40'}
                ${player?.isHost ? 'border-l-2 border-l-gold' : ''}
              `}
            >
              <div className={`
                w-10 h-10 border flex items-center justify-center shrink-0
                ${player ? 'border-gold-dim bg-gold/5' : 'border-border-secondary/50'}
              `}>
                <User size={16} className={player ? 'text-gold' : 'text-text-faint'} />
              </div>
              
              <div className="flex-1 min-w-0">
                <p className={`text-sm tracking-wide ${player ? 'text-text-primary' : 'text-text-faint italic'}`}>
                  {player ? player.name : 'Searching for signal...'}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="font-mono text-[9px] tracking-[0.2em] uppercase text-text-faint">
                    {player ? (player.isHost ? 'Session Host' : 'Operative') : 'Empty Slot'}
                  </p>
                  {player?.isHost && (
                    <span className="w-1 h-1 rounded-full bg-gold" />
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1.5">
                {player?.name === session.playerName && (
                  <span className="font-mono text-[8px] tracking-[0.2em] uppercase bg-gold text-black px-2 py-0.5 font-bold">You</span>
                )}
                {player?.isHost && (
                  <span className="font-mono text-[8px] tracking-[0.2em] uppercase border border-gold text-gold px-2 py-0.5">Host</span>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2">
          <div>
            <p className="font-mono text-[11px] text-text-faint tracking-[0.1em]">
              <span className="text-gold font-bold">{players.length}</span> / 4 slots filled
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
              <p className="font-mono text-[9px] text-text-faint tracking-[0.25em] uppercase">Awaiting connection</p>
            </div>
          </div>
          
          {isHost && (
            <div className="flex flex-col items-end gap-2">
              <Button 
                onClick={onStartGame} 
                disabled={players.length < 2}
                className="shadow-[0_0_15px_rgba(201,168,76,0.15)]"
              >
                Begin the Crisis
              </Button>
              <p className="font-mono text-[9px] text-text-faint tracking-widest uppercase">
                {players.length < 2 ? 'Min. 2 players to begin' : 'Lobby ready'}
              </p>
            </div>
          )}

          {!isHost && (
            <div className="flex flex-col items-end">
              <p className="font-mono text-xs tracking-widest text-text-faint uppercase animate-pulse">
                Waiting for host to begin...
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};


```

## src\components\ui\index.jsx
```jsx
import { motion } from 'framer-motion';

export const Button = ({ children, onClick, variant = 'primary', disabled, className = '', ...props }) => {
  const variants = {
    primary: 'bg-gold text-black hover:bg-gold-bright shadow-lg shadow-gold/20',
    secondary: 'bg-transparent text-text-primary border border-gold hover:bg-gold/5 hover:border-gold-bright shadow-sm',
    ghost: 'bg-transparent text-text-faint border border-border-primary text-[10px] px-5 py-2.5 hover:text-text-dim hover:border-border-secondary',
  };

  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      disabled={disabled}
      className={`
        font-mono text-[11px] tracking-[0.2em] uppercase px-8 py-3.5 
        transition-all duration-200 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed
        ${variants[variant]} ${className}
      `}
      {...props}
    >
      {children}
    </motion.button>
  );
};




export const Input = ({ label, id, ...props }) => (
  <div className="flex flex-col gap-2 w-full">
    {label && (
      <label htmlFor={id} className="font-mono text-[10px] tracking-[0.25em] uppercase color-text-faint">
        {label}
      </label>
    )}
    <input
      id={id}
      className="bg-deep border border-border-primary text-text-primary font-mono text-sm px-4 py-3 outline-none focus:border-gold-dim transition-colors"
      {...props}
    />
  </div>
);

export const Panel = ({ title, children, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`bg-surface border border-border-primary w-full max-w-[460px] relative before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-gold-dim before:to-transparent ${className}`}
  >
    <div className="px-7 pt-5 pb-4 border-b border-border-primary flex items-center justify-between">
      <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-gold-dim">{title}</span>
    </div>
    <div className="p-7 flex flex-col gap-5">
      {children}
    </div>
  </motion.div>
);

```

## src\data\roles.js
```javascript
export const ROLES = {
  raghava_rao: {
    name: 'Raghava Rao',
    analogue: 'Patriarch · Mass Leader',
    tag: 'Role 01',
    traits: [
      { label: 'Political identity', value: 'Mythic mass leader. Emotional legitimacy built over five decades. The party is inseparable from his image.' },
      { label: 'Strength', value: 'Crowd mandate, symbolic power, the weight of history on your side.' },
      { label: 'Vulnerability', value: 'Unstable command center. Susceptible to the influence of those closest to you.' }
    ],
    secret: 'You are not fighting for power. You are fighting to ensure your life\'s work is not reduced to a cautionary tale.'
  },
  govardhan_naidu: {
    name: 'Govardhan Naidu',
    analogue: 'Strategist · Institutional Operator',
    tag: 'Role 02',
    traits: [
      { label: 'Political identity', value: 'Institutional man. Thirty years of building, organizing, and knowing where the bodies are buried.' },
      { label: 'Strength', value: 'Legislative numbers, procedural command, elite loyalty.' },
      { label: 'Vulnerability', value: 'The coldness that makes you effective also makes you alone.' }
    ],
    secret: 'You need to believe this is necessary. The moment that justification cracks is your most dangerous moment.'
  },
  saraswathi: {
    name: 'Saraswathi',
    analogue: 'Influence Center · Queenmaker',
    tag: 'Role 03',
    traits: [
      { label: 'Political identity', value: 'The outsider who became the inside. Access and influence built through proximity and perception.' },
      { label: 'Strength', value: 'Court politics, emotional access, the only person who sees the whole board.' },
      { label: 'Vulnerability', value: 'If Raghava falls, you have nothing. Every move is also self-preservation.' }
    ],
    secret: 'Your manipulation is not ambition. It is survival with ambition layered on top. That difference matters to you, even if no one else will ever understand it.'
  },
  venkatadri: {
    name: 'Venkatadri',
    analogue: 'Family Hinge · Moral Witness',
    tag: 'Role 04',
    traits: [
      { label: 'Political identity', value: 'The person nobody needed to worry about. Present enough to matter, uncommitted enough to move.' },
      { label: 'Strength', value: 'Swing actor, mediator, the only person both camps still trust.' },
      { label: 'Vulnerability', value: 'Hesitation reads as cowardice. In a crisis, indecision is its own decision.' }
    ],
    secret: 'You are not protecting a person. You are protecting the idea that this family does not destroy itself publicly. Every choice you make violates something you are trying to protect.'
  }
};

```

