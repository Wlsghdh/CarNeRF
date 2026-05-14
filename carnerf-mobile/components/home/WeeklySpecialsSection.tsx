import { useRouter } from 'expo-router';
import { Flame } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Text, View } from 'react-native';

import { useWeeklySpecials } from '../../lib/hooks/useWeeklySpecials';
import { timeToNextMondayKst } from '../../lib/utils/week';
import { SpecialDealCard } from './SpecialDealCard';

export function WeeklySpecialsSection() {
  const router = useRouter();
  const { data, isLoading } = useWeeklySpecials();
  const [remain, setRemain] = useState(timeToNextMondayKst());

  useEffect(() => {
    const id = setInterval(() => setRemain(timeToNextMondayKst()), 1000);
    return () => clearInterval(id);
  }, []);

  const pad = (n: number) => String(n).padStart(2, '0');
  const hms = `${pad(remain.hours)}:${pad(remain.minutes)}:${pad(remain.seconds)}`;
  const remainLabel = remain.days > 0 ? `${remain.days}일 ${hms}` : hms;

  return (
    <View className="mt-7">
      <View className="px-5 flex-row items-end justify-between mb-1">
        <View className="flex-row items-center">
          <Flame size={18} color="#C8A96E" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-lg ml-2">
            이번 주 특가
          </Text>
          <View className="ml-2 px-2 py-0.5 bg-[#C8A96E]/15 border border-[#C8A96E]/40 rounded-full">
            <Text
              style={{ fontFamily: 'Pretendard-SemiBold' }}
              className="text-[#C8A96E] text-[10px]">
              {remainLabel}
            </Text>
          </View>
        </View>
      </View>

      <View className="px-5 mb-3">
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
          매주 월요일 0시 새 특가로 교체
        </Text>
      </View>

      {isLoading ? (
        <View className="py-10 items-center">
          <ActivityIndicator color="#C8A96E" />
        </View>
      ) : (
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={data ?? []}
          keyExtractor={(x) => `special-${x.id}`}
          contentContainerStyle={{ paddingHorizontal: 20, gap: 12 }}
          renderItem={({ item }) => (
            <SpecialDealCard
              item={item}
              onPress={() =>
                router.push({ pathname: '/vehicle/[id]', params: { id: item.id } })
              }
            />
          )}
          ListEmptyComponent={
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute px-5">
              이번 주 특가가 준비 중입니다
            </Text>
          }
        />
      )}
    </View>
  );
}
