import { Sparkles, ThumbsUp, ThumbsDown, AlertTriangle } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { VehicleSummary } from '../../lib/types';

export function AISummary({ summary }: { summary: VehicleSummary }) {
  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center mb-3">
        <Sparkles size={16} color="#C8A96E" />
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-white text-base ml-2">
          AI 차량 요약
        </Text>
        <View className="ml-2 px-2 py-0.5 bg-[#C8A96E]/20 rounded-full">
          <Text
            style={{ fontFamily: 'Pretendard-SemiBold' }}
            className="text-[#C8A96E] text-[10px]">
            RAG · 실제 후기 기반
          </Text>
        </View>
      </View>
      <Text
        style={{ fontFamily: 'Pretendard' }}
        className="text-ink-soft text-sm leading-relaxed">
        {summary.summary}
      </Text>

      <PointList icon={<ThumbsUp size={14} color="#C8A96E" />} title="장점" items={summary.pros} />
      <PointList icon={<ThumbsDown size={14} color="#9CA3AF" />} title="단점" items={summary.cons} muted />
      {summary.known_issues?.length ? (
        <PointList
          icon={<AlertTriangle size={14} color="#EAB308" />}
          title="고질병"
          items={summary.known_issues}
          warning
        />
      ) : null}
    </View>
  );
}

function PointList({
  icon,
  title,
  items,
  muted,
  warning,
}: {
  icon: React.ReactNode;
  title: string;
  items: unknown;
  muted?: boolean;
  warning?: boolean;
}) {
  const list = toStringArray(items);
  if (!list.length) return null;
  return (
    <View className="mt-4">
      <View className="flex-row items-center mb-2">
        {icon}
        <Text
          style={{ fontFamily: 'Pretendard-SemiBold' }}
          className={`text-sm ml-2 ${warning ? 'text-yellow-300' : muted ? 'text-ink-mute' : 'text-[#C8A96E]'}`}>
          {title}
        </Text>
      </View>
      {list.map((it, i) => (
        <Text
          key={i}
          style={{ fontFamily: 'Pretendard' }}
          className="text-ink-soft text-xs leading-relaxed">
          • {it}
        </Text>
      ))}
    </View>
  );
}

function toStringArray(v: unknown): string[] {
  if (Array.isArray(v)) {
    return v.filter((x) => typeof x === 'string' && x.trim().length > 0) as string[];
  }
  if (typeof v === 'string' && v.trim().length > 0) {
    try {
      const parsed = JSON.parse(v);
      if (Array.isArray(parsed)) return toStringArray(parsed);
    } catch {}
    return [v.trim()];
  }
  return [];
}
