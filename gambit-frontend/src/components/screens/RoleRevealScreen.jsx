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
        <p className="font-mono text-[11px] tracking-[0.4em] uppercase text-gold-dim mb-2">Your Role</p>
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
            <p className="font-mono text-[12px] tracking-[0.3em] uppercase text-text-faint">Tap to reveal your role</p>
          </div>

          {/* Card Front */}
          <div 
            className="absolute inset-0 backface-hidden bg-surface border border-border-secondary rotate-y-180 flex flex-col overflow-hidden before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-0.5 before:bg-gradient-to-r before:from-transparent before:via-gold before:to-transparent"
          >
            <div className="p-6 pb-5 border-b border-border-primary text-left">
              <p className="font-mono text-[11px] tracking-[0.35em] uppercase text-gold-dim mb-2">{role.tag}</p>
              <h3 className="font-serif text-[30px] font-semibold leading-tight text-text-primary">{role.name}</h3>
              <p className="font-serif italic text-sm text-text-dim mt-1">{role.analogue}</p>
            </div>
            
            <div className="p-6 flex-1 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
              {role.traits.map((trait, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <p className="font-mono text-[11px] tracking-[0.25em] uppercase text-text-faint">{trait.label}</p>
                  <p className="text-[15px] text-text-dim leading-relaxed">{trait.value}</p>
                </div>
              ))}
              
              <div className="mt-auto bg-deep border border-red-dim p-4 relative">
                <p className="font-mono text-[10px] tracking-[0.3em] text-red-primary mb-1.5 uppercase">⬛ CLASSIFIED</p>
                <p className="text-sm text-text-dim leading-relaxed italic">{role.secret}</p>
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
            <p className="font-mono text-[12px] tracking-widest text-text-faint uppercase animate-pulse-soft">
              Your briefing is classified. Do not share it.
            </p>
            <Button onClick={onAccept}>Accept This Role →</Button>
          </motion.div>
        ) : (
          <p className="font-mono text-[12px] tracking-widest text-text-faint uppercase animate-pulse-soft">
            Tap the card to reveal
          </p>
        )}
      </div>
    </div>
  );
};
