// KST(UTC+9) 기준 ISO 주차 키 생성. 매주 월요일 0시(KST)에 키가 바뀐다.
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

export function nowKst(): Date {
  return new Date(Date.now() + KST_OFFSET_MS);
}

// 주 시작(월요일 0시 KST)의 timestamp 반환
export function weekStartKst(d: Date = nowKst()): Date {
  const dow = d.getUTCDay();
  const diff = (dow + 6) % 7;
  const ws = new Date(d);
  ws.setUTCDate(ws.getUTCDate() - diff);
  ws.setUTCHours(0, 0, 0, 0);
  return ws;
}

// ISO 주차 키: "2026-W20"
export function weekKey(d: Date = nowKst()): string {
  const ws = weekStartKst(d);
  const year = ws.getUTCFullYear();
  const first = new Date(Date.UTC(year, 0, 1));
  const days = Math.floor((ws.getTime() - first.getTime()) / 86400000);
  const week = Math.ceil((days + first.getUTCDay() + 1) / 7);
  return `${year}-W${String(week).padStart(2, '0')}`;
}

// 다음 월요일까지 남은 일/시/분/초
export function timeToNextMondayKst(d: Date = nowKst()): {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
} {
  const ws = weekStartKst(d);
  const next = new Date(ws);
  next.setUTCDate(next.getUTCDate() + 7);
  const totalMs = next.getTime() - d.getTime();
  return {
    days: Math.floor(totalMs / 86400000),
    hours: Math.floor((totalMs % 86400000) / 3600000),
    minutes: Math.floor((totalMs % 3600000) / 60000),
    seconds: Math.floor((totalMs % 60000) / 1000),
    totalMs,
  };
}

// 결정론적 PRNG (mulberry32)
export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 문자열 → 정수 시드 (FNV-1a)
export function hashSeed(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}
