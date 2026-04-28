// src/components/screens/GameScreen.jsx
// ─────────────────────────────────────────────────────────────────────────────
// MOCK DATA BLOCK — everything in this section can be ripped out and replaced
// with live WebSocket / API state when you connect the backend.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ROLES } from '../../data/roles';

// ── Mock: current round metadata ─────────────────────────────
const MOCK_ROUND = {
  number: 3,
  total: 8,
  phase: 'DECISION', // 'NARRATION' | 'DECISION' | 'RESOLUTION'
};

// ── Mock: current narration beat ─────────────────────────────
// type: 'environment' renders in italic serif (stage direction feel)
// type: 'speech' renders in upright serif with speaker label
const MOCK_NARRATION = {
  type: 'environment',
  speaker: null,
  text: 'The lights in Suite 412 flicker once. Outside, the corridor has gone completely silent. Govardhan has placed a sealed envelope on the table. Nobody speaks. The air conditioning hums at the back of the room. Somewhere down the hall, a telephone rings twice and stops.',
};

// ── Mock: player decision options ────────────────────────────
const MOCK_OPTIONS = [
  { id: 'A', text: 'Pick up the envelope. Open it in front of everyone present.' },
  { id: 'B', text: 'Leave it untouched. Walk slowly to the window and say nothing.' },
  { id: 'C', text: 'Slide it back across the table without making eye contact.' },
];

// ── Mock: the three counterparts visible in The Room ─────────
// Replace with players array from game state minus yourself
const MOCK_COUNTERPARTS = [
  { roleKey: 'govardhan_naidu', status: 'Decided',     decided: true,  isActive: false },
  { roleKey: 'raghava_rao',     status: 'Deliberating', decided: false, isActive: true  },
  { roleKey: 'venkatadri',      status: 'Waiting',      decided: false, isActive: false },
];

// ── Mock: pairwise trust values 0–100 ────────────────────────
// Keys must follow the pattern "roleKeyA-roleKeyB" (alphabetical or consistent order)
const MOCK_TRUST = {
  'raghava_rao-govardhan_naidu': 62,
  'raghava_rao-saraswathi':      84,
  'raghava_rao-venkatadri':      55,
  'govardhan_naidu-saraswathi':  30,
  'govardhan_naidu-venkatadri':  45,
  'saraswathi-venkatadri':       71,
};

// ── Mock: press headlines for Daily Chronicle ─────────────────
const MOCK_HEADLINES = [
  {
    id: 1,
    dateline: 'Empire Bay Courier · 14 August 1995',
    headline: "Uncertainty at the Top: Rao's Future in Question",
    body: 'Senior figures within the party met in closed session last evening. No official communiqué has been released.',
  },
  {
    id: 2,
    dateline: 'The Political Observer · Late Edition',
    headline: 'Naidu Maintains Silence as Pressure Mounts',
    body: "The party secretary has declined three requests for comment following yesterday's session in the legislature.",
  },
  {
    id: 3,
    dateline: 'Deccan Wire Service · Flash',
    headline: 'Public Mood Shifts: Calls for Clarity Intensify',
    body: 'Street-level support remains fractured. Cadre loyalty is reported to be uncertain across three districts.',
  },
];
// ─────────────────────────────────────────────────────────────────────────────
// END MOCK DATA BLOCK
// ─────────────────────────────────────────────────────────────────────────────


// ── Sub-component: Human Silhouette ───────────────────────────
const Silhouette = ({ active, decided }) => {
  const bodyFill = decided
    ? 'var(--color-gold-dim)'
    : active
    ? 'var(--color-border-secondary)'
    : 'var(--color-border-primary)';

  return (
    <svg width="46" height="60" viewBox="0 0 46 60" fill="none">
      {decided && (
        <circle cx="23" cy="15" r="14"
          stroke="var(--color-gold-dim)" strokeWidth="0.6"
          fill="none" opacity="0.45"
        />
      )}
      <circle cx="23" cy="15" r="11" fill={bodyFill} />
      <path d="M5 58 C5 40 11 32 23 32 C35 32 41 40 41 58" fill={bodyFill} />
    </svg>
  );
};


