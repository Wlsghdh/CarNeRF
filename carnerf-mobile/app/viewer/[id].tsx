import { useLocalSearchParams, useRouter } from 'expo-router';
import { X } from 'lucide-react-native';
import { Pressable, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://223.195.111.31:5199';

export default function ViewerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  return (
    <View className="flex-1 bg-black">
      <WebView
        source={{ uri: `${BASE}/viewer?id=${id}&embed=1` }}
        originWhitelist={['*']}
        allowsInlineMediaPlayback
        javaScriptEnabled
        domStorageEnabled
        injectedJavaScript={`
          document.querySelectorAll('nav, footer, header').forEach(el => el.style.display = 'none');
          document.body.style.background = '#000';
          true;
        `}
        style={{ flex: 1, backgroundColor: '#000' }}
      />
      <SafeAreaView edges={['top']} className="absolute top-0 left-0 right-0">
        <Pressable
          onPress={() => router.back()}
          className="m-3 w-10 h-10 rounded-full bg-black/70 items-center justify-center">
          <X size={18} color="#FFF" />
        </Pressable>
      </SafeAreaView>
    </View>
  );
}
