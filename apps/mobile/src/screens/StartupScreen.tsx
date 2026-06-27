import { StyleSheet, Text, View } from 'react-native';
import { useEffect, useState } from 'react';

import { createMobileApiClient } from '../api/client';
import type { AppTheme } from '../theme';

interface StartupScreenProps {
  theme: AppTheme;
}

export function StartupScreen({ theme }: StartupScreenProps): JSX.Element {
  const [healthStatus, setHealthStatus] = useState('checking');

  useEffect(() => {
    async function checkHealth(): Promise<void> {
      try {
        const client = createMobileApiClient();
        const response = await client.getHealthLive();
        setHealthStatus(response.data.status);
      } catch {
        setHealthStatus('unreachable');
      }
    }

    void checkHealth();
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <Text style={[styles.title, { color: theme.colors.text }]}>WEBSTUDIO IMS</Text>
      <Text style={{ color: theme.colors.muted }}>Sprint 0 foundation</Text>
      <Text style={{ color: theme.colors.text }}>API health: {healthStatus}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
  },
});
