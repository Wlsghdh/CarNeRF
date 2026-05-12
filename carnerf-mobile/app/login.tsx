import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';

import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Logo } from '../components/Brand';
import { extractError } from '../lib/api/client';
import { useAuth } from '../lib/store/auth';

type Mode = 'login' | 'register';

export default function LoginScreen() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!email || !password) {
      Alert.alert('알림', '이메일과 비밀번호를 입력하세요.');
      return;
    }
    if (mode === 'register' && !username) {
      Alert.alert('알림', '닉네임을 입력하세요.');
      return;
    }
    try {
      setLoading(true);
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register({ email, password, username, phone: phone || undefined });
        await login(email, password);
      }
      router.replace('/');
    } catch (err) {
      Alert.alert('실패', extractError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        className="flex-1">
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ padding: 20, paddingTop: 32 }}
          keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => router.back()} className="self-end mb-4">
            <Text style={{ fontFamily: 'Pretendard-Medium' }} className="text-ink-mute text-xs">
              닫기
            </Text>
          </Pressable>

          <Logo size={28} />
          <Text
            style={{ fontFamily: 'Pretendard-Bold' }}
            className="text-white text-2xl mt-6 leading-snug">
            {mode === 'login' ? '다시 만나서 반갑습니다' : '계정을 만들어 보세요'}
          </Text>
          <Text style={{ fontFamily: 'Pretendard' }} className="text-ink-mute text-sm mt-2">
            CarNeRF의 3D · AI 분석 · 시세 예측을 한 번에.
          </Text>

          <View className="flex-row mt-8 bg-white/5 rounded-2xl p-1">
            {(['login', 'register'] as Mode[]).map((m) => {
              const active = mode === m;
              return (
                <Pressable
                  key={m}
                  onPress={() => setMode(m)}
                  className={`flex-1 py-2 rounded-xl items-center ${active ? 'bg-[#C8A96E]' : ''}`}>
                  <Text
                    style={{ fontFamily: 'Pretendard-SemiBold' }}
                    className={`text-sm ${active ? 'text-black' : 'text-ink-mute'}`}>
                    {m === 'login' ? '로그인' : '회원가입'}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <View className="mt-6">
            <Input
              label="이메일"
              value={email}
              onChangeText={setEmail}
              placeholder="you@carnerf.kr"
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
            />
            {mode === 'register' && (
              <>
                <Input
                  label="닉네임"
                  value={username}
                  onChangeText={setUsername}
                  placeholder="홍길동"
                />
                <Input
                  label="휴대폰 (선택)"
                  value={phone}
                  onChangeText={setPhone}
                  placeholder="010-1234-5678"
                  keyboardType="phone-pad"
                />
              </>
            )}
            <Input
              label="비밀번호"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
            />

            <Button label={mode === 'login' ? '로그인' : '회원가입 후 시작'} onPress={submit} loading={loading} />
          </View>

          <Text
            style={{ fontFamily: 'Pretendard' }}
            className="text-ink-mute text-xs text-center mt-8">
            로그인하면 CarNeRF의 이용약관과 개인정보 처리방침에 동의하는 것으로 간주됩니다.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
