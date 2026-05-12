import { Tabs } from 'expo-router';
import { Home, Car, Video, User } from 'lucide-react-native';
import { Text } from 'react-native';

const GOLD = '#C8A96E';
const MUTE = '#6B7280';

const tabLabel = (label: string, color: string) => (
  <Text style={{ fontFamily: 'Pretendard-SemiBold', fontSize: 11, color }}>{label}</Text>
);

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: GOLD,
        tabBarInactiveTintColor: MUTE,
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0a0a0a',
          borderTopColor: 'rgba(255,255,255,0.06)',
          height: 64,
          paddingBottom: 10,
          paddingTop: 8,
        },
      }}>
      <Tabs.Screen
        name="index"
        options={{
          tabBarIcon: ({ color }) => <Home size={22} color={color} />,
          tabBarLabel: ({ color }) => tabLabel('홈', color),
        }}
      />
      <Tabs.Screen
        name="listings"
        options={{
          tabBarIcon: ({ color }) => <Car size={22} color={color} />,
          tabBarLabel: ({ color }) => tabLabel('매물', color),
        }}
      />
      <Tabs.Screen
        name="sell"
        options={{
          tabBarIcon: ({ color }) => <Video size={22} color={color} />,
          tabBarLabel: ({ color }) => tabLabel('내 차 팔기', color),
        }}
      />
      <Tabs.Screen
        name="mypage"
        options={{
          tabBarIcon: ({ color }) => <User size={22} color={color} />,
          tabBarLabel: ({ color }) => tabLabel('마이', color),
        }}
      />
    </Tabs>
  );
}
