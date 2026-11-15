import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { apiBaseUrl } from './src/api/config.ts';

export default defineConfig(({ command, mode }) => {
  // Vite exposes only public VITE_ settings to the browser. Fail the build
  // before producing an artifact with an unsafe or wrongly prefixed API URL.
  if (command === 'build') {
    const env = loadEnv(mode, '.', ['VITE_', 'NODE_ENV']);
    if ((env.NODE_ENV && env.NODE_ENV !== 'production') ||
        (env.VITE_USER_NODE_ENV && env.VITE_USER_NODE_ENV !== 'production')) {
      throw new Error('Production builds require NODE_ENV=production; remove development NODE_ENV overrides.');
    }
    apiBaseUrl(true, env.VITE_API_BASE_URL);
  }
  return {
    plugins: [react()],
    test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', css: true }
  };
});
