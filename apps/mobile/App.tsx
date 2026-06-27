import { NavigationContainer, DefaultTheme, DarkTheme } from '@react-navigation/native';
import { useColorScheme } from 'react-native';

import { RootNavigator } from './src/navigation/RootNavigator';
import { getTheme } from './src/theme';

export default function App(): JSX.Element {
  const scheme = useColorScheme();
  const theme = getTheme(scheme);

  return (
    <NavigationContainer theme={scheme === 'dark' ? DarkTheme : DefaultTheme}>
      <RootNavigator theme={theme} />
    </NavigationContainer>
  );
}
