const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const rawWsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// Strip trailing slashes to prevent // double-slash issues
const API_BASE_URL = rawApiUrl.replace(/\/+$/, '');
const WS_BASE_URL = rawWsUrl.replace(/\/+$/, '');

export { API_BASE_URL, WS_BASE_URL };
