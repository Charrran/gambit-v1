import { useState } from 'react';
import { Panel, Input, Button } from '../ui';

export const JoinSessionScreen = ({ onJoined }) => {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleJoin = async () => {
    if (!code || code.length < 4) {
      setStatus({ text: 'Enter a valid session code.', type: 'error' });
      return;
    }
    if (!name.trim()) {
      setStatus({ text: 'Enter your name to continue.', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ text: 'Joining session...', type: '' });

    // Mock API Call
    setTimeout(() => {
      onJoined({ sessionId: code.toUpperCase(), playerName: name, isHost: false });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Panel title="Join Session">
        <div>
          <p className="font-serif text-[32px] font-light text-text-primary mb-1 tracking-tight">Enter the code</p>
          <p className="text-[13px] text-text-dim leading-relaxed">Ask the host for the session code and enter it below.</p>
        </div>

        <div className="flex flex-col gap-5">
          <Input
            label="Session code"
            id="join-code"
            placeholder="e.g. AB12CD"
            maxLength={8}
            className="uppercase tracking-[0.2em]"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />

          <Input
            label="Your name"
            id="join-name"
            placeholder="Enter your name"
            maxLength={24}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <p className={`font-mono text-[11px] tracking-wider text-center min-h-[16px] ${
          status.type === 'error' ? 'text-red-primary' : status.type === 'success' ? 'text-gold' : 'text-text-faint'
        }`}>
          {status.text}
        </p>

        <Button onClick={handleJoin} disabled={loading} className="self-start">
          {loading ? 'Processing...' : 'Join Session'}
        </Button>
      </Panel>
    </div>
  );
};
