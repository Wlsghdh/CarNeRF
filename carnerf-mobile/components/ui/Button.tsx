import { ActivityIndicator, Pressable, Text, View } from 'react-native';

type Variant = 'primary' | 'secondary' | 'ghost' | 'outline';

const variants: Record<Variant, { bg: string; text: string; border?: string }> = {
  primary: { bg: 'bg-[#C8A96E]', text: 'text-black' },
  secondary: { bg: 'bg-white', text: 'text-black' },
  ghost: { bg: 'bg-transparent', text: 'text-white' },
  outline: { bg: 'bg-transparent', text: 'text-white', border: 'border border-white/10' },
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  loading,
  disabled,
  leading,
  className,
}: {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  leading?: React.ReactNode;
  className?: string;
}) {
  const v = variants[variant];
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      className={`flex-row items-center justify-center py-3 px-5 rounded-2xl ${v.bg} ${v.border ?? ''} ${
        disabled ? 'opacity-50' : ''
      } ${className ?? ''}`}>
      {loading ? (
        <ActivityIndicator color={variant === 'primary' || variant === 'secondary' ? '#000' : '#C8A96E'} />
      ) : (
        <View className="flex-row items-center">
          {leading}
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className={`text-[15px] ${v.text} ${leading ? 'ml-2' : ''}`}>
            {label}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
