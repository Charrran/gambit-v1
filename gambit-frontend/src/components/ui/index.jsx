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
