import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { SlidersHorizontal, Sparkles } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { NLSearchBar } from '../../components/search/NLSearchBar';
import { ParsedFilters } from '../../components/search/ParsedFilters';
import { SortChips } from '../../components/search/SortChips';
import { FilterSheet } from '../../components/search/FilterSheet';
import { Chip } from '../../components/ui/Chip';
import { VehicleCard } from '../../components/vehicle/VehicleCard';
import { listingsApi, ListingQuery, Sort } from '../../lib/api/listings';
import { searchApi } from '../../lib/api/search';
import { Listing } from '../../lib/types';

const PAGE = 20;

const AI_SUGGESTIONS = [
  '1500만원 이하 디젤 SUV',
  '주행 5만 이하 그랜저',
  '5년 이내 하이브리드',
  '서울 BMW 4천 이하',
];

export default function ListingsScreen() {
  const router = useRouter();
  const [aiMode, setAiMode] = useState(false);
  const [query, setQuery] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [sort, setSort] = useState<Sort>('newest');
  const [filters, setFilters] = useState<ListingQuery>({});
  const [filterOpen, setFilterOpen] = useState(false);
  const [aiResult, setAiResult] = useState<{ parsed: Record<string, any>; matches: Map<number, number> } | null>(null);

  const baseQuery: ListingQuery = useMemo(
    () => ({ ...filters, sort, search: appliedSearch || undefined, limit: PAGE }),
    [filters, sort, appliedSearch],
  );

  const listingsQ = useInfiniteQuery({
    queryKey: ['listings', baseQuery],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => listingsApi.list({ ...baseQuery, page: pageParam as number }),
    getNextPageParam: (last, all) => (last.length < PAGE ? undefined : all.length + 1),
    enabled: !aiMode || aiResult !== null,
  });

  const aiSearch = useMutation({
    mutationFn: (q: string) => searchApi.aiRecommend(q),
    onSuccess: (data) => {
      const m = new Map<number, number>();
      data.listings.forEach((l) => m.set(l.id, l.match_score));
      setAiResult({ parsed: data.parsed_filters, matches: m });
    },
  });

  const popularQ = useQuery({
    queryKey: ['popular-keywords'],
    queryFn: () => searchApi.popularKeywords(),
  });

  const submitSearch = () => {
    if (aiMode) {
      if (query.trim()) aiSearch.mutate(query.trim());
    } else {
      setAppliedSearch(query.trim());
    }
  };

  const clearSearch = () => {
    setQuery('');
    setAppliedSearch('');
    setAiResult(null);
  };

  const items: { listing: Listing; matchScore?: number }[] = useMemo(() => {
    const all = listingsQ.data?.pages.flat() ?? [];
    if (aiMode && aiResult) {
      return all
        .filter((l) => aiResult.matches.has(l.id))
        .map((l) => ({ listing: l, matchScore: aiResult.matches.get(l.id) }))
        .sort((a, b) => (b.matchScore ?? 0) - (a.matchScore ?? 0));
    }
    return all.map((l) => ({ listing: l }));
  }, [listingsQ.data, aiMode, aiResult]);

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="px-5 pt-2 pb-3 flex-row items-end justify-between">
        <View>
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-2xl">
            매물 찾기
          </Text>
          <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-1">
            3D 검수가 완료된 프리미엄 중고차
          </Text>
        </View>
        <Pressable
          onPress={() => setFilterOpen(true)}
          className="w-10 h-10 rounded-full bg-[#0E1117] border border-white/10 items-center justify-center">
          <SlidersHorizontal size={18} color="#C8A96E" />
        </Pressable>
      </View>

      <View className="px-5 pb-2">
        <NLSearchBar
          value={query}
          onChangeText={setQuery}
          onSubmit={submitSearch}
          aiMode={aiMode}
          onToggleAi={() => {
            setAiMode((m) => !m);
            setAiResult(null);
          }}
          onClear={clearSearch}
        />
      </View>

      {aiMode && !aiResult && (
        <View className="mt-3">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-ink-mute text-[11px] px-5 mb-2 tracking-wide">
            AI 추천 검색
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 20, gap: 8, paddingVertical: 2 }}>
            {AI_SUGGESTIONS.map((s) => (
              <Pressable
                key={s}
                onPress={() => {
                  setQuery(s);
                  aiSearch.mutate(s);
                }}
                className="px-3 h-8 rounded-full bg-[#C8A96E]/15 border border-[#C8A96E]/40 flex-row items-center">
                <Sparkles size={12} color="#C8A96E" />
                <Text
                  style={{ fontFamily: 'Pretendard-SemiBold' }}
                  className="text-[#C8A96E] text-[11px] ml-1">
                  {s}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}

      {!aiMode && popularQ.data && popularQ.data.keywords.length > 0 && (
        <View className="mt-3">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-ink-mute text-[11px] px-5 mb-2 tracking-wide">
            인기 검색어
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 20, gap: 8, paddingVertical: 2 }}>
            {popularQ.data.keywords.map((k) => (
              <Chip
                key={k.text}
                label={`# ${k.text}`}
                active={appliedSearch === k.text}
                onPress={() => {
                  setQuery(k.text);
                  setAppliedSearch(k.text);
                }}
              />
            ))}
          </ScrollView>
        </View>
      )}

      {aiMode && aiResult && (
        <View className="mt-3">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-ink-mute text-[11px] px-5 mb-2 tracking-wide">
            AI가 이해한 조건
          </Text>
          <ParsedFilters filters={aiResult.parsed} />
        </View>
      )}

      <View className="h-px bg-white/5 mx-5 my-3" />

      <View>
        <Text
          style={{ fontFamily: 'Pretendard-SemiBold' }}
          className="text-ink-mute text-[11px] px-5 mb-2 tracking-wide">
          정렬
        </Text>
        <SortChips value={sort} onChange={setSort} />
      </View>

      <FlatList
        data={items}
        keyExtractor={(x) => String(x.listing.id)}
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 12, paddingBottom: 24 }}
        onEndReached={() => listingsQ.hasNextPage && !listingsQ.isFetchingNextPage && listingsQ.fetchNextPage()}
        onEndReachedThreshold={0.4}
        renderItem={({ item }) => (
          <VehicleCard
            listing={item.listing}
            matchScore={item.matchScore}
            onPress={() => router.push({ pathname: '/vehicle/[id]', params: { id: item.listing.id } })}
          />
        )}
        ListEmptyComponent={
          listingsQ.isLoading || aiSearch.isPending ? (
            <View className="py-12 items-center">
              <ActivityIndicator color="#C8A96E" />
            </View>
          ) : (
            <Text
              style={{ fontFamily: 'Pretendard' }}
              className="text-ink-mute text-center mt-12">
              {aiMode ? 'AI 검색 결과가 없습니다' : '매물이 없습니다'}
            </Text>
          )
        }
        ListFooterComponent={
          listingsQ.isFetchingNextPage ? (
            <View className="py-6 items-center">
              <ActivityIndicator color="#C8A96E" />
            </View>
          ) : null
        }
      />

      <FilterSheet
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        initial={filters}
        onApply={setFilters}
      />
    </SafeAreaView>
  );
}
