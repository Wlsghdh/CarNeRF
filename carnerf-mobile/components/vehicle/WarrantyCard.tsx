import { ShieldCheck } from 'lucide-react-native';
import { Text, View } from 'react-native';

import {
  INSPECTION_WARRANTY,
  WARRANTY_BY_BRAND,
  WarrantyTerms,
} from '../../lib/constants/warranty';

interface Remain {
  daysLeft: number;
  kmLeft: number;
  isExpired: boolean;
  endDate: string;
}

function calcRemain(
  startISO: string | null | undefined,
  mileage: number,
  terms: { years: number; km: number },
): Remain | null {
  if (!startISO) return null;
  const start = new Date(startISO);
  if (Number.isNaN(start.getTime())) return null;
  const end = new Date(start);
  end.setFullYear(end.getFullYear() + terms.years);
  const daysLeft = Math.max(0, Math.floor((end.getTime() - Date.now()) / 86400000));
  const kmLeft = Math.max(0, terms.km - mileage);
  return {
    daysLeft,
    kmLeft,
    isExpired: daysLeft === 0 || kmLeft === 0,
    endDate: end.toISOString().slice(0, 10).replace(/-/g, '.'),
  };
}

function calcInspectionRemain(
  inspectionISO: string | null | undefined,
  mileage: number,
  baseMileage: number,
): Remain | null {
  if (!inspectionISO) return null;
  const start = new Date(inspectionISO);
  if (Number.isNaN(start.getTime())) return null;
  const end = new Date(start);
  end.setDate(end.getDate() + INSPECTION_WARRANTY.days);
  const daysLeft = Math.max(0, Math.floor((end.getTime() - Date.now()) / 86400000));
  const kmLeft = Math.max(0, INSPECTION_WARRANTY.km - Math.max(0, mileage - baseMileage));
  return {
    daysLeft,
    kmLeft,
    isExpired: daysLeft === 0 || kmLeft === 0,
    endDate: end.toISOString().slice(0, 10).replace(/-/g, '.'),
  };
}

export function WarrantyCard({
  brand,
  firstRegisteredAt,
  inspectionDate,
  mileage,
}: {
  brand: string;
  firstRegisteredAt?: string | null;
  inspectionDate?: string | null;
  mileage: number;
}) {
  const terms: WarrantyTerms | undefined = WARRANTY_BY_BRAND[brand];

  const general = terms ? calcRemain(firstRegisteredAt, mileage, terms.general) : null;
  const powertrain = terms ? calcRemain(firstRegisteredAt, mileage, terms.powertrain) : null;
  const rust = terms?.rust ? calcRemain(firstRegisteredAt, mileage, terms.rust) : null;
  const inspection = calcInspectionRemain(inspectionDate, mileage, mileage);

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center mb-4">
        <ShieldCheck size={16} color="#C8A96E" />
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-white text-base ml-2">
          A/S 보증 정보
        </Text>
      </View>

      {terms && firstRegisteredAt ? (
        <View className="mb-4">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-ink-soft text-xs mb-2">
            제조사 신차 보증
          </Text>
          {general && (
            <WarrantyRow label="일반 보증" remain={general} />
          )}
          {powertrain && (
            <WarrantyRow label="동력계 보증" remain={powertrain} />
          )}
          {rust && <WarrantyRow label="부식 보증" remain={rust} />}
        </View>
      ) : (
        <Text
          style={{ fontFamily: 'Pretendard' }}
          className="text-ink-mute text-xs mb-4">
          {terms
            ? '최초 등록일 정보가 없어 신차 보증 잔여를 계산할 수 없습니다.'
            : `${brand} 브랜드의 보증 정보가 등록되어 있지 않습니다.`}
        </Text>
      )}

      {inspection && (
        <View className="mb-4">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-ink-soft text-xs mb-2">
            성능·상태 점검 보증
          </Text>
          <View className="flex-row items-start mb-1.5">
            <Text
              style={{ fontFamily: 'Pretendard' }}
              className="text-ink-mute text-[11px] w-20">
              점검일
            </Text>
            <Text
              style={{ fontFamily: 'Pretendard-SemiBold' }}
              className="text-white text-[11px]">
              {inspectionDate?.replace(/-/g, '.')}
            </Text>
          </View>
          <View className="flex-row items-start mb-1.5">
            <Text
              style={{ fontFamily: 'Pretendard' }}
              className="text-ink-mute text-[11px] w-20">
              보증범위
            </Text>
            <Text
              style={{ fontFamily: 'Pretendard' }}
              className="text-ink-soft text-[11px] flex-1">
              {INSPECTION_WARRANTY.days}일 또는 {INSPECTION_WARRANTY.km.toLocaleString()}km
              이내 발견된 결함 무상 수리
            </Text>
          </View>
          <WarrantyRow label="잔여" remain={inspection} />
        </View>
      )}

      <Text
        style={{ fontFamily: 'Pretendard' }}
        className="text-ink-mute text-[10px] mt-1 leading-snug">
        ※ 보증은 차량 최초 등록일 기준 자동 계산된 예상치입니다. 정확한 보증 범위는 제조사 정책에
        따라 상이할 수 있으며, 제조사 보증과 성능·상태 점검 보증은 별도로 운영됩니다.
      </Text>
    </View>
  );
}

function WarrantyRow({ label, remain }: { label: string; remain: Remain }) {
  const years = Math.floor(remain.daysLeft / 365);
  const months = Math.floor((remain.daysLeft % 365) / 30);
  const remainText =
    years > 0 ? `${years}년 ${months}개월` : `${remain.daysLeft}일`;
  const kmText = remain.kmLeft >= 999_000 ? '무제한' : `${remain.kmLeft.toLocaleString()}km`;

  return (
    <View className="flex-row items-center mb-2">
      <Text
        style={{ fontFamily: 'Pretendard' }}
        className="text-ink-mute text-[11px] w-20">
        {label}
      </Text>
      {remain.isExpired ? (
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-ink-mute text-[11px]">
          만료됨
        </Text>
      ) : (
        <View className="flex-row items-center flex-1">
          <View className="bg-[#C8A96E]/15 border border-[#C8A96E]/40 rounded-full px-2.5 py-1">
            <Text
              style={{ fontFamily: 'Pretendard-Bold' }}
              className="text-[#C8A96E] text-[11px]">
              {remainText} · {kmText}
            </Text>
          </View>
          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-[10px] ml-2">
            ~{remain.endDate}까지
          </Text>
        </View>
      )}
    </View>
  );
}