// ── Sub-component: Trust Matrix (SVG diamond) ─────────────────
const TrustMatrix = ({ myRoleKey }) => {
  const keys = Object.keys(ROLES);

  // Diamond positions in a 200×200 viewBox
  const pos = {
    [keys[0]]: { x: 100, y: 25  },   // top
    [keys[1]]: { x: 30,  y: 100 },   // left
    [keys[2]]: { x: 170, y: 100 },   // right
    [keys[3]]: { x: 100, y: 175 },   // bottom
  };

  const getTrust = (a, b) => {
    if (!gameState?.state_axes) return 50;
    // Map backend axes (e.g. 'raghava_restoration') to pairwise visual trust
    // For now, a simple average of relevant axes or default to 50
    const axisKey = `${a}-${b}`;
    return gameState.state_axes[axisKey] ?? 50;
  };


  const edgeStyle = (trust) => ({
    stroke: trust >= 65
      ? 'var(--color-gold-dim)'
      : trust >= 40
      ? 'var(--color-border-secondary)'
      : 'var(--color-red-dim)',
    strokeWidth: 0.6 + (trust / 100) * 2.2,
    strokeDasharray: trust < 40 ? '3 2' : trust < 60 ? '5 3' : undefined,
    opacity: 0.8,
  });

  // All 6 edges between 4 nodes
  const edges = [];
  for (let i = 0; i < keys.length; i++)
    for (let j = i + 1; j < keys.length; j++)
      edges.push([keys[i], keys[j]]);

  return (
    <svg viewBox="0 0 200 200" className="w-full" style={{ maxHeight: 280 }}>
      {edges.map(([a, b]) => {
        const s = edgeStyle(getTrust(a, b));
        return (
          <line key={`${a}-${b}`}
            x1={pos[a].x} y1={pos[a].y}
            x2={pos[b].x} y2={pos[b].y}
            stroke={s.stroke}
            strokeWidth={s.strokeWidth}
            strokeDasharray={s.strokeDasharray}
            opacity={s.opacity}
          />
        );
      })}

      {keys.map((k) => {
        const p = pos[k];
        const isMe = k === myRoleKey;
        const name = ROLES[k]?.name?.split(' ')[0] || k;
        const labelY = p.y < 100 ? p.y - 13 : p.y + 17;

        return (
          <g key={k}>
            {isMe && (
              <circle cx={p.x} cy={p.y} r={12}
                stroke="var(--color-gold)" strokeWidth="0.5"
                fill="none" opacity="0.35"
              />
            )}
            <circle cx={p.x} cy={p.y} r={isMe ? 7 : 5}
              fill={isMe ? 'var(--color-gold)' : 'var(--color-surface2)'}
              stroke={isMe ? 'var(--color-gold)' : 'var(--color-border-secondary)'}
              strokeWidth="1"
            />
            <text x={p.x} y={labelY}
              textAnchor="middle"
              fill={isMe ? 'var(--color-gold)' : 'var(--color-text-faint)'}
              fontSize={isMe ? '9.5' : '8.5'}
              fontFamily="var(--font-mono)"
              letterSpacing="0.8"
            >
              {name}
            </text>
          </g>
        );
      })}
    </svg>
  );
};


