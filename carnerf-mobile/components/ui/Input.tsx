import { TextInput, TextInputProps, View, Text } from 'react-native';

export function Input({
  label,
  error,
  className,
  ...props
}: TextInputProps & { label?: string; error?: string; className?: string }) {
  return (
    <View className={`mb-4 ${className ?? ''}`}>
      {label ? (
        <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-soft text-xs mb-2">
          {label}
        </Text>
      ) : null}
      <TextInput
        placeholderTextColor="#6B7280"
        style={{ fontFamily: 'Pretendard' }}
        className={`bg-white/5 border ${
          error ? 'border-red-500/60' : 'border-white/10'
        } rounded-2xl px-4 py-3 text-white text-[15px]`}
        {...props}
      />
      {error ? (
        <Text style={{ fontFamily: 'Pretendard' }} className="text-red-400 text-xs mt-1">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
