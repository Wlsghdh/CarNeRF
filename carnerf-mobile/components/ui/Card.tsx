import { View, ViewProps } from 'react-native';

export function Card({ children, className, ...rest }: ViewProps & { className?: string }) {
  return (
    <View
      {...rest}
      className={`bg-[#0E1117] border border-white/5 rounded-2xl ${className ?? ''}`}>
      {children}
    </View>
  );
}
