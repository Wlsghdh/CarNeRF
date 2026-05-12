import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { ChevronRight, Coins, Heart, LogOut, Receipt, Settings, ShieldCheck, Star, User as UserIcon } from 'lucide-react-native';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { authApi } from '../../lib/api/auth';
import { pointsApi } from '../../lib/api/points';
import { wishlistApi } from '../../lib/api/wishlist';
import { useAuth } from '../../lib/store/auth';

export default function MypageScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const balanceQ = useQuery({
    queryKey: ['balance'],
    queryFn: () => pointsApi.balance(),
    enabled: !!user,
  });
  const myListingsQ = useQuery({
    queryKey: ['my-listings'],
    queryFn: () => authApi.myListings(),
    enabled: !!user,
  });
  const wishQ = useQuery({
    queryKey: ['wishlist'],
    queryFn: () => wishlistApi.list(),
    enabled: !!user,
  });

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <ScrollView>
        <View className="px-5 pt-2 pb-5">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-2xl">
            마이
          </Text>
        </View>

        <View className="mx-5 rounded-2xl bg-[#0E1117] border border-white/5 p-5 flex-row items-center">
          <View className="w-14 h-14 rounded-full bg-[#C8A96E] items-center justify-center">
            <UserIcon size={26} color="#000" />
          </View>
          <View className="ml-4 flex-1">
            <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-lg">
              {user?.username ?? '게스트'}
            </Text>
            <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
              {user ? user.email : '로그인하고 모든 기능을 사용해 보세요'}
            </Text>
          </View>
          {user ? (
            <Pressable onPress={logout} className="px-3 py-2 bg-white/5 rounded-full">
              <LogOut size={14} color="#9CA3AF" />
            </Pressable>
          ) : (
            <Pressable onPress={() => router.push('/login')} className="bg-[#C8A96E] rounded-full px-4 py-2">
              <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-black text-xs">
                로그인
              </Text>
            </Pressable>
          )}
        </View>

        <View className="mx-5 mt-4 flex-row gap-3">
          <Stat label="포인트" value={`${(balanceQ.data?.balance ?? 0).toLocaleString()} P`} onPress={() => router.push('/points')} />
          <Stat label="찜한 매물" value={`${wishQ.data?.length ?? 0}`} />
          <Stat label="내 매물" value={`${myListingsQ.data?.length ?? 0}`} />
        </View>

        <View className="mt-6 bg-[#0E1117] mx-5 rounded-2xl border border-white/5 overflow-hidden">
          <MenuRow icon={<Heart size={20} color="#C8A96E" />} label="찜한 매물" />
          <MenuRow icon={<Receipt size={20} color="#C8A96E" />} label="거래 내역" />
          <MenuRow icon={<Coins size={20} color="#C8A96E" />} label="포인트 충전/사용" onPress={() => router.push('/points')} />
          <MenuRow icon={<ShieldCheck size={20} color="#C8A96E" />} label="판매자 인증" />
          <MenuRow icon={<Star size={20} color="#C8A96E" />} label="내 리뷰" />
          <MenuRow icon={<Settings size={20} color="#C8A96E" />} label="설정" last />
        </View>

        <Pressable
          onPress={() => router.push('/compare')}
          className="mx-5 mt-4 bg-[#0E1117] border border-white/5 rounded-2xl p-4 flex-row items-center">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white flex-1">
            차량 비교하기 (최대 4대)
          </Text>
          <ChevronRight size={18} color="#9CA3AF" />
        </Pressable>

        <View className="h-12" />
      </ScrollView>
    </SafeAreaView>
  );
}

function Stat({ label, value, onPress }: { label: string; value: string; onPress?: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-1 bg-[#0E1117] border border-white/5 rounded-2xl py-4 items-center">
      <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-base">
        {value}
      </Text>
      <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
        {label}
      </Text>
    </Pressable>
  );
}

function MenuRow({
  icon,
  label,
  onPress,
  last,
}: {
  icon: React.ReactNode;
  label: string;
  onPress?: () => void;
  last?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`flex-row items-center px-5 py-4 ${last ? '' : 'border-b border-white/5'}`}>
      {icon}
      <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-soft text-base ml-3 flex-1">
        {label}
      </Text>
      <ChevronRight size={18} color="#6B7280" />
    </Pressable>
  );
}
