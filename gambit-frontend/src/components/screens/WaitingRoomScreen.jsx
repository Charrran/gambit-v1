import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '../ui';
import { User, Copy, Check } from 'lucide-react';

import { API_BASE_URL } from '../../config';

/**
 * WaitingRoomScreen
 * Props:
 *   session     – { sessionId, playerName, isHost }
 *   gameState   – live WebSocket gameState (for LOBBY_UPDATE messages)
 *   onStartGame – called when host clicks Begin
 */
export const WaitingRoomScreen = ({ session, gameState, onStartGame }) => {
  const [players, setPlayers] = useState([]);
  const [copied, setCopied] = useState(false);
  const isHost = session?.isHost;

  // --- Poll backend every 2 seconds to get live player list ---
  useEffect(() => {
    if (!session?.sessionId) return;

    const fetchPlayers = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/lobby/${session.sessionId}/state`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.active_players) {
          const list = Object.values(data.active_players).map((p) => ({
            id: p.player_id,
            name: p.player_id,
            isHost: false, // We don't have a host flag in backend, determine by name match
          }));
          setPlayers(list);
        }
      } catch (_) {
        // silent fail — backend may not be ready yet
      }
    };

    fetchPlayers(); // immediate first fetch
    const interval = setInterval(fetchPlayers, 2000);
    return () => clearInterval(interval);
  }, [session?.sessionId]);

  // --- Also react to WebSocket LOBBY_UPDATE broadcasts ---
  useEffect(() => {
    if (gameState?.type === 'LOBBY_UPDATE' && gameState.active_players) {
      const list = Object.values(gameState.active_players).map((p) => ({
        id: p.player_id,
        name: p.player_id,
        isHost: false,
      }));
      setPlayers(list);
    }
  }, [gameState]);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(session?.sessionId || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const slots = Array.from({ length: 4 }, (_, i) => players[i] || null);

  return (
    <div className="relative w-full max-w-[680px]">
      {/* Background Atmosphere Layer */}
      <div className="absolute -inset-20 pointer-events-none overflow-hidden -z-10">
        <motion.div
          animate={{ x: [-20, 20, -20], y: [-10, 10, -10] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="w-full h-full opacity-[0.03] flex items-center justify-center"
        >
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
        {/* Header */}
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
              <p className="font-mono text-xl font-medium tracking-widest text-gold">{session?.sessionId}</p>
              {copied
                ? <Check size={14} className="text-gold" />
                : <Copy size={14} className="text-text-faint group-hover:text-gold transition-colors" />
              }
            </div>
          </div>
        </div>

        {/* Player slots */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {slots.map((player, i) => (
            <div
              key={i}
              className={`
                bg-surface/60 backdrop-blur-sm border p-4 flex items-center gap-4 relative transition-all duration-300
                ${player ? 'border-border-secondary' : 'border-border-primary/40'}
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
                    {player ? 'Operative' : 'Empty Slot'}
                  </p>
                  {player?.name === session?.playerName && (
                    <span className="font-mono text-[8px] tracking-[0.2em] uppercase bg-gold text-black px-2 py-0.5 font-bold">You</span>
                  )}
                </div>
              </div>

              {/* Connected indicator */}
              {player && (
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-1.5 h-1.5 rounded-full bg-gold shrink-0"
                />
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <p className="font-mono text-[11px] text-text-faint tracking-[0.1em]">
              <span className="text-gold font-bold">{players.length}</span> / 4 players connected
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
              <p className="font-mono text-[9px] text-text-faint tracking-[0.25em] uppercase">Polling for connections</p>
            </div>
          </div>

          {isHost && (
            <div className="flex flex-col items-end gap-2">
              <Button
                onClick={onStartGame}
                disabled={players.length < 4}
                className="shadow-[0_0_15px_rgba(201,168,76,0.15)]"
              >
                Begin the Crisis
              </Button>
              <p className="font-mono text-[9px] text-text-faint tracking-widest uppercase">
                {players.length < 4
                  ? `${4 - players.length} more player${4 - players.length !== 1 ? 's' : ''} needed`
                  : 'All operatives present'}
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
