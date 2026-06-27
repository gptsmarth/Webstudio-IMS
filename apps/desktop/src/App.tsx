import { useEffect, useState } from 'react';

import './App.css';

interface HealthState {
  status: string;
  message: string;
}

declare global {
  interface Window {
    webstudio?: {
      checkHealth: () => Promise<{ data?: { status?: string } }>;
    };
  }
}

export function App(): JSX.Element {
  const [health, setHealth] = useState<HealthState>({
    status: 'checking',
    message: 'Connecting to API...',
  });

  useEffect(() => {
    async function bootstrap(): Promise<void> {
      try {
        if (!window.webstudio?.checkHealth) {
          setHealth({ status: 'error', message: 'IPC bridge unavailable' });
          return;
        }
        const response = await window.webstudio.checkHealth();
        setHealth({
          status: response.data?.status ?? 'unknown',
          message: 'Backend health check complete',
        });
      } catch {
        setHealth({ status: 'error', message: 'Backend unreachable' });
      }
    }

    void bootstrap();
  }, []);

  return (
    <main className="app">
      <h1>WEBSTUDIO IMS</h1>
      <p>Sprint 0 foundation</p>
      <p>
        API health: <strong>{health.status}</strong> — {health.message}
      </p>
    </main>
  );
}
