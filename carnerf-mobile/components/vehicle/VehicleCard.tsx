import { Image } from 'expo-image';
import { Box, Heart, Sparkles, Star } from 'lucide-react-native';
import { Pressable, Text, View } from 'react-native';

import { Listing } from '../../lib/types';

const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://223.195.111.31:5199';
const abs = (u?: string | null) => (!u ? null : u.startsWith('http') ? u : `${BASE}${u}`);

export function VehicleCard({
  listing,
  matchScore,
  onPress,
}: {
  listing: Listing;
  matchScore?: number;
  onPress?: () => void;
}) {
  const v = listing.vehicle;
  const thumb = abs(v?.thumbnail_url);
  const has3D = v?.model_3d_status === 'ready';

  return (
    <Pressable
      onPress={onPress}
      className="bg-[#0E1117] border border-white/5 rounded-2xl overflow-hidden mb-4">
      <View className="h-44 bg-black/60 relative">
        {thumb ? (
          <Image
            source={{ uri: thumb }}
            style={{ width: '100%', height: '100%' }}
            contentFit="cover"
            transition={200}
          />
        ) : (
          <View className="flex-1 items-center justify-center">
            <Box size={56} color="#C8A96E" />
          </View>
        )}

        <View className="absolute top-3 left-3 flex-row gap-2">
          {has3D && (
            <View className="bg-black/70 border border-[#C8A96E]/40 rounded-full px-3 py-1 flex-row items-center">
              <Box size={12} color="#C8A96E" />
              <Text
                style={{ fontFamily: 'Pretendard-SemiBold' }}
                className="text-[#C8A96E] text-[11px] ml-1">
                3D
              </Text>
            </View>
          )}
          {matchScore != null && (
            <View className="bg-[#C8A96E] rounded-full px-3 py-1 flex-row items-center">
              <Sparkles size={12} color="#000" />
              <Text
                style={{ fontFamily: 'Pretendard-Bold' }}
                className="text-black text-[11px] ml-1">
                매칭 {Math.round(matchScore)}%
              </Text>
            </View>
          )}
        </View>

        <Pressable className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/70 items-center justify-center">
          <Heart size={16} color="#FFF" />
        </Pressable>
      </View>

      <View className="p-4">
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-white text-base"
          numberOfLines={1}>
          {listing.title}
        </Text>
        {v && (
          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-xs mt-1"
            numberOfLines={1}>
            {v.year} · {v.mileage.toLocaleString()}km · {v.fuel_type} · {v.region ?? '-'}
          </Text>
        )}
        <View className="flex-row items-end justify-between mt-3">
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-[#C8A96E] text-xl">
            {listing.price.toLocaleString()}
            <Text
              style={{ fontFamily: 'Pretendard-Medium' }}
              className="text-ink-mute text-sm">
              {' '}만원
            </Text>
          </Text>
          <View className="flex-row items-center">
            <Star size={12} color="#C8A96E" />
            <Text
              style={{ fontFamily: 'Pretendard-Medium' }}
              className="text-ink-soft text-[11px] ml-1">
              조회 {listing.view_count}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}
