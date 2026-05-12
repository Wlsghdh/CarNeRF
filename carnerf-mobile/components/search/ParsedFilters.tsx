import { View, Text, ScrollView } from 'react-native';

const KEY_LABEL: Record<string, string> = {
  brand: '브랜드',
  model: '모델',
  fuel_type: '연료',
  region: '지역',
  price_min: '최저가',
  price_max: '최고가',
  year_min: '연식↑',
  year_max: '연식↓',
  mileage_max: '주행↓',
  keywords: '키워드',
};

const formatValue = (k: string, v: any): string => {
  if (Array.isArray(v)) return v.join(',');
  if (typeof v === 'number') {
    if (k === 'price_min' || k === 'price_max') return `${v.toLocaleString()}만`;
    if (k === 'mileage_max') return `${v.toLocaleString()}km`;
    return v.toString();
  }
  return String(v);
};

export function ParsedFilters({ filters }: { filters: Record<string, any> }) {
  const entries = Object.entries(filters).filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0));
  if (entries.length === 0) return null;
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: 20, gap: 6, paddingVertical: 8 }}>
      {entries.map(([k, v]) => (
        <View
          key={k}
          className="bg-[#C8A96E]/15 border border-[#C8A96E]/40 rounded-full px-3 py-1.5">
          <Text style={{ fontFamily: 'Pretendard-SemiBold' }} className="text-[#C8A96E] text-[11px]">
            {KEY_LABEL[k] ?? k}: {formatValue(k, v)}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}
