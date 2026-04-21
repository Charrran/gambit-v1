import { motion } from 'framer-motion';
import { Button } from '../ui';

export const LandingScreen = ({ onNavigate }) => {
  return (
    <div className="flex flex-col items-center justify-center p-6 gap-0">
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.8 }}
        className="font-mono text-xs tracking-[0.4em] text-gold-dim uppercase mb-5"
      >
        August 1995 · Empire Bay Hotel
      </motion.p>
      
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
