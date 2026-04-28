import { useState } from 'react';
import { Panel, Input, Button } from '../ui';

export const CreateSessionScreen = ({ onSessionCreated }) => {
  const [name, setName] = useState('');
  const [status, setStatus] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) {
      setStatus({ text: 'Enter your name to continue.', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ text: 'Creating session...', type: '' });

    try {
      const response = await fetch('http://localhost:8000/lobby/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: name }),
      });

      if (!response.ok) throw new Error('Failed to create session');
      
      const data = await response.json();
      onSessionCreated({ sessionId: data.session_id, playerName: name, isHost: true });
    } catch (err) {
      setStatus({ text: 'Error connecting to server. Is the backend running?', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Panel title="New Session">
        <div>
          <p className="font-serif text-[32px] font-light text-text-primary mb-1 tracking-tight">Create a lobby</p>
          <p className="text-[13px] text-text-dim leading-relaxed">You'll receive a session code to share with up to 3 others.</p>
        </div>

        <Input
          label="Your name"
          id="create-name"
          placeholder="Enter your name"
          maxLength={24}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <p className={`font-mono text-[11px] tracking-wider text-center min-h-[16px] ${
          status.type === 'error' ? 'text-red-primary' : status.type === 'success' ? 'text-gold' : 'text-text-faint'
        }`}>
          {status.text}
        </p>

        <Button onClick={handleCreate} disabled={loading} className="self-start">
          {loading ? 'Processing...' : 'Create Session'}
        </Button>
      </Panel>
    </div>
  );
};
