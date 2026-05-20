import { useQuery } from '@tanstack/react-query';
import { TrendingDown, TrendingUp } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { ActivityIndicator, LayoutChangeEvent, Text, View } from 'react-native';
import Svg, { Circle, G, Line as SvgLine, Polyline, Text as SvgText } from 'react-native-svg';

import { transactionsApi } from '../../lib/api/transactions';

const PADDING = { top: 22, right: 20, bottom: 28, left: 50 };
const HEIGHT = 220;
const MS_MONTH = 30 * 86400 * 1000;
const TICK_MONTHS = [12, 9, 6, 3, 1];

type MonthlyPoint = { ms: number; price: number };

export function PriceTrendChart({
  vehicleId,
  ownPrice,
}: {
  vehicleId: number;
  ownPrice: number;
}) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const trendQ = useQuery({
    queryKey: ['market-trend', vehicleId],
    queryFn: () => transactionsApi.marketPrice(vehicleId),
    enabled: !!vehicleId,
  });

  const todayMs = Date.now();
  const startMs = todayMs - 12 * MS_MONTH;

  const points: MonthlyPoint[] = useMemo(() => {
    const data = trendQ.data as any;
    const raw = data?.monthly ?? data?.monthly_prices ?? [];
    if (!Array.isArray(raw)) return [];
    const parsed: MonthlyPoint[] = [];
    for (const item of raw) {
      if (!item || typeof item.month !== 'string') continue;
      const price = Number(item.price ?? item.avg_price);
      if (!Number.isFinite(price) || price <= 0) continue;
      const m = item.month.match(/^(\d{4})-(\d{1,2})/);
      if (!m) continue;
      const year = Number(m[1]);
      const month = Number(m[2]);
      if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) continue;
      const ms = new Date(year, month - 1, 15).getTime();
      if (!Number.isFinite(ms)) continue;
      if (ms < startMs - MS_MONTH || ms > todayMs + MS_MONTH) continue;
      parsed.push({ ms, price });
    }
    parsed.sort((a, b) => a.ms - b.ms);
    return parsed;
  }, [trendQ.data, startMs, todayMs]);

  const oldestMs = points.length ? Math.min(points[0].ms, startMs) : startMs;
  const xRangeMs = Math.max(MS_MONTH, todayMs - oldestMs);

  const allPrices = [
    ...points.map((p) => p.price),
    ...(Number.isFinite(ownPrice) && ownPrice > 0 ? [ownPrice] : []),
  ];
  let yMin = allPrices.length ? Math.min(...allPrices) : 0;
  let yMax = allPrices.length ? Math.max(...allPrices) : 1;
  if (yMax - yMin < 1) {
    const center = (yMax + yMin) / 2 || ownPrice || 1;
    yMin = center * 0.9;
    yMax = center * 1.1;
  } else {
    const pad = (yMax - yMin) * 0.1;
    yMin = Math.max(0, yMin - pad);
    yMax = yMax + pad;
  }

  const innerW = Math.max(0, width - PADDING.left - PADDING.right);
  const innerH = HEIGHT - PADDING.top - PADDING.bottom;

  const sx = (ms: number) => PADDING.left + ((ms - oldestMs) / xRangeMs) * innerW;
  const sy = (price: number) =>
    PADDING.top + (1 - (price - yMin) / Math.max(1, yMax - yMin)) * innerH;

  const polyPoints = points.map((p) => `${sx(p.ms)},${sy(p.price)}`).join(' ');

  const yTicks = useMemo(() => {
    const arr: number[] = [];
    for (let i = 0; i <= 4; i++) arr.push(yMin + ((yMax - yMin) * i) / 4);
    return arr;
  }, [yMin, yMax]);

  const latestAvg = points.length ? points[points.length - 1].price : 0;
  const diff = latestAvg > 0 ? ((ownPrice - latestAvg) / latestAvg) * 100 : 0;
  const diffAbs = Math.abs(diff).toFixed(1);
  const tone: 'cheap' | 'fair' | 'pricey' = diff < -3 ? 'cheap' : diff > 3 ? 'pricey' : 'fair';
  const toneColor =
    tone === 'cheap' ? '#22C55E' : tone === 'pricey' ? '#EF4444' : '#C8A96E';
  const toneLabel = tone === 'cheap' ? '저렴' : tone === 'pricey' ? '비쌈' : '적정';

  const showLoading = trendQ.isLoading;
  const insufficient = !showLoading && points.length < 3;

  const ownX = sx(todayMs);
  const ownY = sy(ownPrice);
  const showOwn = Number.isFinite(ownPrice) && ownPrice > 0;
  const ownLabelY = ownY < PADDING.top + 18 ? ownY + 20 : ownY - 12;

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-3">
        <View className="flex-row items-center">
          <TrendingUp size={16} color="#C8A96E" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-base ml-2">
            가격 추세
          </Text>
        </View>
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-[10px]">
          최근 12개월
        </Text>
      </View>

      {showLoading ? (
        <View className="py-12 items-center">
          <ActivityIndicator color="#C8A96E" />
        </View>
      ) : insufficient ? (
        <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs mt-2">
          시계열 데이터가 부족합니다
        </Text>
      ) : (
        <>
          <View onLayout={onLayout} style={{ height: HEIGHT }}>
            {width > 0 && (
              <Svg width={width} height={HEIGHT}>
                <G>
                  {yTicks.map((t, i) => {
                    const y = sy(t);
                    return (
                      <G key={`yt-${i}`}>
                        <SvgLine
                          x1={PADDING.left}
                          x2={width - PADDING.right}
                          y1={y}
                          y2={y}
                          stroke="rgba(255,255,255,0.05)"
                          strokeWidth={1}
                        />
                        <SvgText
                          x={PADDING.left - 6}
                          y={y + 3}
                          fontSize="9"
                          fill="#9CA3AF"
                          textAnchor="end"
                          fontFamily="Pretendard">
                          {Math.round(t).toLocaleString()}
                        </SvgText>
                      </G>
                    );
                  })}

                  {points.length > 1 && (
                    <Polyline
                      points={polyPoints}
                      fill="none"
                      stroke="#C8A96E"
                      strokeWidth={2}
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  )}

                  {points.map((p, i) => (
                    <Circle
                      key={`pt-${i}`}
                      cx={sx(p.ms)}
                      cy={sy(p.price)}
                      r={2.8}
                      fill="#C8A96E"
                    />
                  ))}

                  {showOwn && (
                    <G>
                      <Circle cx={ownX} cy={ownY} r={11} fill="#C8A96E" opacity={0.18} />
                      <Circle cx={ownX} cy={ownY} r={6} fill="#C8A96E" />
                      <SvgText
                        x={ownX - 10}
                        y={ownLabelY}
                        fontSize="10"
                        fill="#C8A96E"
                        textAnchor="end"
                        fontFamily="Pretendard-Bold">
                        내 차 {ownPrice.toLocaleString()}만
                      </SvgText>
                    </G>
                  )}

                  {TICK_MONTHS.map((m) => {
                    const ms = todayMs - m * MS_MONTH;
                    if (ms < oldestMs - MS_MONTH / 2) return null;
                    return (
                      <SvgText
                        key={`xt-${m}`}
                        x={sx(ms)}
                        y={HEIGHT - 10}
                        fontSize="9"
                        fill="#9CA3AF"
                        textAnchor="middle"
                        fontFamily="Pretendard">
                        {fmtMonth(ms)}
                      </SvgText>
                    );
                  })}
                </G>
              </Svg>
            )}
          </View>

          {latestAvg > 0 && (
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
          )}
        </>
      )}
    </View>
  );
}

function fmtMonth(ms: number): string {
  const d = new Date(ms);
  return `${d.getMonth() + 1}월`;
}
