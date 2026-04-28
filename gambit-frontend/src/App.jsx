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
import { GameScreen } from './components/screens/GameScreen';
import { ROLES } from './data/roles';
import { useGameRoom } from './hooks/useGameRoom';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // --- STATE ---
  const [currentScreen, setCurrentScreen] = useState('landing');
  const [history, setHistory] = useState(['landing']);

  // session = { sessionId, playerName, isHost }
  // hostSessionId = sessionId returned by /lobby/create before episode select
  const [session, setSession] = useState(null);
  const [hostSessionId, setHostSessionId] = useState(null);
  const [hostName, setHostName] = useState('');

  const [assignedRole, setAssignedRole] = useState(null);

  // --- GAME SERVICE ---
  // Only create the WS connection once we have a real session (post episode-select)
  const gameRoom = useGameRoom(session?.sessionId, session?.playerName);
  const { gameState, connect, sendChoice, sendMessage } = gameRoom;

  // Derived state from gameState
  const activePlayers = Object.values(gameState?.active_players || {});
  const readyPlayersCount = activePlayers.filter(p => p.flags?.includes('ready')).length;



  useEffect(() => {
    if (session?.sessionId && session?.playerName) {
      connect();
    }
  }, [session, connect]);

  // Global role assignment sync
  useEffect(() => {
    const myProfile = gameState?.active_players?.[session?.playerName];
    if (myProfile?.role) {
      const roleKey = normalizeRoleKey(myProfile.role);
      if (assignedRole !== roleKey) {
        console.log("Syncing role:", roleKey);
        setAssignedRole(roleKey);
      }
    }
  }, [gameState, session, assignedRole]);


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

  useEffect(() => {
    if (gameState?.type === 'NARRATIVE_BEAT' && currentScreen === 'waiting') {
      console.log("Game started! Navigating to prologue.");
      navigate('prologue');
    }
  }, [gameState, currentScreen, navigate]); 

  // Transition from Prologue to Role Reveal (Synchronized)
  useEffect(() => {
    if (gameState?.story_flags?.includes('role_reveal_started') && currentScreen === 'prologue') {
      console.log("Role reveal started! Navigating to role screen.");
      navigate('role');
    }
  }, [gameState, currentScreen, navigate]);



  // --- ACTIONS ---

  // Step 1: Host creates session → backend returns real session_id
  const handleSessionCreated = (data) => {
    // data = { sessionId, playerName, isHost: true }
    setHostSessionId(data.sessionId);
    setHostName(data.playerName);
    navigate('episode-select');
  };

  // Step 2: Host confirms episode → set session state (triggers WS connect)
  const handleEpisodeConfirmed = (sessionData) => {
    // sessionData = { sessionId (real), playerName, isHost, episodeId }
    setSession(sessionData);
    navigate('waiting');
  };

  // Step 3: Guest joins → backend call already done in JoinSessionScreen
  const handleJoined = (sessionData) => {
    // sessionData = { sessionId, playerName, isHost: false }
    setSession(sessionData);
    navigate('waiting');
  };

  // Step 4: Host clicks Begin
  const handleStartGame = async () => {
    if (!session?.sessionId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/lobby/${session.sessionId}/start`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json();
        console.error('Start game failed:', err.detail);
        if (err.detail?.includes('4')) {
          alert(`The backend requires all 4 players before starting. Currently: ${err.detail}`);
          return;
        }
      }
      // Backend will push a NARRATIVE_BEAT via WebSocket when ready
      // The useEffect above will navigate to 'role'
    } catch (e) {
      console.error('Could not reach backend:', e);
    }
  };

  const handlePlayerReady = () => {
    sendMessage({ type: 'READY' });
  };


  const handleBeginCrisis = () => {
    sendMessage({ type: 'START_ROLE_REVEAL' });
  };


  const handleAcceptRole = () => {
    navigate('game');
  };


  // --- HELPERS ---
  // Convert backend role names like "Raghava Rao" → "raghava_rao"
  function normalizeRoleKey(roleName) {
    if (!roleName) return 'saraswathi';
    return roleName.toLowerCase().replace(/\s+/g, '_');
  }

  // Determine if back button should be visible
  const noBackScreens = ['landing', 'waiting', 'role', 'game'];
  const showBackButton = !noBackScreens.includes(currentScreen) && history.length > 1;

  return (
    <div className={`relative w-full h-full overflow-hidden ${
      currentScreen === 'game' ? '' : 'flex flex-col items-center justify-center'
    }`}>
      {/* Back Button */}
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
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full flex flex-col items-center"
          >
            {currentScreen === 'landing' && (
              <LandingScreen onNavigate={navigate} />
            )}

            {currentScreen === 'create' && (
              <CreateSessionScreen onSessionCreated={handleSessionCreated} />
            )}

            {/* Episode Select receives the REAL sessionId from backend */}
            {currentScreen === 'episode-select' && (
              <EpisodeSelectScreen
                hostName={hostName}
                sessionId={hostSessionId}
                onEpisodeConfirmed={handleEpisodeConfirmed}
              />
            )}

            {currentScreen === 'join' && (
              <JoinSessionScreen onJoined={handleJoined} />
            )}

            {/* WaitingRoom polls + listens to WS for live player list */}
            {currentScreen === 'waiting' && (
              <WaitingRoomScreen
                session={session}
                gameState={gameState}
                onStartGame={handleStartGame}
              />
            )}

            {currentScreen === 'prologue' && (
              <PrologueScreen
                session={session}
                players={activePlayers}
                readyCount={readyPlayersCount}
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

            {currentScreen === 'game' && (
              <GameScreen
                roleKey={assignedRole ?? 'saraswathi'}
                gameRoom={gameRoom}
                session={session}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
