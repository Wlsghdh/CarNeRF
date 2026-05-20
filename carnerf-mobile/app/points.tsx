import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Coins } from 'lucide-react-native';
import { useState } from 'react';
import { Alert, FlatList, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../components/ui/Button';
import { Chip } from '../components/ui/Chip';
import { Input } from '../components/ui/Input';
import { pointsApi } from '../lib/api/points';

const CHARGE_PRESETS = [10000, 30000, 50000, 100000];

export default function PointsScreen() {
  const qc = useQueryClient();
  const [amount, setAmount] = useState('');

  const balanceQ = useQuery({ queryKey: ['balance'], queryFn: () => pointsApi.balance() });
  const historyQ = useQuery({ queryKey: ['point-history'], queryFn: () => pointsApi.history(1) });

  const chargeM = useMutation({
    mutationFn: (a: number) => pointsApi.charge(a),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['balance'] });
      qc.invalidateQueries({ queryKey: ['point-history'] });
      setAmount('');
      Alert.alert('완료', '충전이 완료되었습니다');
    },
    onError: (e) => Alert.alert('실패', String(e)),
  });

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['bottom']}>
      <View className="px-5 pt-2 pb-3">
        <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
          <View className="flex-row items-center">
            <Coins size={18} color="#C8A96E" />
            <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-mute text-xs ml-2">
              현재 잔액
            </Text>
          </View>
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-3xl mt-2">
            {(balanceQ.data?.balance ?? 0).toLocaleString()}
            <Text className="text-ink-mute text-base"> P</Text>
          </Text>
        </View>
      </View>

      <View className="px-5">
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-sm mb-3">
          충전 (1,000 ~ 1,000,000)
        </Text>
        <View className="flex-row mb-3" style={{ gap: 8 }}>
          {CHARGE_PRESETS.map((p) => (
            <Chip
              key={p}
              label={`${p.toLocaleString()}P`}
              active={String(p) === amount}
              onPress={() => setAmount(String(p))}
            />
          ))}
        </View>
        <Input
          placeholder="직접 입력"
          keyboardType="numeric"
          value={amount}
          onChangeText={setAmount}
        />
        <Button
          label={`${amount ? Number(amount).toLocaleString() : 0}P 충전하기`}
          onPress={() => {
            const n = Number(amount);
            if (n < 1000 || n > 1_000_000) {
              Alert.alert('알림', '1,000 ~ 1,000,000 사이로 입력하세요');
              return;
            }
            chargeM.mutate(n);
          }}
          loading={chargeM.isPending}
        />
      </View>

      <Text
        style={{ fontFamily: 'Pretendard-Bold' }}
        className="text-white text-sm mx-5 mt-6 mb-2">
        이력
      </Text>
      <FlatList
        data={historyQ.data?.items ?? []}
        keyExtractor={(i) => String(i.id)}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
        renderItem={({ item }) => (
          <View className="flex-row items-center justify-between py-3 border-b border-white/5">
            <View className="flex-1">
              <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-white text-sm">
                {item.description}
              </Text>
              <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[11px] mt-0.5">
                {new Date(item.created_at).toLocaleString('ko-KR')}
              </Text>
            </View>
            <Text
              style={{ fontFamily: 'Pretendard-Bold' }}
              className={item.amount > 0 ? 'text-[#C8A96E]' : 'text-ink-mute'}>
              {item.amount > 0 ? '+' : ''}
              {item.amount.toLocaleString()}P
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-center mt-6">
            이력이 없습니다
          </Text>
        }
      />
    </SafeAreaView>
  );
}
