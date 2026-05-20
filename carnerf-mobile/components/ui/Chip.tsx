import { Pressable, Text } from 'react-native';

export function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`px-4 h-9 rounded-full items-center justify-center border ${
        active ? 'bg-[#C8A96E] border-[#C8A96E]' : 'bg-[#0E1117] border-white/10'
      }`}>
      <Text
        style={{ fontFamily: 'Pretendard-SemiBold' }}
        className={`text-xs ${active ? 'text-black' : 'text-ink-soft'}`}>
        {label}
      </Text>
    </Pressable>
  );
}
