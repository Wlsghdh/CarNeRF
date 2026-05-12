import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { ArrowRight, Bell, Box, ShieldCheck, Sparkles, TrendingUp } from 'lucide-react-native';
import { ActivityIndicator, FlatList, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Logo } from '../../components/Brand';
import { VehicleCard } from '../../components/vehicle/VehicleCard';
import { listingsApi } from '../../lib/api/listings';

export default function HomeScreen() {
  const router = useRouter();
  const { data: featured, isLoading } = useQuery({
    queryKey: ['listings', 'featured'],
    queryFn: () => listingsApi.list({ sort: 'newest', limit: 10 }),
  });

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View className="px-5 pt-2 pb-4 flex-row items-center justify-between">
          <Logo size={22} />
          <Pressable className="p-2">
            <Bell size={22} color="#E5E7EB" />
          </Pressable>
        </View>

        <Pressable
          onPress={() => router.push('/listings')}
          className="mx-5 mt-2 rounded-2xl overflow-hidden bg-[#0E1117] border border-white/5 p-6">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-[#C8A96E] text-xs tracking-widest">
            CARNERF · LUXURY 3D
          </Text>
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-2xl mt-2 leading-snug">
            영상 한 번에{'\n'}3D 중고차를 만나다
          </Text>
          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-sm mt-3 leading-relaxed">
            전용 RAG 기반 AI 요약 · 결함 탐지 · 시세 예측까지{'\n'}한 화면에서.
          </Text>
          <View className="mt-5 self-start bg-[#C8A96E] rounded-full px-5 py-3 flex-row items-center">
            <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-black mr-2">
              매물 둘러보기
            </Text>
            <ArrowRight size={16} color="#000" />
          </View>
        </Pressable>

        <View className="flex-row mx-5 mt-5 gap-3">
          <FeatureChip icon={<Box size={22} color="#C8A96E" />} label="3D 뷰어" />
          <FeatureChip icon={<ShieldCheck size={22} color="#C8A96E" />} label="AI 결함" />
          <FeatureChip icon={<TrendingUp size={22} color="#C8A96E" />} label="시세 예측" />
        </View>

        <View className="px-5 mt-8 mb-3 flex-row items-end justify-between">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg">
            추천 매물
          </Text>
          <Pressable onPress={() => router.push('/listings')} className="flex-row items-center">
            <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-[#C8A96E] text-xs">
              전체보기
            </Text>
            <ArrowRight size={12} color="#C8A96E" />
          </Pressable>
        </View>

        {isLoading ? (
          <View className="px-5 py-10 items-center">
            <ActivityIndicator color="#C8A96E" />
          </View>
        ) : (
          <FlatList
            horizontal
            showsHorizontalScrollIndicator={false}
            data={featured ?? []}
            keyExtractor={(l) => String(l.id)}
            contentContainerStyle={{ paddingHorizontal: 20, gap: 12 }}
            renderItem={({ item }) => (
              <View style={{ width: 280 }}>
                <VehicleCard
                  listing={item}
                  onPress={() => router.push({ pathname: '/vehicle/[id]', params: { id: item.id } })}
                />
              </View>
            )}
            ListEmptyComponent={
              <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute px-5">
                매물이 아직 없습니다
              </Text>
            }
          />
        )}

        <View className="px-5 mt-8">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg mb-3">
            CarNeRF 작동 방식
          </Text>
          <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
            <Step n="1" t="영상 촬영" d="차 한 바퀴 30~60초 영상" />
            <View className="h-px bg-white/5 my-3" />
            <Step n="2" t="자동 3D 모델링" d="COLMAP → Gaussian Splatting 60K iter" />
            <View className="h-px bg-white/5 my-3" />
            <Step n="3" t="AI 분석" d="결함 탐지 · 시세 예측 · RAG 요약" />
          </View>
        </View>

        <View className="h-12" />
      </ScrollView>
    </SafeAreaView>
  );
}

function FeatureChip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <View className="flex-1 bg-[#0E1117] border border-white/5 rounded-2xl py-4 items-center">
      {icon}
      <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-ink-soft text-xs mt-2">
        {label}
      </Text>
    </View>
  );
}

function Step({ n, t, d }: { n: string; t: string; d: string }) {
  return (
    <View className="flex-row items-start">
      <View className="w-7 h-7 rounded-full bg-[#C8A96E] items-center justify-center mr-3">
        <Text style={{ fontFamily: 'Pretendard-Bold', color: '#000' }}>{n}</Text>
      </View>
      <View className="flex-1">
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white">
          {t}
        </Text>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-0.5">
          {d}
        </Text>
      </View>
      <Sparkles size={14} color="#C8A96E" />
    </View>
  );
}
