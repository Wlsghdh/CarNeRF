import { Text, View } from 'react-native';

export function Logo({ size = 24 }: { size?: number }) {
  return (
    <View className="flex-row items-center">
      <Text
        style={{ fontFamily: 'Pretendard-Bold', fontSize: size, letterSpacing: -0.5, color: '#FFFFFF' }}>
        Car
      </Text>
      <Text
        style={{ fontFamily: 'Pretendard-Bold', fontSize: size, letterSpacing: -0.5, color: '#C8A96E' }}>
        NeRF
      </Text>
    </View>
  );
}
