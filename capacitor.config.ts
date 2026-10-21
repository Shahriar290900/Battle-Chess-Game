import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.shahriar.battlechess',
  appName: 'Battle Chess',
  webDir: 'dist',
  backgroundColor: '#0b0d12',
  android: { backgroundColor: '#0b0d12', allowMixedContent: false },
};

export default config;
