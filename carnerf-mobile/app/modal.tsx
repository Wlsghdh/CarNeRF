import { StatusBar } from 'expo-status-bar';
import { Platform, Text, View } from 'react-native';

export default function ModalScreen() {
  return (
    <View className="flex-1 bg-bg items-center justify-center">
      <Text className="text-white text-xl font-bold">알림</Text>
      <View className="h-px w-3/4 bg-white/10 my-6" />
      <Text className="text-ink-mute">상세 내용이 여기에 표시됩니다.</Text>
      <StatusBar style={Platform.OS === 'ios' ? 'light' : 'auto'} />
    </View>
  );
}
