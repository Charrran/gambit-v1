import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { Button } from '../ui';

const EPISODES = [
  {
    id: 'EP_01_REGENT',
    title: 'Episode 1 — The Regent Rebellion',
    subtitle: 'Empire Bay Hotel · August 1995',
    description: 'A patriarch. A strategist. A woman nobody can name. A family about to fracture. Four roles. One crisis. Fifteen minutes of alternate history.',
    status: 'AVAILABLE'
  },
];

/**
 * EpisodeSelectScreen
 * Props:
 *   hostName       – the name the host entered
 *   sessionId      – the REAL session ID already created by the backend
 *   onEpisodeConfirmed(sessionData) – called with { sessionId, playerName, isHost, episodeId }
 */
export const EpisodeSelectScreen = ({ hostName, sessionId, onEpisodeConfirmed }) => {
  const [selectedId, setSelectedId] = useState('EP_01_REGENT');
  const [loading, setLoading] = useState(false);

  const handleConfirm = () => {
    if (!selectedId || !sessionId) return;
    setLoading(true);

    // Session is already created in the backend — just forward the confirmed episode
    onEpisodeConfirmed({
      sessionId,          // ← real backend session ID, NOT a mock
      playerName: hostName,
      isHost: true,
      episodeId: selectedId,
    });
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
        disabled={!selectedId || loading || !sessionId}
        className="min-w-[240px]"
      >
        {loading ? 'Securing History...' : 'Confirm Episode'}
      </Button>
    </div>
  );
};
