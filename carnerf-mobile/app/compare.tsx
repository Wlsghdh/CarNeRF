import { useMutation } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react-native';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { searchApi } from '../lib/api/search';
import { Listing } from '../lib/types';

export default function CompareScreen() {
  const [idInput, setIdInput] = useState('');
  const [ids, setIds] = useState<number[]>([]);
  const [data, setData] = useState<{ items: Listing[]; tags: Record<string, number> } | null>(null);

  const compareM = useMutation({
    mutationFn: (xs: number[]) => searchApi.compare(xs),
    onSuccess: (res) => setData(res),
    onError: (e) => Alert.alert('실패', String(e)),
  });

  const add = () => {
    const n = Number(idInput);
    if (!Number.isFinite(n) || n <= 0) return;
    if (ids.includes(n)) return;
    if (ids.length >= 4) {
      Alert.alert('알림', '최대 4대까지 비교 가능합니다');
      return;
    }
    const next = [...ids, n];
    setIds(next);
    setIdInput('');
    compareM.mutate(next);
  };

  const remove = (n: number) => {
    const next = ids.filter((x) => x !== n);
    setIds(next);
    if (next.length === 0) setData(null);
    else compareM.mutate(next);
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['bottom']}>
      <ScrollView contentContainerStyle={{ padding: 20 }}>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mb-3">
          차량 ID로 추가 (최대 4대)
        </Text>
        <View className="flex-row gap-2">
          <View className="flex-1">
            <Input placeholder="예: 13" keyboardType="numeric" value={idInput} onChangeText={setIdInput} />
          </View>
          <Button label="추가" leading={<Plus size={14} color="#000" />} onPress={add} />
        </View>

        <View className="flex-row flex-wrap gap-2 mt-2">
          {ids.map((n) => (
            <Pressable
              key={n}
              onPress={() => remove(n)}
              className="bg-[#C8A96E]/15 border border-[#C8A96E]/40 rounded-full px-3 py-1.5 flex-row items-center">
              <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-xs">
                #{n}
              </Text>
              <X size={12} color="#C8A96E" />
            </Pressable>
          ))}
        </View>

        {data?.items && data.items.length > 0 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mt-5">
            <View className="flex-row gap-3">
              {data.items.map((l) => (
                <View
                  key={l.id}
                  className="w-60 bg-[#0E1117] border border-white/5 rounded-2xl p-4">
                  <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white" numberOfLines={2}>
                    {l.title}
                  </Text>
                  {l.vehicle && (
                    <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
                      {l.vehicle.year} · {l.vehicle.mileage.toLocaleString()}km
                    </Text>
                  )}
                  <Text
                    style={{ fontFamily: 'Pretendard-Bold' }}
                    className="text-[#C8A96E] text-xl mt-3">
                    {l.price.toLocaleString()}
                    <Text className="text-ink-mute text-xs"> 만원</Text>
                  </Text>
                  <View className="flex-row flex-wrap gap-1 mt-3">
                    {Object.entries(data.tags ?? {}).map(([k, v]) =>
                      v === l.id ? (
                        <View key={k} className="bg-[#C8A96E] rounded-full px-2 py-0.5">
                          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-black text-[10px]">
                            {k === 'lowest_price'
                              ? '최저가'
                              : k === 'lowest_mileage'
                                ? '최소 주행'
                                : k === 'best_score'
                                  ? '최고 점수'
                                  : k}
                          </Text>
                        </View>
                      ) : null,
                    )}
                  </View>
                </View>
              ))}
            </View>
          </ScrollView>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