// ── Sub-component: Poll Results ──────────────────────────────
const PollResults = ({ options, votes, totalPlayers }) => {
  // Calculate counts per option
  const counts = options.reduce((acc, opt) => {
    acc[opt.id] = Object.values(votes).filter(v => v === opt.id).length;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-4 mb-6">
      <p className="font-mono text-[10px] tracking-[0.4em] uppercase text-gold mb-2">
        Consensus Distribution
      </p>
      {options.map((opt) => {
        const count = counts[opt.id] || 0;
        const pct = totalPlayers > 0 ? (count / totalPlayers) * 100 : 0;
        
        return (
          <div key={opt.id} className="flex flex-col gap-1.5">
            <div className="flex justify-between items-end">
              <span className="text-[13px] text-text-primary font-medium">{opt.text}</span>
              <span className="font-mono text-[11px] text-gold">{Math.round(pct)}%</span>
            </div>
            <div className="h-1.5 bg-surface border border-border-primary relative overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-gold-dim to-gold shadow-[0_0_10px_rgba(201,168,76,0.3)]"
              />
            </div>
            <p className="font-mono text-[9px] text-text-faint uppercase tracking-wider">
              {count} {count === 1 ? 'Vote' : 'Votes'}
            </p>
          </div>
        );
      })}
    </div>
  );
};


// ── Sub-component: Countdown Timer Bar ────────────────────────
const TOTAL_SECONDS = 45;

const TimerBar = ({ seconds }) => {
  const pct = (seconds / TOTAL_SECONDS) * 100;
  const urgent = seconds <= 10;
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');

  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-text-faint">
          Decision Window
        </span>
        <motion.span
          className={`font-mono text-[14px] tabular-nums font-medium ${
            urgent ? 'text-red-primary' : 'text-text-dim'
          }`}
          animate={urgent ? { opacity: [1, 0.45, 1] } : {}}
          transition={urgent ? { duration: 0.55, repeat: Infinity } : {}}
        >
          {mm}:{ss}
        </motion.span>
      </div>

      <div className="relative h-[2px] w-full bg-border-primary overflow-hidden">
        {/* Fill bar */}
        <div
          className={`absolute left-0 top-0 h-full transition-[background-color] duration-300 ${
            urgent ? 'bg-red-primary' : 'bg-gold-dim'
          }`}
          style={{ width: `${pct}%`, transition: 'width 1s linear, background-color 0.3s' }}
        />
        {/* Urgent pulse overlay */}
        {urgent && (
          <motion.div
            className="absolute inset-0 bg-red-primary/25"
            animate={{ opacity: [0, 0.7, 0] }}
            transition={{ duration: 0.55, repeat: Infinity }}
          />
        )}
      </div>
    </div>
  );
};


