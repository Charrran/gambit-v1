import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

export function useGameRoom(sessionId, playerId) {
  const [gameState, setGameState] = useState(null);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const wsRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId || !playerId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    console.log(`Connecting to WS: ${WS_BASE_URL}/ws/play/${sessionId}/${playerId}`);
    const ws = new WebSocket(`${WS_BASE_URL}/ws/play/${sessionId}/${playerId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WS Message Received:', data);
        
        if (data.type === 'ERROR' || data.type === 'FATAL_ERROR') {
          setError(data.error);
        } else {
          // Some backend WS messages are partial updates (choice prompts,
          // waiting notices). Preserve the last full scene/lobby snapshot.
          setGameState((prev) => ({ ...(prev || {}), ...data }));
        }
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      wsRef.current = null;
      // Optional: implement reconnect logic here
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('Connection error');
    };

    wsRef.current = ws;
  }, [sessionId, playerId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendChoice = useCallback((choiceId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ choice_id: choiceId }));
    } else {
      console.error('Cannot send choice: WebSocket not connected');
      setError('Not connected to game server');
    }
  }, []);

  const sendMessage = useCallback((msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);


  // API helper for joining a lobby
  const joinLobby = async (sessionIdToJoin, playerName) => {
    try {
      const response = await fetch(`${API_BASE_URL}/lobby/${sessionIdToJoin}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerName }), // Using playerName as ID for simplicity
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to join lobby');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      console.error('Join lobby error:', err);
      throw err;
    }
  };

  return {
    gameState,
    error,
    isConnected,
    connect,
    disconnect,
    sendChoice,
    sendMessage,
    joinLobby,

  };
}
