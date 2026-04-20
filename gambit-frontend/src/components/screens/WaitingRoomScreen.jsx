import { motion } from 'framer-motion';
import { Button } from '../ui';
import { User, Copy } from 'lucide-react';

export const WaitingRoomScreen = ({ session, players, onStartGame }) => {
  const slots = Array.from({ length: 4 }, (_, i) => players[i] || null);
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(session.sessionId);
    // You could add a toast here
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full max-w-[680px] flex flex-col gap-6"
    >
      <div className="flex items-end justify-between pb-5 border-b border-border-primary">
        <div>
          <p className="font-mono text-[9px] tracking-[0.35em] uppercase text-gold-dim mb-1.5">Waiting Room</p>
          <h2 className="font-serif text-[42px] font-light leading-none tracking-tight">
            The <span className="text-gold italic">Viceroy</span><br />Hotel
          </h2>
        </div>
        <div 
          onClick={copyToClipboard}
          className="bg-deep border border-border-secondary p-3 px-5 text-center cursor-pointer hover:border-gold-dim transition-colors"
        >
          <p className="font-mono text-[9px] tracking-[0.4em] uppercase text-text-faint mb-1">Session Code</p>
          <div className="flex items-center gap-2">
            <p className="font-mono text-xl font-medium tracking-widest text-gold">{session.sessionId}</p>
            <Copy size={12} className="text-text-faint" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {slots.map((player, i) => (
          <div 
            key={i}
            className={`
              bg-surface border p-4 flex items-center gap-3 relative transition-all duration-300
              ${player ? 'border-border-secondary' : 'border-border-primary'}
              ${player?.isHost ? 'before:content-[""] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-0.5 before:bg-gold' : ''}
            `}
          >
            <div className={`
              w-8 h-8 border flex items-center justify-center shrink-0
              ${player ? 'border-gold-dim bg-gold/5' : 'border-border-secondary'}
            `}>
              <User size={14} className={player ? 'text-gold' : 'text-text-faint'} />
            </div>
            
            <div className="flex-1 min-w-0">
              <p className={`text-sm truncate ${player ? 'text-text-primary' : 'text-text-faint italic'}`}>
                {player ? player.name : 'Waiting...'}
              </p>
              <p className="font-mono text-[9px] tracking-[0.2em] uppercase text-text-faint mt-0.5">
                {player ? (player.isHost ? 'Host' : 'Player') : 'Empty Slot'}
              </p>
            </div>

            {player?.name === session.playerName && (
              <span className="font-mono text-[8px] tracking-widest uppercase bg-gold text-black px-1.5 py-0.5">You</span>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-1">
        <div>
          <p className="font-mono text-[11px] text-text-faint tracking-wider">
            <span className="text-gold">{players.length}</span> / 4 players joined
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-dim animate-pulse-soft" />
            <p className="font-mono text-[10px] text-text-faint tracking-widest uppercase">Waiting for players</p>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-2">
          <Button 
            onClick={onStartGame} 
            disabled={!session.isHost || players.length < 2}
          >
            Begin the Crisis
          </Button>
          <p className="font-mono text-[9px] text-text-faint tracking-widest">
            Min. 2 players required
          </p>
        </div>
      </div>
    </motion.div>
  );
};
