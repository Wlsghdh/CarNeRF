import '../global.css';

import { DarkTheme, ThemeProvider } from '@react-navigation/native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack, useRouter } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useState } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import 'react-native-reanimated';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { setUnauthorizedHandler } from '../lib/api/client';
import { useAuth } from '../lib/store/auth';

export {
  ErrorBoundary,
} from 'expo-router';

export const unstable_settings = {
  initialRouteName: '(tabs)',
};

SplashScreen.preventAutoHideAsync();

const CarNeRFTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: '#000000',
    card: '#0E1117',
    primary: '#C8A96E',
    text: '#FFFFFF',
    border: 'rgba(255,255,255,0.06)',
    notification: '#C8A96E',
  },
};

function useQueryClient() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );
  return client;
}

export default function RootLayout() {
  const [loaded, error] = useFonts({
    'Pretendard': require('../assets/fonts/Pretendard-Regular.otf'),
    'Pretendard-Medium': require('../assets/fonts/Pretendard-Medium.otf'),
    'Pretendard-SemiBold': require('../assets/fonts/Pretendard-SemiBold.otf'),
    'Pretendard-Bold': require('../assets/fonts/Pretendard-Bold.otf'),
  });

  const hydrate = useAuth((s) => s.hydrate);
  const queryClient = useQueryClient();
  const router = useRouter();

  useEffect(() => {
    if (error) throw error;
  }, [error]);

  useEffect(() => {
    hydrate();
    setUnauthorizedHandler(() => {
      router.replace('/login');
    });
  }, [hydrate, router]);

  useEffect(() => {
    if (loaded) SplashScreen.hideAsync();
  }, [loaded]);

  if (!loaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: '#000' }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider value={CarNeRFTheme}>
            <Stack screenOptions={{ contentStyle: { backgroundColor: '#000000' } }}>
              <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
              <Stack.Screen name="login" options={{ headerShown: false, presentation: 'modal' }} />
              <Stack.Screen
                name="vehicle/[id]"
                options={{ headerShown: false, contentStyle: { backgroundColor: '#000' } }}
              />
              <Stack.Screen
                name="viewer/[id]"
                options={{ headerShown: false, presentation: 'fullScreenModal' }}
              />
              <Stack.Screen name="compare" options={{ title: '비교', headerStyle: { backgroundColor: '#0E1117' }, headerTintColor: '#FFF' }} />
              <Stack.Screen name="points" options={{ title: '포인트', headerStyle: { backgroundColor: '#0E1117' }, headerTintColor: '#FFF' }} />
              <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
            </Stack>
          </ThemeProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
