import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { StartupScreen } from '../screens/StartupScreen';
import type { AppTheme } from '../theme';

export type RootStackParamList = {
  Startup: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

interface RootNavigatorProps {
  theme: AppTheme;
}

export function RootNavigator({ theme }: RootNavigatorProps): JSX.Element {
  return (
    <Stack.Navigator>
      <Stack.Screen name="Startup" options={{ title: 'WEBSTUDIO IMS' }}>
        {() => <StartupScreen theme={theme} />}
      </Stack.Screen>
    </Stack.Navigator>
  );
}
