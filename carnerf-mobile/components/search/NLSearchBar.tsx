import { Search, Sparkles, X } from 'lucide-react-native';
import { Pressable, Text, TextInput, View } from 'react-native';

export function NLSearchBar({
  value,
  onChangeText,
  onSubmit,
  aiMode,
  onToggleAi,
  onClear,
}: {
  value: string;
  onChangeText: (v: string) => void;
  onSubmit: () => void;
  aiMode: boolean;
  onToggleAi: () => void;
  onClear: () => void;
}) {
  return (
    <View className="flex-row items-center bg-[#0E1117] border border-white/10 rounded-2xl px-3 h-12">
      {aiMode ? (
        <Sparkles size={18} color="#C8A96E" />
      ) : (
        <Search size={18} color="#9CA3AF" />
      )}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        onSubmitEditing={onSubmit}
        placeholder={aiMode ? '예: 1500만원 이하 디젤 SUV' : '차량명, 브랜드 검색'}
        placeholderTextColor="#6B7280"
        style={{ fontFamily: 'Pretendard' }}
        returnKeyType="search"
        className="flex-1 text-white ml-2 text-[14px]"
      />
      {value.length > 0 && (
        <Pressable onPress={onClear} className="mr-2">
          <X size={16} color="#9CA3AF" />
        </Pressable>
      )}
      <Pressable
        onPress={onToggleAi}
        className={`px-3 h-8 rounded-full items-center justify-center flex-row ${
          aiMode ? 'bg-[#C8A96E]' : 'bg-white/5 border border-white/10'
        }`}>
        <Sparkles size={12} color={aiMode ? '#000' : '#C8A96E'} />
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className={`text-[11px] ml-1 ${aiMode ? 'text-black' : 'text-white'}`}>
          AI
        </Text>
      </Pressable>
    </View>
  );
}
