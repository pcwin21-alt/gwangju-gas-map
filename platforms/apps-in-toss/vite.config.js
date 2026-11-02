import { defineConfig } from 'vite';
import { resolve } from 'node:path';

export default defineConfig({
  publicDir: false,
  build: {
    outDir: 'dist/assets',
    emptyOutDir: false,
    lib: { entry: resolve(import.meta.dirname, 'src/toss-adapter.js'), formats: ['es'], fileName: () => 'toss-adapter.js' },
    sourcemap: false,
  },
});
