import { Image } from 'expo-image';
import { Box, Flame, Star } from 'lucide-react-native';
import { Pressable, Text, View } from 'react-native';

import type { SpecialListing } from '../../lib/hooks/useWeeklySpecials';

const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://223.195.111.31:5199';
const abs = (u?: string | null) => (!u ? null : u.startsWith('http') ? u : `${BASE}${u}`);

export function SpecialDealCard({
  item,
  onPress,
}: {
  item: SpecialListing;
  onPress?: () => void;
}) {
  const v = item.vehicle;
  const thumb = abs(v?.thumbnail_url);
  const pct = Math.round(item.discount_rate * 100);

  return (
    <Pressable
      onPress={onPress}
      className="bg-[#0E1117] border border-white/5 rounded-2xl overflow-hidden"
      style={{ width: 280 }}>
      <View className="h-40 bg-black/60 relative">
        {thumb ? (
          <Image
            source={{ uri: thumb }}
            style={{ width: '100%', height: '100%' }}
            contentFit="cover"
            transition={200}
          />
        ) : (
          <View className="flex-1 items-center justify-center">
            <Box size={48} color="#C8A96E" />
          </View>
        )}

        <View className="absolute top-3 left-3 bg-[#C8A96E] rounded-full px-3 py-1 flex-row items-center">
          <Flame size={12} color="#000" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-black text-[11px] ml-1">
            -{pct}%
          </Text>
        </View>

        <View className="absolute top-3 right-3 bg-black/70 border border-[#C8A96E]/40 rounded-full px-2.5 py-1">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-[#C8A96E] text-[10px]">
            이번 주 특가
          </Text>
        </View>
      </View>

      <View className="p-4">
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-white text-sm"
          numberOfLines={1}>
          {item.title}
        </Text>
        {v && (
          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-[11px] mt-1"
            numberOfLines={1}>
            {v.year} · {v.mileage.toLocaleString()}km · {v.fuel_type}
          </Text>
        )}

        <View className="mt-3 flex-row items-end justify-between">
          <View>
            <Text
              style={{
                fontFamily: 'Pretendard',
                textDecorationLine: 'line-through',
              }}
              className="text-ink-mute text-xs">
              {item.original_price.toLocaleString()}만
            </Text>
            <Text
              style={{ fontFamily: 'Pretendard-Bold' }}
              className="text-[#C8A96E] text-xl mt-0.5">
              {item.special_price.toLocaleString()}
              <Text
                style={{ fontFamily: 'Pretendard-Medium' }}
                className="text-ink-mute text-xs">
                {' '}만원
              </Text>
            </Text>
          </View>
          <View className="flex-row items-center mb-1">
            <Star size={12} color="#C8A96E" />
            <Text
              style={{ fontFamily: 'Pretendard-Medium' }}
              className="text-ink-soft text-[11px] ml-1">
              조회 {item.view_count}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}
