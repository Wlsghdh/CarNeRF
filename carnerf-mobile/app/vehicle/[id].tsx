import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Box, ChevronLeft, Heart, MessageCircle, Share2, Star } from 'lucide-react-native';
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AISummary } from '../../components/vehicle/AISummary';
import { DefectBars } from '../../components/vehicle/DefectBars';
import { PriceChart } from '../../components/vehicle/PriceChart';
import { Button } from '../../components/ui/Button';
import { aiApi } from '../../lib/api/ai';
import { defectApi } from '../../lib/api/defect';
import { listingsApi } from '../../lib/api/listings';
import { marketApi } from '../../lib/api/market';
import { predictApi } from '../../lib/api/predict';
import { reviewsApi } from '../../lib/api/reviews';
import { wishlistApi } from '../../lib/api/wishlist';

const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://223.195.111.31:5199';
const abs = (u?: string | null) => (!u ? null : u.startsWith('http') ? u : `${BASE}${u}`);

export default function VehicleDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const listingId = Number(id);
  const router = useRouter();
  const qc = useQueryClient();

  const listingQ = useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => listingsApi.get(listingId),
    enabled: Number.isFinite(listingId),
  });
  const vehicleId = listingQ.data?.vehicle_id;

  const summaryQ = useQuery({
    queryKey: ['ai-summary', vehicleId],
    queryFn: () => aiApi.vehicleSummary(vehicleId!),
    enabled: !!vehicleId,
  });
  const defectQ = useQuery({
    queryKey: ['defect', vehicleId],
    queryFn: () => defectApi.byVehicle(vehicleId!),
    enabled: !!vehicleId,
  });
  const marketQ = useQuery({
    queryKey: ['market', vehicleId],
    queryFn: () => marketApi.price(vehicleId!),
    enabled: !!vehicleId,
  });
  const predictQ = useQuery({
    queryKey: ['predict', vehicleId],
    queryFn: () => predictApi.byVehicle(vehicleId!),
    enabled: !!vehicleId,
  });
  const reviewsQ = useQuery({
    queryKey: ['reviews', vehicleId],
    queryFn: () => reviewsApi.forVehicle(vehicleId!, 1, 5),
    enabled: !!vehicleId,
  });
  const wishCheckQ = useQuery({
    queryKey: ['wish-check', vehicleId],
    queryFn: () => wishlistApi.check(vehicleId!),
    enabled: !!vehicleId,
  });
  const toggleWish = useMutation({
    mutationFn: () => wishlistApi.toggle(vehicleId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wish-check', vehicleId] }),
    onError: (e) => Alert.alert('실패', String(e)),
  });

  if (!Number.isFinite(listingId) || listingQ.isLoading) {
    return (
      <View className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator color="#C8A96E" />
      </View>
    );
  }
  if (!listingQ.data) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute">매물을 찾을 수 없습니다</Text>
      </SafeAreaView>
    );
  }

  const l = listingQ.data;
  const v = l.vehicle;
  const thumb = abs(v?.thumbnail_url);
  const has3D = v?.model_3d_status === 'ready';
  const wished = wishCheckQ.data?.wishlisted ?? false;

  return (
    <View className="flex-1 bg-bg">
      <ScrollView contentContainerStyle={{ paddingBottom: 100 }}>
        <View className="h-72 bg-[#0a0a0a] relative">
          {thumb ? (
            <Image source={{ uri: thumb }} style={{ width: '100%', height: '100%' }} contentFit="cover" />
          ) : (
            <View className="flex-1 items-center justify-center">
              <Box size={80} color="#C8A96E" />
            </View>
          )}

          <SafeAreaView edges={['top']} className="absolute top-0 left-0 right-0">
            <View className="flex-row items-center justify-between px-3 py-2">
              <Pressable
                onPress={() => router.back()}
                className="w-10 h-10 rounded-full bg-black/60 items-center justify-center">
                <ChevronLeft size={20} color="#FFF" />
              </Pressable>
              <View className="flex-row gap-2">
                <Pressable
                  onPress={() => toggleWish.mutate()}
                  className="w-10 h-10 rounded-full bg-black/60 items-center justify-center">
                  <Heart size={18} color={wished ? '#C8A96E' : '#FFF'} fill={wished ? '#C8A96E' : 'none'} />
                </Pressable>
                <Pressable className="w-10 h-10 rounded-full bg-black/60 items-center justify-center">
                  <Share2 size={18} color="#FFF" />
                </Pressable>
              </View>
            </View>
          </SafeAreaView>

          {has3D && (
            <Pressable
              onPress={() => router.push({ pathname: '/viewer/[id]', params: { id: String(vehicleId) } })}
              className="absolute bottom-4 left-4 right-4 bg-[#C8A96E] rounded-2xl py-3 flex-row items-center justify-center">
              <Box size={18} color="#000" />
              <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-black ml-2">
                3D 모델 보기
              </Text>
            </Pressable>
          )}
        </View>

        <View className="px-5 mt-5">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-2xl leading-tight">
            {l.title}
          </Text>
          {v && (
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mt-2">
              {v.brand} {v.model} {v.trim ?? ''} · {v.year} · {v.mileage.toLocaleString()}km
            </Text>
          )}
          <View className="flex-row items-end mt-4">
            <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-3xl">
              {l.price.toLocaleString()}
            </Text>
            <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-mute text-base ml-1 mb-0.5">
              만원
            </Text>
            {l.is_negotiable && (
              <View className="ml-3 mb-1 px-2 py-0.5 bg-white/5 rounded-full">
                <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-ink-soft text-[10px]">
                  네고 가능
                </Text>
              </View>
            )}
          </View>
          {l.description ? (
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-soft text-sm mt-4 leading-relaxed">
              {l.description}
            </Text>
          ) : null}
        </View>

        <View className="px-5 mt-6">
          <SectionTitle title="AI 분석" />
          {summaryQ.data ? <AISummary summary={summaryQ.data} /> : <Loader />}

          <View className="h-3" />
          {defectQ.data ? <DefectBars report={defectQ.data} /> : null}

          <View className="h-3" />
          {predictQ.data ? <PriceChart estimate={predictQ.data} /> : null}

          {marketQ.data ? (
            <>
              <View className="h-3" />
              <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
                <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white">
                  시세 비교
                </Text>
                <View className="flex-row mt-3 gap-3">
                  <PriceCell label="내부 평균" value={marketQ.data.internal_average} />
                  {marketQ.data.external_average ? (
                    <PriceCell label="외부 평균" value={marketQ.data.external_average} />
                  ) : null}
                </View>
              </View>
            </>
          ) : null}
        </View>

        <View className="px-5 mt-6">
          <SectionTitle title="구매자 후기" />
          <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
            {reviewsQ.data?.items?.length ? (
              reviewsQ.data.items.map((r, i) => (
                <View key={r.id} className={i > 0 ? 'mt-4 pt-4 border-t border-white/5' : ''}>
                  <View className="flex-row items-center mb-1">
                    {Array.from({ length: 5 }).map((_, idx) => (
                      <Star
                        key={idx}
                        size={12}
                        color={idx < r.rating ? '#C8A96E' : '#3a3a3a'}
                        fill={idx < r.rating ? '#C8A96E' : 'transparent'}
                      />
                    ))}
                  </View>
                  <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-soft text-sm">
                    {r.content}
                  </Text>
                </View>
              ))
            ) : (
              <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
                아직 후기가 없습니다
              </Text>
            )}
          </View>
        </View>
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-[#0a0a0a] border-t border-white/5 px-5 pb-8 pt-3">
        <View className="flex-row gap-3">
          <Button
            label={wished ? '찜 해제' : '찜하기'}
            variant="outline"
            onPress={() => toggleWish.mutate()}
            leading={<Heart size={16} color={wished ? '#C8A96E' : '#FFF'} />}
            className="flex-1"
          />
          <View style={{ flex: 2 }}>
            <Button label="판매자 문의" leading={<MessageCircle size={16} color="#000" />} />
          </View>
        </View>
      </View>
    </View>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg mb-3">
      {title}
    </Text>
  );
}

function PriceCell({ label, value }: { label: string; value: number }) {
  return (
    <View className="flex-1 bg-white/5 rounded-xl p-3">
      <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[11px]">
        {label}
      </Text>
      <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg mt-1">
        {value.toLocaleString()}
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
          {' '}만원
        </Text>
      </Text>
    </View>
  );
}

function Loader() {
  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl py-10 items-center">
      <ActivityIndicator color="#C8A96E" />
    </View>
  );
}
