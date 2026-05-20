import { FlatList } from 'react-native';

import { Sort } from '../../lib/api/listings';
import { Chip } from '../ui/Chip';

const ITEMS: { value: Sort; label: string }[] = [
  { value: 'newest', label: '최신순' },
  { value: 'price_asc', label: '낮은가격' },
  { value: 'price_desc', label: '높은가격' },
  { value: 'mileage', label: '주행거리' },
  { value: 'region_match', label: '지역순' },
];

export function SortChips({ value, onChange }: { value: Sort; onChange: (s: Sort) => void }) {
  return (
    <FlatList
      horizontal
      showsHorizontalScrollIndicator={false}
      data={ITEMS}
      keyExtractor={(i) => i.value}
      contentContainerStyle={{ paddingHorizontal: 20, gap: 8, paddingVertical: 2 }}
      renderItem={({ item }) => (
        <Chip label={item.label} active={value === item.value} onPress={() => onChange(item.value)} />
      )}
    />
  );
}
