import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'onnuri-fuel-map',
  brand: { primaryColor: '#233e78' },
  permissions: [{ name: 'geolocation', access: 'access' }],
  navigationBar: { withBackButton: true, withTitle: true, theme: 'light' },
  webView: { bounces: false, pullToRefreshEnabled: false, overScrollMode: 'never' },
  webBundleDir: 'dist',
});
