import { TrendingDown } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { PriceEstimate } from '../../lib/types';

export function PriceChart({ estimate }: { estimate: PriceEstimate }) {
  const curve = estimate.depreciation_curve ?? [];
  const max = Math.max(...curve.map((c) => c.price), estimate.predicted_price);
  const min = Math.min(...curve.map((c) => c.price), 0);
  const span = max - min || 1;

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-3">
        <View className="flex-row items-center">
          <TrendingDown size={16} color="#C8A96E" />
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-base ml-2">
            AI 가격 예측
          </Text>
        </View>
        <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-ink-mute text-[10px]">
          신뢰도 {Math.round(estimate.confidence * 100)}%
        </Text>
      </View>

      <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-3xl">
        {estimate.predicted_price.toLocaleString()}
        <Text className="text-ink-mute text-base"> 만원</Text>
      </Text>
      <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
        {estimate.price_range_low.toLocaleString()} ~ {estimate.price_range_high.toLocaleString()} 만원
      </Text>

      {curve.length > 0 && (
        <View className="mt-5">
          <View className="flex-row items-end justify-between h-32" style={{ gap: 4 }}>
            {curve.map((p, i) => {
              const h = ((p.price - min) / span) * 100;
              return (
                <View key={i} className="flex-1 items-center">
                  <View
                    style={{ height: `${Math.max(8, h)}%`, backgroundColor: '#C8A96E', opacity: 0.4 + (h / 200) }}
                    className="w-full rounded-t-lg"
                  />
                </View>
              );
            })}
          </View>
          <View className="flex-row justify-between mt-2">
            {curve.map((p, i) => (
              <Text
                key={i}
                style={{ fontFamily: 'Pretendard' }}
                className="text-ink-mute text-[10px] flex-1 text-center">
                {p.year}
              </Text>
            ))}
          </View>
          <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[10px] mt-3 text-center">
            연도별 감가상각 곡선 (LightGBM 예측)
          </Text>
        </View>
      )}
    </View>
  );
}
