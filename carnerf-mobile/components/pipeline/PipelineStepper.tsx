import { Check } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { PipelineStatus } from '../../lib/types';

const STEPS = [
  { key: 'extracting_frames', label: '프레임 추출' },
  { key: 'colmap', label: 'SfM (카메라 추정)' },
  { key: 'removing_background', label: '배경 제거' },
  { key: 'generating_depth', label: '깊이 추정' },
  { key: 'training', label: '3D 학습' },
  { key: 'exporting', label: '모델 추출' },
  { key: 'completed', label: '완료' },
] as const;

export function PipelineStepper({ status }: { status: PipelineStatus | null }) {
  const idx = status ? STEPS.findIndex((s) => s.key === status.status) : -1;

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-4">
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-white text-base">
          3D 파이프라인 진행률
        </Text>
        <Text style={{ fontFamily: 'Pretendard-Bold' }} className="text-[#C8A96E] text-base">
          {status?.progress != null ? `${Math.round(status.progress)}%` : '대기 중'}
        </Text>
      </View>

      {STEPS.map((s, i) => {
        const done = idx > i || status?.status === 'completed';
        const active = idx === i;
        return (
          <View key={s.key} className="flex-row items-center mb-2.5">
            <View
              className={`w-6 h-6 rounded-full items-center justify-center ${
                done ? 'bg-[#C8A96E]' : active ? 'border-2 border-[#C8A96E]' : 'border border-white/15'
              }`}>
              {done ? (
                <Check size={12} color="#000" />
              ) : (
                <Text
                  style={{ fontFamily: 'Pretendard-Bold' }}
                  className={`text-[10px] ${active ? 'text-[#C8A96E]' : 'text-ink-mute'}`}>
                  {i + 1}
                </Text>
              )}
            </View>
            <Text
              style={{ fontFamily: 'Pretendard-Medium' }}
              className={`text-sm ml-3 ${done || active ? 'text-white' : 'text-ink-mute'}`}>
              {s.label}
            </Text>
            {active && (
              <Text
                style={{ fontFamily: 'Pretendard' }}
                className="text-[#C8A96E] text-[11px] ml-auto">
                진행 중…
              </Text>
            )}
          </View>
        );
      })}

      {status?.message ? (
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-3">
          {status.message}
        </Text>
      ) : null}
    </View>
  );
}
