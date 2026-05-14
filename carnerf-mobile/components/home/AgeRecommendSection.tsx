import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { ArrowRight } from 'lucide-react-native';
import { useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, ScrollView, Text, View } from 'react-native';

import { ListingQuery, listingsApi } from '../../lib/api/listings';
import { Chip } from '../ui/Chip';
import { VehicleCard } from '../vehicle/VehicleCard';

type AgeGroup = '20s' | '30s' | '40s' | '50s' | '60s+';

const AGE_TABS: { key: AgeGroup; label: string }[] = [
  { key: '20s', label: '20대' },
  { key: '30s', label: '30대' },
  { key: '40s', label: '40대' },
  { key: '50s', label: '50대' },
  { key: '60s+', label: '60대+' },
];

// TODO: backend age-recommend endpoint — 현재는 클라이언트 룰로 필터 매핑
const AGE_FILTER: Record<AgeGroup, ListingQuery> = {
  '20s': { price_max: 2000, sort: 'newest', limit: 10 },
  '30s': { price_min: 2000, price_max: 4000, fuel_type: '하이브리드', limit: 10 },
  '40s': { price_min: 3000, price_max: 6000, brand: '제네시스', limit: 10 },
  '50s': { price_min: 4000, fuel_type: '가솔린', limit: 10 },
  '60s+': { price_max: 3000, fuel_type: '가솔린', limit: 10 },
};

export function AgeRecommendSection() {
  const router = useRouter();
  const [age, setAge] = useState<AgeGroup>('30s');

  const { data, isLoading } = useQuery({
    queryKey: ['age-recommend', age],
    queryFn: () => listingsApi.list(AGE_FILTER[age]),
  });

  const currentLabel = AGE_TABS.find((t) => t.key === age)?.label ?? '';

  return (
    <View>
      <View className="px-5 mt-8 mb-1 flex-row items-end justify-between">
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg">
          연령대별 인기 차량
        </Text>
        <Pressable onPress={() => router.push('/listings')} className="flex-row items-center">
          <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-[#C8A96E] text-xs">
            전체보기
          </Text>
          <ArrowRight size={12} color="#C8A96E" />
        </Pressable>
      </View>
      <Text
        style={{ fontFamily: 'Pretendard' }}
        className="text-ink-mute text-xs px-5 mb-3">
        또래가 가장 많이 찾은 매물
      </Text>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 20, gap: 8, paddingBottom: 12 }}>
        {AGE_TABS.map((t) => (
          <Chip key={t.key} label={t.label} active={age === t.key} onPress={() => setAge(t.key)} />
        ))}
      </ScrollView>

      {isLoading ? (
        <View className="px-5 py-10 items-center">
          <ActivityIndicator color="#C8A96E" />
        </View>
      ) : (
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={data ?? []}
          keyExtractor={(l) => `age-${age}-${l.id}`}
          contentContainerStyle={{ paddingHorizontal: 20, gap: 12 }}
          renderItem={({ item }) => (
            <View style={{ width: 280 }}>
              <View className="relative">
                <VehicleCard
                  listing={item}
                  onPress={() =>
                    router.push({ pathname: '/vehicle/[id]', params: { id: item.id } })
                  }
                />
                <View
                  style={{ pointerEvents: 'none' }}
                  className="absolute top-3 left-3 bg-[#C8A96E] rounded-full px-3 py-1 z-10">
                  <Text
                    style={{ fontFamily: 'Pretendard-Bold' }}
                    className="text-black text-[11px]">
                    {currentLabel} 추천
                  </Text>
                </View>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute px-5">
              해당 연령대 추천 매물이 없습니다
            </Text>
          }
        />
      )}
    </View>
  );
}
