// Platform glue: Capacitor (Android) vs plain web. Capacitor modules are loaded lazily so the web build never touches native APIs.
import { Capacitor } from '@capacitor/core';
import type { PlatformApi } from '../contracts';

export function createPlatform(): PlatformApi {
  const isNative = Capacitor.isNativePlatform();
  const isMobile = isNative || /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  const handlers: Array<() => boolean> = [];

  return {
    isNative,
    isMobile,

    async init() {
      if (!isNative) return;
      try {
        const [{ StatusBar }, { ScreenOrientation }, { App }] = await Promise.all([
          import('@capacitor/status-bar'),
          import('@capacitor/screen-orientation'),
          import('@capacitor/app'),
        ]);
        await StatusBar.hide().catch(() => {});
        await StatusBar.setOverlaysWebView({ overlay: true }).catch(() => {});
        await ScreenOrientation.unlock().catch(() => {});

        await App.addListener('backButton', () => {
          // Newest handler first; exit when nothing consumes the press.
          for (let i = handlers.length - 1; i >= 0; i--) if (handlers[i]()) return;
          void App.exitApp();
        });
        await App.addListener('appStateChange', ({ isActive }) => {
          window.dispatchEvent(new Event(isActive ? 'bc:app-resume' : 'bc:app-pause'));
        });
        await App.addListener('pause', () => window.dispatchEvent(new Event('bc:app-pause')));
        await App.addListener('resume', () => window.dispatchEvent(new Event('bc:app-resume')));
      } catch (err) {
        console.warn('[platform] native init failed', err);
      }
    },

    onBack(handler) { handlers.push(handler); },
  };
}
