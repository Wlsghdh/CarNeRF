import { useMutation, useQuery } from '@tanstack/react-query';
import * as ImagePicker from 'expo-image-picker';
import { Image } from 'expo-image';
import { Camera, ChevronLeft, ChevronRight, Cloud, Image as ImageIcon, Sparkles, Video } from 'lucide-react-native';
import { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PipelineStepper } from '../../components/pipeline/PipelineStepper';
import { Button } from '../../components/ui/Button';
import { Chip } from '../../components/ui/Chip';
import { Input } from '../../components/ui/Input';
import { listingsApi } from '../../lib/api/listings';
import { pipelineApi } from '../../lib/api/pipeline';
import { predictApi } from '../../lib/api/predict';
import { uploadApi } from '../../lib/api/upload';
import { PipelineStatus, Quality } from '../../lib/types';

const STEPS = ['기본정보', 'AI 시세', '가격', '사진', '3D 영상'];

const BRANDS = ['현대', '기아', '제네시스', '쉐보레', 'BMW', '벤츠', '아우디', '렉서스', '포르쉐'];
const FUELS = ['가솔린', '디젤', 'LPG', '하이브리드', '전기'];
const TRANS = ['자동', '수동'];
const REGIONS = ['서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산'];

export default function SellScreen() {
  const [step, setStep] = useState(0);

  const [brand, setBrand] = useState('현대');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [trim, setTrim] = useState('');
  const [mileage, setMileage] = useState('');
  const [fuel, setFuel] = useState('가솔린');
  const [transmission, setTransmission] = useState('자동');
  const [engineCc, setEngineCc] = useState('');
  const [region, setRegion] = useState('서울');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [negotiable, setNegotiable] = useState(true);

  const [images, setImages] = useState<{ uri: string; name: string; type: string }[]>([]);
  const [video, setVideo] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [quality, setQuality] = useState<Quality>('standard');
  const [jobId, setJobId] = useState<string | null>(null);

  const priceQ = useMutation({
    mutationFn: () =>
      predictApi.price({
        brand,
        model,
        year: Number(year),
        mileage: Number(mileage),
        fuel_type: fuel,
        transmission,
        engine_cc: engineCc ? Number(engineCc) : undefined,
        region,
      }),
    onError: (e) => Alert.alert('실패', String(e)),
  });

  const pickImages = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      selectionLimit: 10,
      quality: 0.8,
    });
    if (res.canceled) return;
    const next = res.assets.map((a, i) => ({
      uri: a.uri,
      name: a.fileName ?? `image_${Date.now()}_${i}.jpg`,
      type: a.mimeType ?? 'image/jpeg',
    }));
    setImages((prev) => [...prev, ...next].slice(0, 10));
  };

  const pickVideo = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      quality: 0.8,
    });
    if (res.canceled) return;
    const a = res.assets[0];
    setVideo({ uri: a.uri, name: a.fileName ?? `video_${Date.now()}.mp4`, type: a.mimeType ?? 'video/mp4' });
  };

  const submit = useMutation({
    mutationFn: async () => {
      let imageUrls: string[] = [];
      if (images.length) {
        const r = await uploadApi.images(images);
        imageUrls = r.urls;
      }
      const listing = await listingsApi.create({
        brand,
        model,
        year: Number(year),
        trim: trim || undefined,
        fuel_type: fuel,
        transmission,
        mileage: Number(mileage),
        engine_cc: engineCc ? Number(engineCc) : undefined,
        region,
        title: title || `${year} ${brand} ${model}`,
        description,
        price: Number(price),
        is_negotiable: negotiable,
        image_urls: imageUrls,
      });
      if (video) {
        const job = await pipelineApi.start({ video, vehicle_id: listing.vehicle?.id, quality });
        setJobId(job.job_id);
      }
      return listing;
    },
    onError: (e) => Alert.alert('실패', String(e)),
  });

  const pollQ = useQuery({
    queryKey: ['pipeline-status', jobId],
    queryFn: () => pipelineApi.status(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const d = q.state.data as PipelineStatus | undefined;
      return d && (d.status === 'completed' || d.status === 'failed') ? false : 3000;
    },
  });

  const canNext = useMemo(() => {
    if (step === 0) return brand && model && year && mileage && fuel && transmission;
    if (step === 2) return !!price && Number(price) > 0;
    return true;
  }, [step, brand, model, year, mileage, fuel, transmission, price]);

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-2xl">
          내 차 팔기
        </Text>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
          영상만 올리면 3D · AI 시세 · 결함 리포트 자동 생성
        </Text>
      </View>

      <View className="flex-row px-5 mb-3" style={{ gap: 4 }}>
        {STEPS.map((s, i) => (
          <View key={s} className="flex-1">
            <View
              className={`h-1.5 rounded-full ${i <= step ? 'bg-[#C8A96E]' : 'bg-white/10'}`}
            />
            <Text
              style={{ fontFamily: 'Pretendard-Medium' }}
              className={`text-[10px] mt-1 text-center ${i === step ? 'text-[#C8A96E]' : 'text-ink-mute'}`}>
              {s}
            </Text>
          </View>
        ))}
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 100 }}>
        {step === 0 && (
          <View>
            <Section title="브랜드">
              <ChipRow items={BRANDS} value={brand} onPick={setBrand} />
            </Section>
            <Input label="모델명" placeholder="예: 그랜저 IG" value={model} onChangeText={setModel} />
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Input label="연식" placeholder="2022" keyboardType="numeric" value={year} onChangeText={setYear} />
              </View>
              <View className="flex-1">
                <Input label="주행거리 (km)" placeholder="32000" keyboardType="numeric" value={mileage} onChangeText={setMileage} />
              </View>
            </View>
            <Input label="트림 (선택)" value={trim} onChangeText={setTrim} />
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Input label="배기량 (cc, 선택)" keyboardType="numeric" value={engineCc} onChangeText={setEngineCc} />
              </View>
            </View>
            <Section title="연료">
              <ChipRow items={FUELS} value={fuel} onPick={setFuel} />
            </Section>
            <Section title="변속기">
              <ChipRow items={TRANS} value={transmission} onPick={setTransmission} />
            </Section>
            <Section title="지역">
              <ChipRow items={REGIONS} value={region} onPick={setRegion} />
            </Section>
          </View>
        )}

        {step === 1 && (
          <View>
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mb-4">
              AI가 입력하신 차량 정보를 바탕으로 예상 시세를 계산합니다.
            </Text>
            <Button
              label="AI 시세 계산하기"
              leading={<Sparkles size={16} color="#000" />}
              onPress={() => priceQ.mutate()}
              loading={priceQ.isPending}
            />
            {priceQ.data && (
              <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5 mt-5">
                <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
                  예상 시세
                </Text>
                <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-3xl mt-1">
                  {priceQ.data.price_range_low.toLocaleString()} ~ {priceQ.data.price_range_high.toLocaleString()}
                  <Text className="text-ink-mute text-base"> 만원</Text>
                </Text>
                <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-2">
                  신뢰도 {Math.round(priceQ.data.confidence * 100)}%
                </Text>
                <Pressable
                  onPress={() => setPrice(String(priceQ.data.predicted_price))}
                  className="mt-4 bg-white/5 rounded-xl py-2 items-center">
                  <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-sm">
                    예측가({priceQ.data.predicted_price.toLocaleString()}만)로 설정
                  </Text>
                </Pressable>
              </View>
            )}
          </View>
        )}

        {step === 2 && (
          <View>
            <Input
              label="판매가 (만원)"
              keyboardType="numeric"
              placeholder="3500"
              value={price}
              onChangeText={setPrice}
            />
            <Input label="제목 (선택)" value={title} onChangeText={setTitle} placeholder="자동 생성됩니다" />
            <Input
              label="상세 설명"
              multiline
              numberOfLines={4}
              value={description}
              onChangeText={setDescription}
            />
            <Pressable
              onPress={() => setNegotiable((v) => !v)}
              className="flex-row items-center bg-[#0E1117] border border-white/5 rounded-2xl px-4 py-3">
              <View
                className={`w-5 h-5 rounded-md mr-3 items-center justify-center ${
                  negotiable ? 'bg-[#C8A96E]' : 'border border-white/20'
                }`}>
                {negotiable && (
                  <Text style={{ fontFamily: 'Pretendard-Bold', color: '#000', fontSize: 12 }}>✓</Text>
                )}
              </View>
              <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-white">
                가격 협상 가능
              </Text>
            </Pressable>
          </View>
        )}

        {step === 3 && (
          <View>
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mb-4">
              차량 사진 최대 10장
            </Text>
            <Pressable
              onPress={pickImages}
              className="bg-[#0E1117] border border-dashed border-white/20 rounded-2xl py-10 items-center mb-4">
              <ImageIcon size={28} color="#C8A96E" />
              <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white mt-2">
                사진 선택 ({images.length}/10)
              </Text>
            </Pressable>
            <View className="flex-row flex-wrap gap-2">
              {images.map((img, i) => (
                <View key={i} className="w-[31%] aspect-square rounded-xl overflow-hidden bg-white/5">
                  <Image source={{ uri: img.uri }} style={{ width: '100%', height: '100%' }} contentFit="cover" />
                </View>
              ))}
            </View>
          </View>
        )}

        {step === 4 && (
          <View>
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mb-4">
              차량 한 바퀴 30~60초 영상을 업로드하면 3D 모델이 자동 생성됩니다.
            </Text>
            <View className="flex-row gap-3 mb-4">
              {(['standard', 'hq', 'ultra'] as Quality[]).map((q) => (
                <Pressable
                  key={q}
                  onPress={() => setQuality(q)}
                  className={`flex-1 py-3 rounded-2xl items-center border ${
                    quality === q ? 'bg-[#C8A96E] border-[#C8A96E]' : 'bg-[#0E1117] border-white/10'
                  }`}>
                  <Text
                    style={{ fontFamily: 'Pretendard-Bold' }}
                    className={`text-sm ${quality === q ? 'text-black' : 'text-white'}`}>
                    {q === 'standard' ? '표준' : q === 'hq' ? 'HQ' : 'Ultra'}
                  </Text>
                </Pressable>
              ))}
            </View>
            <Pressable
              onPress={pickVideo}
              className="bg-[#0E1117] border border-dashed border-white/20 rounded-2xl py-10 items-center mb-4">
              <Video size={28} color="#C8A96E" />
              <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white mt-2">
                {video ? '영상 선택됨 (변경)' : '영상 선택'}
              </Text>
            </Pressable>

            <View className="flex-row gap-3">
              <View className="flex-1">
                <Button label="저장만" variant="outline" onPress={() => submit.mutate()} loading={submit.isPending} />
              </View>
              <View className="flex-1">
                <Button
                  label={video ? '등록 + 3D 생성' : '등록'}
                  leading={<Cloud size={16} color="#000" />}
                  onPress={() => submit.mutate()}
                  loading={submit.isPending}
                />
              </View>
            </View>

            {jobId && (
              <View className="mt-5">
                <PipelineStepper status={pollQ.data ?? null} />
              </View>
            )}
          </View>
        )}
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-[#0a0a0a] border-t border-white/5 px-5 pb-8 pt-3">
        <View className="flex-row gap-3">
          {step > 0 && (
            <View className="flex-1">
              <Button
                label="이전"
                variant="outline"
                onPress={() => setStep((s) => Math.max(0, s - 1))}
                leading={<ChevronLeft size={16} color="#FFF" />}
              />
            </View>
          )}
          {step < STEPS.length - 1 && (
            <View className="flex-[2]">
              <Button
                label="다음"
                onPress={() => canNext && setStep((s) => s + 1)}
                disabled={!canNext}
                leading={<ChevronRight size={16} color="#000" />}
              />
            </View>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="mb-4">
      <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-soft text-xs mb-2">
        {title}
      </Text>
      {children}
    </View>
  );
}

function ChipRow({ items, value, onPick }: { items: string[]; value: string; onPick: (v: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
      {items.map((i) => (
        <Chip key={i} label={i} active={value === i} onPress={() => onPick(i)} />
      ))}
    </ScrollView>
  );
}
