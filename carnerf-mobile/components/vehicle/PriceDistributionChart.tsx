import { TrendingDown, TrendingUp } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { LayoutChangeEvent, Text, View } from 'react-native';
import Svg, { Circle, G, Line as SvgLine, Text as SvgText } from 'react-native-svg';

import { PriceDistribution } from '../../lib/types';

const PADDING = { top: 18, right: 18, bottom: 28, left: 44 };
const HEIGHT = 200;

type Point = { x: number; y: number; kind: 'txn' | 'listing' | 'mine'; label?: string };

export function PriceDistributionChart({
  distribution,
  ownPrice,
}: {
  distribution: PriceDistribution;
  ownPrice: number;
}) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const stats = distribution.stats;
  const txns = distribution.transactions ?? [];
  const listings = distribution.listings ?? [];

  if (!stats || stats.sample_size < 5) {
    return (
      <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
        <View className="flex-row items-center mb-2">
          <TrendingUp size={16} color="#C8A96E" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-base ml-2">
            가격 분포
          </Text>
        </View>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-2">
          비교 표본이 부족합니다 ({stats?.sample_size ?? 0}건)
        </Text>
      </View>
    );
  }

  const todayMs = Date.now();
  const oldestMs = useMemo(() => {
    const dates = [
      ...txns.map((t) => new Date(t.date).getTime()),
      ...listings.map((l) => new Date(l.date).getTime()),
    ].filter((n) => Number.isFinite(n));
    if (!dates.length) return todayMs - 365 * 86400000;
    return Math.min(...dates);
  }, [txns, listings, todayMs]);

  const xMin = stats.min * 0.9;
  const xMax = stats.max * 1.05;

  const innerW = Math.max(0, width - PADDING.left - PADDING.right);
  const innerH = HEIGHT - PADDING.top - PADDING.bottom;

  const sx = (price: number) =>
    PADDING.left + ((price - xMin) / Math.max(1, xMax - xMin)) * innerW;
  const sy = (ms: number) => {
    const range = Math.max(1, todayMs - oldestMs);
    return PADDING.top + ((todayMs - ms) / range) * innerH;
  };

  const points: Point[] = useMemo(() => {
    const out: Point[] = [];
    for (const t of txns) {
      const ms = new Date(t.date).getTime();
      if (!Number.isFinite(ms)) continue;
      out.push({ x: sx(t.price), y: sy(ms), kind: 'txn' });
    }
    for (const l of listings) {
      const ms = new Date(l.date).getTime();
      if (!Number.isFinite(ms)) continue;
      out.push({ x: sx(l.price), y: sy(ms), kind: 'listing' });
    }
    out.push({ x: sx(ownPrice), y: sy(todayMs), kind: 'mine' });
    return out;
  }, [txns, listings, ownPrice, width, todayMs, oldestMs, xMin, xMax]);

  const avgX = sx(stats.avg);
  const diff = ((ownPrice - stats.avg) / stats.avg) * 100;
  const diffAbs = Math.abs(diff).toFixed(1);
  const tone: 'cheap' | 'fair' | 'pricey' = diff < -3 ? 'cheap' : diff > 3 ? 'pricey' : 'fair';
  const toneColor =
    tone === 'cheap' ? '#22C55E' : tone === 'pricey' ? '#EF4444' : '#C8A96E';
  const toneLabel = tone === 'cheap' ? '저렴' : tone === 'pricey' ? '비쌈' : '적정';

  const xTicks = useMemo(() => {
    const ticks: number[] = [];
    const step = (xMax - xMin) / 4;
    for (let i = 0; i <= 4; i++) ticks.push(xMin + step * i);
    return ticks;
  }, [xMin, xMax]);

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-3">
        <View className="flex-row items-center">
          <TrendingUp size={16} color="#C8A96E" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-base ml-2">
            가격 분포
          </Text>
        </View>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[10px]">
          {distribution.range}
        </Text>
      </View>

      <View className="flex-row flex-wrap mb-3" style={{ gap: 6 }}>
        <StatChip label="평균" value={`${stats.avg.toLocaleString()}만`} />
        <StatChip label="최저" value={`${stats.min.toLocaleString()}만`} />
        <StatChip label="최고" value={`${stats.max.toLocaleString()}만`} />
        <StatChip label="중간값" value={`${stats.p50.toLocaleString()}만`} />
        <StatChip label="샘플" value={`${stats.sample_size}건`} />
      </View>

      <View onLayout={onLayout} style={{ height: HEIGHT }}>
        {width > 0 && (
          <Svg width={width} height={HEIGHT}>
            <G>
              {[0, 0.25, 0.5, 0.75, 1].map((p, i) => {
                const y = PADDING.top + innerH * p;
                return (
                  <SvgLine
                    key={`grid-${i}`}
                    x1={PADDING.left}
                    x2={width - PADDING.right}
                    y1={y}
                    y2={y}
                    stroke="rgba(255,255,255,0.05)"
                    strokeWidth={1}
                  />
                );
              })}
              <SvgLine
                x1={avgX}
                x2={avgX}
                y1={PADDING.top}
                y2={HEIGHT - PADDING.bottom}
                stroke="#C8A96E"
                strokeOpacity={0.4}
                strokeWidth={1}
                strokeDasharray="4,3"
              />
              <SvgText
                x={avgX}
                y={PADDING.top - 4}
                fontSize="9"
                fill="#C8A96E"
                textAnchor="middle"
                fontFamily="Pretendard-SemiBold">
                평균
              </SvgText>

              {points
                .filter((p) => p.kind === 'txn')
                .map((p, i) => (
                  <Circle
                    key={`t-${i}`}
                    cx={p.x}
                    cy={p.y}
                    r={3}
                    fill="rgba(156,163,175,0.45)"
                  />
                ))}
              {points
                .filter((p) => p.kind === 'listing')
                .map((p, i) => (
                  <Circle
                    key={`l-${i}`}
                    cx={p.x}
                    cy={p.y}
                    r={4}
                    fill="transparent"
                    stroke="#C8A96E"
                    strokeWidth={1.5}
                  />
                ))}
              {points
                .filter((p) => p.kind === 'mine')
                .map((p, i) => (
                  <G key={`m-${i}`}>
                    <Circle cx={p.x} cy={p.y} r={11} fill="#C8A96E" opacity={0.18} />
                    <Circle cx={p.x} cy={p.y} r={6} fill="#C8A96E" />
                    <SvgText
                      x={p.x}
                      y={p.y - 10}
                      fontSize="10"
                      fill="#C8A96E"
                      textAnchor="middle"
                      fontFamily="Pretendard-Bold">
                      내 차
                    </SvgText>
                  </G>
                ))}

              {xTicks.map((t, i) => (
                <SvgText
                  key={`xt-${i}`}
                  x={sx(t)}
                  y={HEIGHT - 10}
                  fontSize="9"
                  fill="#9CA3AF"
                  textAnchor="middle"
                  fontFamily="Pretendard">
                  {Math.round(t).toLocaleString()}
                </SvgText>
              ))}
              <SvgText
                x={PADDING.left}
                y={PADDING.top + 4}
                fontSize="9"
                fill="#9CA3AF"
                textAnchor="start"
                fontFamily="Pretendard">
                오늘
              </SvgText>
              <SvgText
                x={PADDING.left}
                y={HEIGHT - PADDING.bottom}
                fontSize="9"
                fill="#9CA3AF"
                textAnchor="start"
                fontFamily="Pretendard">
                {fmtMonth(oldestMs)}
              </SvgText>
            </G>
          </Svg>
        )}
      </View>

      <View className="flex-row items-center mt-2">
        {tone === 'cheap' ? (
          <TrendingDown size={13} color={toneColor} />
        ) : (
          <TrendingUp size={13} color={toneColor} />
        )}
        <Text
          style={{ fontFamily: 'Pretendard-Bold', color: toneColor }}
          className="text-xs ml-1">
          평균 대비 {diffAbs}% {diff < 0 ? '낮은' : '높은'} 가격 — {toneLabel}
        </Text>
      </View>

      <View className="flex-row items-center mt-3" style={{ gap: 12 }}>
        <Legend color="rgba(156,163,175,0.6)" label="과거 거래" />
        <Legend color="#C8A96E" hollow label="활성 매물" />
        <Legend color="#C8A96E" label="내 차" />
      </View>
    </View>
  );
}

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <View className="bg-white/5 rounded-full px-2.5 py-1 flex-row items-center">
      <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[10px]">
        {label}
      </Text>
      <Text
        style={{ fontFamily: 'Pretendard-Bold' }}
        className="text-white text-[11px] ml-1">
        {value}
      </Text>
    </View>
  );
}

function Legend({
  color,
  label,
  hollow,
}: {
  color: string;
  label: string;
  hollow?: boolean;
}) {
  return (
    <View className="flex-row items-center">
      <View
        style={{
          width: 9,
          height: 9,
          borderRadius: 5,
          backgroundColor: hollow ? 'transparent' : color,
          borderWidth: hollow ? 1.5 : 0,
          borderColor: color,
        }}
      />
      <Text
        style={{ fontFamily: 'Pretendard' }}
        className="text-ink-mute text-[10px] ml-1.5">
        {label}
      </Text>
    </View>
  );
}

function fmtMonth(ms: number): string {
  const d = new Date(ms);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
}
