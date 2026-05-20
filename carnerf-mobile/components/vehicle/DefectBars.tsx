import { ShieldCheck } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { DefectReport } from '../../lib/types';

const SEVERITY_COLOR = { low: '#22C55E', medium: '#EAB308', high: '#EF4444' };

export function DefectBars({ report }: { report: DefectReport }) {
  const counts = report.defects.reduce(
    (acc, d) => {
      acc[d.severity] = (acc[d.severity] ?? 0) + 1;
      return acc;
    },
    { low: 0, medium: 0, high: 0 } as Record<'low' | 'medium' | 'high', number>,
  );
  const max = Math.max(1, counts.low + counts.medium + counts.high);

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-3">
        <View className="flex-row items-center">
          <ShieldCheck size={16} color="#C8A96E" />
          <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-base ml-2">
            AI 결함 리포트
          </Text>
        </View>
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-[#C8A96E] text-2xl">
          {report.total_defect_score}
          <Text className="text-ink-mute text-xs"> 점</Text>
        </Text>
      </View>

      <Row label="경미" color={SEVERITY_COLOR.low} count={counts.low} ratio={counts.low / max} />
      <Row label="중간" color={SEVERITY_COLOR.medium} count={counts.medium} ratio={counts.medium / max} />
      <Row label="심각" color={SEVERITY_COLOR.high} count={counts.high} ratio={counts.high / max} />

      <View className="mt-3 pt-3 border-t border-white/5">
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
          전체 등급:{' '}
          <Text
            style={{ fontFamily: 'Pretendard-Bold', color: SEVERITY_COLOR[report.severity_level] }}>
            {report.severity_level.toUpperCase()}
          </Text>
        </Text>
      </View>
    </View>
  );
}

function Row({ label, color, count, ratio }: { label: string; color: string; count: number; ratio: number }) {
  return (
    <View className="mb-2.5">
      <View className="flex-row items-center justify-between mb-1">
        <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-soft text-xs">
          {label}
        </Text>
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-xs">
          {count}건
        </Text>
      </View>
      <View className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <View
          style={{ width: `${Math.max(4, ratio * 100)}%`, backgroundColor: color }}
          className="h-full"
        />
      </View>
    </View>
  );
}
