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
