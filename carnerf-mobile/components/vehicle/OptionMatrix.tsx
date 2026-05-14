import {
  Check,
  ChevronDown,
  ChevronUp,
  Sparkles,
  type LucideIcon,
} from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { Modal, Pressable, Text, View } from 'react-native';

import {
  CAR_OPTIONS,
  CATEGORY_LABEL,
  CATEGORY_ORDER,
  type CarOption,
} from '../../lib/constants/options';
import { Button } from '../ui/Button';

export function OptionMatrix({ owned }: { owned?: string[] }) {
  const ownedSet = new Set(owned ?? []);
  const total = CAR_OPTIONS.length;
  const ownedItems = CAR_OPTIONS.filter((o) => ownedSet.has(o.key));
  const ownedCount = ownedItems.length;

  const [expanded, setExpanded] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const selected = useMemo<CarOption | null>(
    () =>
      selectedKey
        ? CAR_OPTIONS.find((o) => o.key === selectedKey) ?? null
        : null,
    [selectedKey],
  );

  const openOption = (key: string) => {
    if (selectedKey) return;
    setSelectedKey(key);
  };
  const closeOption = () => setSelectedKey(null);

  return (
    <View className="bg-[#0E1117] border border-white/5 rounded-2xl p-5">
      <View className="flex-row items-center justify-between mb-4">
        <View className="flex-row items-center">
          <Sparkles size={16} color="#C8A96E" />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-base ml-2">
            보유 옵션
          </Text>
        </View>
        <Text
          style={{ fontFamily: 'Pretendard-Bold' }}
          className="text-[#C8A96E] text-base">
          {ownedCount}
          <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-xs">
            {' '}/ {total}
          </Text>
        </Text>
      </View>

      {!expanded && (
        <View>
          {ownedItems.length === 0 ? (
            <Text
              style={{ fontFamily: 'Pretendard' }}
              className="text-ink-mute text-xs py-2">
              등록된 보유 옵션이 없습니다
            </Text>
          ) : (
            <View className="flex-row flex-wrap" style={{ gap: 6 }}>
              {ownedItems.map((o) => (
                <OptionPill
                  key={o.key}
                  label={o.label}
                  active
                  icon={o.icon}
                  onPress={() => openOption(o.key)}
                />
              ))}
            </View>
          )}
        </View>
      )}

      {expanded &&
        CATEGORY_ORDER.map((cat) => {
          const items = CAR_OPTIONS.filter((o) => o.category === cat);
          if (items.length === 0) return null;
          const catOwned = items.filter((o) => ownedSet.has(o.key)).length;
          return (
            <View key={cat} className="mt-3">
              <View className="flex-row items-center mb-2">
                <Text
                  style={{ fontFamily: 'Pretendard-SemiBold' }}
                  className="text-ink-soft text-xs">
                  {CATEGORY_LABEL[cat]}
                </Text>
                <Text
                  style={{ fontFamily: 'Pretendard' }}
                  className="text-ink-mute text-[10px] ml-2">
                  {catOwned}/{items.length}
                </Text>
              </View>
              <View className="flex-row flex-wrap" style={{ gap: 6 }}>
                {items.map((o) => (
                  <OptionPill
                    key={o.key}
                    label={o.label}
                    active={ownedSet.has(o.key)}
                    onPress={() => openOption(o.key)}
                  />
                ))}
              </View>
            </View>
          );
        })}

      <Pressable
        onPress={() => setExpanded((v) => !v)}
        className="mt-4 flex-row items-center justify-center bg-white/5 border border-white/10 rounded-xl py-2.5">
        <Text
          style={{ fontFamily: 'Pretendard-SemiBold' }}
          className="text-[#C8A96E] text-xs mr-1">
          {expanded ? '접기' : `전체 옵션 보기 (${total}개)`}
        </Text>
        {expanded ? (
          <ChevronUp size={14} color="#C8A96E" />
        ) : (
          <ChevronDown size={14} color="#C8A96E" />
        )}
      </Pressable>

      {expanded && (
        <Text
          style={{ fontFamily: 'Pretendard' }}
          className="text-ink-mute text-[10px] mt-3">
          ※ 골드는 보유 · 회색은 미보유
        </Text>
      )}

      <Modal
        visible={!!selected}
        transparent
        animationType="slide"
        onRequestClose={closeOption}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.6)' }}>
          <Pressable style={{ flex: 1 }} onPress={closeOption} />
          <View
            className="bg-[#0E1117] border-t border-white/10 px-6 pt-3 pb-10"
            style={{ borderTopLeftRadius: 28, borderTopRightRadius: 28 }}>
            <View
              style={{
                width: 40,
                height: 4,
                backgroundColor: 'rgba(255,255,255,0.2)',
                borderRadius: 2,
                alignSelf: 'center',
                marginBottom: 18,
              }}
            />
            {selected && (
              <>
                <View className="items-center mb-4">
                  <View
                    style={{
                      width: 64,
                      height: 64,
                      borderRadius: 32,
                      backgroundColor: 'rgba(200,169,110,0.18)',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                    <selected.icon size={28} color="#C8A96E" />
                  </View>
                </View>
                <Text
                  style={{ fontFamily: 'Pretendard-Bold' }}
                  className="text-white text-lg text-center">
                  {selected.label}
                </Text>
                <View className="items-center mt-2">
                  {ownedSet.has(selected.key) ? (
                    <View className="px-3 py-1 bg-[#C8A96E]/15 border border-[#C8A96E]/40 rounded-full">
                      <Text
                        style={{ fontFamily: 'Pretendard-SemiBold' }}
                        className="text-[#C8A96E] text-xs">
                        이 차량 보유
                      </Text>
                    </View>
                  ) : (
                    <View className="px-3 py-1 bg-white/5 border border-white/10 rounded-full">
                      <Text
                        style={{ fontFamily: 'Pretendard-SemiBold' }}
                        className="text-ink-mute text-xs">
                        미보유
                      </Text>
                    </View>
                  )}
                </View>
                <Text
                  style={{ fontFamily: 'Pretendard' }}
                  className="text-ink-soft text-sm leading-relaxed mt-5 text-center">
                  {selected.description}
                </Text>
                <View className="mt-7">
                  <Button label="닫기" variant="outline" onPress={closeOption} />
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

function OptionPill({
  label,
  active,
  icon: Icon,
  onPress,
}: {
  label: string;
  active: boolean;
  icon?: LucideIcon;
  onPress?: () => void;
}) {
  const hasIcon = !!Icon;
  const hasLeading = hasIcon || active;
  const content = (
    <View
      className={`flex-row items-center px-3 py-1.5 rounded-full border ${
        active
          ? 'bg-[#C8A96E]/15 border-[#C8A96E]/50'
          : 'bg-white/5 border-white/10'
      }`}>
      {Icon ? (
        <Icon size={11} color={active ? '#C8A96E' : '#9CA3AF'} />
      ) : null}
      {active && (
        <Check
          size={11}
          color="#C8A96E"
          style={hasIcon ? { marginLeft: 3 } : undefined}
        />
      )}
      <Text
        style={{ fontFamily: active ? 'Pretendard-Bold' : 'Pretendard' }}
        className={`text-[11px] ${hasLeading ? 'ml-1' : ''} ${
          active ? 'text-[#C8A96E]' : 'text-ink-mute'
        }`}>
        {label}
      </Text>
    </View>
  );

  if (!onPress) return content;
  return <Pressable onPress={onPress}>{content}</Pressable>;
}
