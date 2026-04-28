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

  const myPlayer = players.find(p => p.player_id === session?.playerName);
  const isReady = hasClickReady || myPlayer?.flags?.includes('ready');

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
            <div className="w-full flex flex-wrap justify-center gap-6 mt-2">
              {players.map((p) => {
                const isPlayerReady = p.flags?.includes('ready');
                return (
                  <div key={p.player_id} className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${isPlayerReady ? 'bg-gold shadow-[0_0_8px_rgba(212,175,55,0.6)]' : 'bg-white/10'}`} />
                    <span className={`font-mono text-[10px] tracking-widest uppercase transition-colors duration-500 ${isPlayerReady ? 'text-gold' : 'text-text-faint'}`}>
                      {p.player_id}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col items-center gap-4">
            <Button
              variant={isReady ? 'ghost' : 'primary'}
              onClick={handleReady}
              disabled={isReady}
            >
              {isReady ? 'Waiting for others...' : "I'm Ready"}
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