// ── Main GameScreen ───────────────────────────────────────────
// Props:
//   roleKey  – one of the ROLES keys, e.g. 'saraswathi'
//              (passed from App after role assignment)
export const GameScreen = ({ roleKey = 'saraswathi', gameRoom = {}, session = {} }) => {
  const { gameState, sendChoice } = gameRoom;
  
  const [timeLeft, setTimeLeft] = useState(TOTAL_SECONDS);
  const [selected, setSelected] = useState(null);
  const [committed, setCommitted] = useState(false);
  
  // Map backend state
  const isInterrogation = gameState?.phase === 'INTERROGATION';
  const isPoll = gameState?.phase === 'POLL';
  const currentPhase = gameState?.phase || 'INITIALIZING';
  const currentChapterTitle = gameState?.chapter_title || "Loading Story...";
  
  const narrationText = gameState?.flavor || "Awaiting the next move...";
  const narrationSpeaker = gameState?.spotlight_role || "Narrator";
  
  const options = gameState?.options || [];

  // Derive counterparts from active players
  const counterparts = Object.keys(gameState?.active_players || {})
    .filter(pid => pid !== session?.playerName)
    .map(pid => {
      const p = gameState.active_players[pid];
      return {
        roleKey: p.role,
        name: p.player_id,
        decided: !!gameState.votes?.[pid],
        isActive: gameState.current_scene_player === pid || gameState.spotlight_player === pid,
        isTarget: gameState.current_interrogation_pair?.target_player === pid
      };
    });





  const role = ROLES[roleKey] || ROLES['saraswathi'];

  // Countdown tick
  useEffect(() => {
    if (committed || timeLeft <= 0) return;
    const id = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(id);
  }, [committed, timeLeft]);

  return (
    // Uses w-screen to break out of App's centering container
    <div className="w-screen h-screen flex overflow-hidden bg-black">

      {/* ═══════════════════════════════════════════════════════
          LEFT COLUMN — Identity
      ════════════════════════════════════════════════════════ */}
      <aside
        className="flex flex-col h-full border-r border-border-primary overflow-hidden"
        style={{ width: '25%', minWidth: 220, maxWidth: 320 }}
      >
        {/* Panel header */}
        <div className="px-5 h-11 border-b border-border-primary flex items-center justify-between flex-shrink-0">
          <span className="font-mono text-[10px] tracking-[0.45em] uppercase text-text-faint">Your Identity</span>
          <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-gold">{role.tag}</span>
        </div>

        {/* Portrait silhouette */}
        <div className="relative flex flex-col items-center justify-start pt-6 pb-5 border-b border-border-primary flex-shrink-0 overflow-hidden"
          style={{ background: 'var(--color-deep)' }}
        >
          <div className="absolute inset-0"
            style={{ background: 'radial-gradient(ellipse at center, var(--color-surface) 0%, var(--color-deep) 70%)' }}
          />
          <div className="relative z-10 flex flex-col items-center gap-2">
            <Silhouette active={false} decided={false} />
            <div className="text-center">
              <p className="font-serif text-[14px] text-transparent leading-none select-none">Spacer</p>
              <p className="font-mono text-[10px] tracking-[0.45em] uppercase text-gold-dim opacity-55 mt-1">
                Identity Sealed
              </p>
            </div>
          </div>
        </div>

        {/* Name & public title */}
        <div className="px-5 py-4 border-b border-border-primary flex-shrink-0">
          <h2 className="font-serif text-[21px] font-light text-text-primary tracking-tight leading-tight">
            {role.name}
          </h2>
          <p className="font-mono text-[10.5px] tracking-[0.22em] uppercase text-gold-dim mt-1.5">
            {role.analogue}
          </p>
        </div>

        {/* Trait dossier — scrollable */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4"
          style={{ scrollbarWidth: 'none' }}
        >
          {role.traits.map((trait, i) => (
            <div key={i}>
              <p className="font-mono text-[9.5px] tracking-[0.35em] uppercase text-text-faint mb-1">
                {trait.label}
              </p>
              <p className="text-[13.5px] text-text-dim leading-relaxed">
                {trait.value}
              </p>
            </div>
          ))}
        </div>

        {/* Secret objective — locked at bottom */}
        <div className="flex-shrink-0 mx-4 mb-4 p-3.5 relative"
          style={{
            border: '1px solid rgba(122, 100, 48, 0.4)',
            background: 'rgba(201,168,76,0.03)',
          }}
        >
          <div className="absolute -top-px left-5 right-5 h-px"
            style={{ background: 'linear-gradient(to right, transparent, var(--color-gold-dim), transparent)' }}
          />
          <p className="font-mono text-[9.5px] tracking-[0.4em] uppercase text-gold mb-2">
            Secret Objective
          </p>
          <p className="font-serif text-[14px] italic text-text-dim leading-relaxed">
            {role.secret}
          </p>
        </div>
      </aside>


      {/* ═══════════════════════════════════════════════════════
          CENTER COLUMN — The Theatre
      ════════════════════════════════════════════════════════ */}
      <main className="flex-1 flex flex-col h-full min-w-0">

        {/* Status bar */}
        <div className="px-6 h-11 border-b border-border-primary flex items-center justify-between flex-shrink-0">
          <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-text-faint">
            Round{' '}
            <span className="text-gold font-medium">{gameState?.revision || 1}</span>
            {' '}/ {gameState?.total_steps || 12}
          </span>
          <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-text-faint">
            {currentChapterTitle}
          </span>
          <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-text-faint">
            Phase:{' '}
            <span className={isInterrogation ? "text-red-primary font-medium animate-pulse" : "text-gold font-medium"}>
              {currentPhase}
            </span>
          </span>
        </div>

        {/* THE ROOM — three counterpart silhouettes */}
        <div className="border-b border-border-primary flex flex-col items-center justify-start flex-shrink-0 px-6 pt-6 pb-5"
          style={{ background: 'rgba(15,13,10,0.5)' }}
        >
          <div className="flex items-center justify-center gap-16">
            {(counterparts.length > 0 ? counterparts : MOCK_COUNTERPARTS).map((cp, i) => (
              <motion.div key={i}
                className="flex flex-col items-center gap-2"
                animate={cp.isActive ? { opacity: [0.6, 1, 0.6] } : {}}
                transition={cp.isActive ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : {}}
              >
                <div className="relative flex items-center justify-center">
                  {(cp.isActive || cp.isTarget) && (
                    <motion.div
                      className={`absolute rounded-full pointer-events-none ${cp.isTarget ? 'bg-red-primary/10' : 'bg-gold/10'}`}
                      style={{
                        width: 80, height: 80,
                        background: cp.isTarget 
                          ? 'radial-gradient(circle, rgba(139,38,53,0.14) 0%, transparent 70%)'
                          : 'radial-gradient(circle, rgba(201,168,76,0.14) 0%, transparent 70%)',
                        top: '50%', left: '50%',
                        transform: 'translate(-50%, -50%)',
                      }}
                      animate={{ scale: [0.8, 1.3, 0.8], opacity: [0.4, 0.7, 0.4] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                  )}
                  <Silhouette active={cp.isActive} decided={cp.decided} />
                </div>

                <div className="text-center">
                  <p className="font-serif text-[14px] text-text-dim leading-none">
                    {ROLES[cp.roleKey]?.name || cp.name}
                  </p>
                  <p className={`font-mono text-[9px] tracking-[0.2em] uppercase mt-1 ${cp.decided ? 'text-gold' : 'text-text-faint'}`}>
                    {cp.isTarget ? 'Under Scrutiny' : cp.decided ? 'Decided' : 'Deliberating'}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>

        </div>

        {/* Timer bar */}
        <div className="px-6 pt-4 pb-2 flex-shrink-0">
          <TimerBar seconds={timeLeft} />
        </div>

        {/* Narration + options — scrollable */}
        <div className="flex-1 overflow-y-auto px-6 pt-4 pb-2"
          style={{ scrollbarWidth: 'none' }}
        >
          {/* Narration dialogue box */}
          <div className={`border-l-2 pl-4 mb-6 transition-colors duration-1000 ${
            isInterrogation ? 'border-red-primary' : 'border-gold/35'
          }`}>
            <AnimatePresence mode="wait">
              <motion.div
                key={narrationText}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 4 }}
                transition={{ duration: 0.4 }}
              >
                {!gameState && MOCK_NARRATION.type === 'environment' ? (
                  <p className="font-serif text-[16.5px] italic text-text-dim leading-[1.8] tracking-wide">
                    {narrationText}
                  </p>
                ) : (
                  <div>
                    <p className={`font-mono text-[10px] tracking-[0.4em] uppercase mb-2 ${isInterrogation ? 'text-red-primary' : 'text-gold'}`}>
                      {narrationSpeaker}
                    </p>
                    <p className="font-serif text-[18px] text-text-primary leading-relaxed">
                      "{narrationText}"
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Tactical options */}
          <AnimatePresence mode="wait">
            {!committed ? (
              <motion.div key="options"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex flex-col gap-2 mb-6"
              >
                <p className="font-mono text-[10px] tracking-[0.4em] uppercase text-text-faint mb-1">
                  Your Move
                </p>

                {options.map((opt) => (
                  <motion.button key={opt.id}
                    whileTap={{ scale: 0.995 }}
                    onClick={() => setSelected(opt.id || opt.choice_id)}
                    className={`w-full text-left px-4 py-3.5 border transition-all duration-200 ${
                      selected === (opt.id || opt.choice_id)
                        ? (isInterrogation ? 'border-red-primary bg-red-primary/5 shadow-[0_0_18px_rgba(139,38,53,0.1)]' : 'border-gold bg-gold/5 shadow-[0_0_18px_rgba(201,168,76,0.07)]')
                        : 'border-border-primary bg-deep/30 hover:border-border-secondary'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className={`font-mono text-[12px] shrink-0 mt-0.5 ${
                        selected === opt.id ? 'text-gold' : 'text-text-faint'
                      }`}>
                        {opt.id}.
                      </span>
                      <span className={`text-[15px] leading-relaxed ${
                        selected === opt.id ? 'text-text-primary' : 'text-text-dim'
                      }`}>
                        {opt.text}
                      </span>
                    </div>
                  </motion.button>
                ))}

                <div className="flex justify-end mt-3">
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      if (selected) {
                        setCommitted(true);
                        if (sendChoice) sendChoice(selected);
                      }
                    }}
                    className={`font-mono text-[12px] tracking-[0.25em] uppercase px-7 py-3 transition-all duration-200 ${
                      selected
                        ? (isInterrogation ? 'bg-red-primary text-text-primary hover:bg-red-dim cursor-pointer' : 'bg-gold text-black hover:bg-gold-bright cursor-pointer shadow-lg shadow-gold/15')
                        : 'bg-border-primary text-text-faint cursor-not-allowed opacity-35'
                    }`}
                  >
                    Commit Decision
                  </motion.button>
                </div>
              </motion.div>
            ) : (
              <motion.div key="sealed"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col"
              >
                <div className="border border-border-secondary bg-surface/30 px-5 py-4 mb-8 flex items-center gap-3">
                  <motion.div
                    className="w-1.5 h-1.5 rounded-full bg-gold flex-shrink-0"
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                  />
                  <div>
                    <p className="font-mono text-[10px] tracking-[0.4em] uppercase text-gold">
                      Decision Recorded
                    </p>
                    <p className="text-[14px] text-text-faint mt-0.5">
                      Awaiting group resolution...
                    </p>
                  </div>
                </div>

                {/* Show Poll Results if in poll mode and committed */}
                {MOCK_ROUND.phase === 'POLL' && (
                  <PollResults 
                    options={MOCK_OPTIONS} 
                    votes={{ 'p1': 'A', 'p2': 'A', 'p3': 'B' }} // Mock votes
                    totalPlayers={4}
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Character seal — signature at the bottom */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-border-primary">
          <div className="flex items-center gap-4">
            <div className="flex-1 h-px"
              style={{ background: 'linear-gradient(to right, transparent, var(--color-border-secondary))' }}
            />
            <p className="font-serif text-[19px] font-light tracking-[0.2em] text-text-dim whitespace-nowrap">
              {role.name}
            </p>
            <div className="flex-1 h-px"
              style={{ background: 'linear-gradient(to left, transparent, var(--color-border-secondary))' }}
            />
          </div>
        </div>
      </main>


      {/* ═══════════════════════════════════════════════════════
          RIGHT COLUMN — Intel
      ════════════════════════════════════════════════════════ */}
      <aside
        className="flex flex-col h-full border-l border-border-primary overflow-hidden"
        style={{ width: '25%', minWidth: 220, maxWidth: 320 }}
      >
        {/* ── Trust Matrix ─────────────────────────────────── */}
        <div className="flex-shrink-0 border-b border-border-primary">
          <div className="px-4 h-11 border-b border-border-primary/50 flex items-center justify-between">
            <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-gold-dim">
              Trust Matrix
            </span>
            <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-text-faint">
              Live
            </span>
          </div>

          <div className="px-3 pt-2 pb-3">
            <TrustMatrix myRoleKey={roleKey} />

            {/* Legend */}
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 px-1">
              {[
                { color: 'var(--color-gold-dim)',         dash: false, label: 'Allied'   },
                { color: 'var(--color-border-secondary)', dash: true,  label: 'Neutral'  },
                { color: 'var(--color-red-dim)',           dash: true,  label: 'Hostile'  },
              ].map(({ color, dash, label }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <svg width="16" height="6" viewBox="0 0 16 6">
                    <line x1="0" y1="3" x2="16" y2="3"
                      stroke={color} strokeWidth="1.5"
                      strokeDasharray={dash ? '3 2' : undefined}
                    />
                  </svg>
                  <span className="font-mono text-[9px] tracking-widest uppercase text-text-faint">
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Daily Chronicle ───────────────────────────────── */}
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
          <div className="px-4 h-11 border-b border-border-primary/50 flex items-center justify-between">
            <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-gold-dim">
              The Daily Chronicle
            </span>
          </div>

          {/* Masthead ornament */}
          <div className="text-center py-3 mx-4 border-b border-border-primary/40">
            <p className="font-serif text-[12px] italic text-text-faint tracking-wider">
              Public Dispatch · Live Edition
            </p>
            <div className="flex items-center gap-2 mt-1.5">
              <div className="flex-1 h-px bg-border-primary" />
              <div className="w-1 h-1 rounded-full bg-gold-dim opacity-55" />
              <div className="w-5 h-px bg-gold-dim opacity-55" />
              <div className="w-1 h-1 rounded-full bg-gold-dim opacity-55" />
              <div className="flex-1 h-px bg-border-primary" />
            </div>
          </div>

          {/* Headlines */}
          <div className="px-4 py-2">
            {MOCK_HEADLINES.map((item, i) => (
              <motion.div key={item.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.12 }}
                className="py-4 border-b border-border-primary/40 last:border-0"
              >
                <p className="font-mono text-[9px] tracking-[0.3em] uppercase text-text-faint mb-1.5">
                  {item.dateline}
                </p>
                <p className="font-serif text-[15px] font-semibold text-text-primary leading-snug mb-1.5">
                  {item.headline}
                </p>
                <p className="text-[11px] text-text-dim leading-relaxed">
                  {item.body}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
};
