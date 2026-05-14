import { AlertTriangle, Droplets, Info, ShieldCheck, Users } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { Vehicle } from '../../lib/types';

const BODY_TYPE_LABEL: Record<string, string> = {
  sedan: '세단',
  suv: 'SUV',
  hatchback: '해치백',
  coupe: '쿠페',
  wagon: '왜건',
};

function fmtDate(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(
    d.getDate(),
  ).padStart(2, '0')}`;
}

export function VehicleSpecCard({ vehicle }: { vehicle?: Vehicle }) {
  if (!vehicle) return null;
  const v = vehicle;

  const accident = v.accident_count ?? 0;
  const flood = !!v.flood_history;
  const ownerChange = v.owner_change_count ?? 0;

  const rows: { label: string; value: string | null }[] = [
    { label: '브랜드', value: v.brand },
    {
      label: '모델',
      value: `${v.model}${v.trim ? ` ${v.trim}` : ''}`,
    },
    { label: '연식', value: `${v.year}년` },
    {
      label: '차종',
      value: v.body_type ? BODY_TYPE_LABEL[v.body_type] ?? v.body_type : null,
    },
    { label: '연료', value: v.fuel_type },
    { label: '변속기', value: v.transmission },
    { label: '구동방식', value: v.drive_type ?? null },
    { label: '배기량', value: v.engine_cc ? `${v.engine_cc.toLocaleString()}cc` : null },
    { label: '주행거리', value: `${v.mileage.toLocaleString()}km` },
    { label: '색상', value: v.color ?? null },
    { label: '승차정원', value: v.seats ? `${v.seats}인승` : null },
    { label: '차량번호', value: v.plate_number_masked ?? null },
    {
      label: 'VIN',
      value: v.vin_last4 ? `**** **** ***${v.vin_last4}` : null,
    },
    { label: '최초 등록일', value: fmtDate(v.first_registered_at) },
    { label: '성능·상태 점검일', value: fmtDate(v.inspection_date) },
    { label: '지역', value: v.region ?? null },
  ].filter((r) => r.value != null && r.value !== '');

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center mb-4">
        <Info size={16} color="#C8A96E" />
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-white text-base ml-2">
          차량 정보
        </Text>
      </View>

      <View className="flex-row flex-wrap mb-4" style={{ gap: 6 }}>
        <HistoryBadge
          icon={
            accident > 0 ? (
              <AlertTriangle size={11} color="#EF4444" />
            ) : (
              <ShieldCheck size={11} color="#C8A96E" />
            )
          }
          label={accident > 0 ? `사고 ${accident}회` : '무사고'}
          tone={accident > 0 ? 'danger' : 'good'}
        />
        <HistoryBadge
          icon={<Droplets size={11} color={flood ? '#EF4444' : '#C8A96E'} />}
          label={flood ? '침수 이력' : '침수無'}
          tone={flood ? 'danger' : 'good'}
        />
        <HistoryBadge
          icon={<Users size={11} color="#C8A96E" />}
          label={ownerChange === 0 ? '소유자 1명' : `소유자 ${ownerChange + 1}명`}
          tone="good"
        />
      </View>

      {rows.map((r) => (
        <View key={r.label} className="flex-row items-start mb-2.5">
          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-xs w-24">
            {r.label}
          </Text>
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-white text-xs flex-1">
            {r.value}
          </Text>
        </View>
      ))}
    </View>
  );
}

function HistoryBadge({
  icon,
  label,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  tone: 'good' | 'danger';
}) {
  const isGood = tone === 'good';
  return (
    <View
      className={`flex-row items-center px-2.5 py-1 rounded-full border ${
        isGood
          ? 'bg-[#C8A96E]/15 border-[#C8A96E]/40'
          : 'bg-[#EF4444]/15 border-[#EF4444]/40'
      }`}>
      {icon}
      <Text
        style={{ fontFamily: 'Pretendard-Bold' }}
        className={`text-[11px] ml-1 ${isGood ? 'text-[#C8A96E]' : 'text-[#EF4444]'}`}>
        {label}
      </Text>
    </View>
  );
}
