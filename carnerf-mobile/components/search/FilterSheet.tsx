import { useState } from 'react';
import { Modal, Pressable, ScrollView, Text, View } from 'react-native';

import { ListingQuery } from '../../lib/api/listings';
import { Button } from '../ui/Button';
import { Chip } from '../ui/Chip';
import { Input } from '../ui/Input';

const BRANDS = ['전체', '현대', '기아', '제네시스', '쉐보레', 'BMW', '벤츠', '아우디', '렉서스', '포르쉐'];
const FUELS = ['전체', '가솔린', '디젤', 'LPG', '하이브리드', '전기'];
const REGIONS = ['전체', '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산'];

export function FilterSheet({
  open,
  onClose,
  initial,
  onApply,
}: {
  open: boolean;
  onClose: () => void;
  initial: ListingQuery;
  onApply: (q: ListingQuery) => void;
}) {
  const [brand, setBrand] = useState(initial.brand ?? '전체');
  const [fuel, setFuel] = useState(initial.fuel_type ?? '전체');
  const [region, setRegion] = useState(initial.region ?? '전체');
  const [priceMin, setPriceMin] = useState(initial.price_min != null ? String(initial.price_min) : '');
  const [priceMax, setPriceMax] = useState(initial.price_max != null ? String(initial.price_max) : '');
  const [yearMin, setYearMin] = useState(initial.year_min != null ? String(initial.year_min) : '');
  const [yearMax, setYearMax] = useState(initial.year_max != null ? String(initial.year_max) : '');

  const reset = () => {
    setBrand('전체');
    setFuel('전체');
    setRegion('전체');
    setPriceMin('');
    setPriceMax('');
    setYearMin('');
    setYearMax('');
  };

  const apply = () => {
    const next: ListingQuery = {
      brand: brand !== '전체' ? brand : undefined,
      fuel_type: fuel !== '전체' ? fuel : undefined,
      region: region !== '전체' ? region : undefined,
      price_min: priceMin ? Number(priceMin) : undefined,
      price_max: priceMax ? Number(priceMax) : undefined,
      year_min: yearMin ? Number(yearMin) : undefined,
      year_max: yearMax ? Number(yearMax) : undefined,
    };
    onApply(next);
    onClose();
  };

  return (
    <Modal visible={open} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View className="flex-1 bg-black">
        <View className="flex-row items-center justify-between px-5 pt-5 pb-3">
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-xl">
            필터
          </Text>
          <Pressable onPress={onClose}>
            <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-mute">
              닫기
            </Text>
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 24 }}>
          <Section title="브랜드">
            <ChipRow items={BRANDS} active={brand} onPick={setBrand} />
          </Section>
          <Section title="연료">
            <ChipRow items={FUELS} active={fuel} onPick={setFuel} />
          </Section>
          <Section title="지역">
            <ChipRow items={REGIONS} active={region} onPick={setRegion} />
          </Section>

          <Section title="가격 (만원)">
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Input placeholder="최소" keyboardType="numeric" value={priceMin} onChangeText={setPriceMin} />
              </View>
              <View className="flex-1">
                <Input placeholder="최대" keyboardType="numeric" value={priceMax} onChangeText={setPriceMax} />
              </View>
            </View>
          </Section>
          <Section title="연식">
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Input placeholder="최소 (예: 2018)" keyboardType="numeric" value={yearMin} onChangeText={setYearMin} />
              </View>
              <View className="flex-1">
                <Input placeholder="최대 (예: 2024)" keyboardType="numeric" value={yearMax} onChangeText={setYearMax} />
              </View>
            </View>
          </Section>
        </ScrollView>

        <View className="flex-row gap-3 px-5 pb-8 pt-3 border-t border-white/5">
          <View className="flex-1">
            <Button label="초기화" variant="outline" onPress={reset} />
          </View>
          <View className="flex-[2]">
            <Button label="적용하기" onPress={apply} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="mt-5">
      <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-sm mb-3">
        {title}
      </Text>
      {children}
    </View>
  );
}

function ChipRow({ items, active, onPick }: { items: string[]; active: string; onPick: (s: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
      {items.map((i) => (
        <Chip key={i} label={i} active={active === i} onPress={() => onPick(i)} />
      ))}
    </ScrollView>
  );
}
