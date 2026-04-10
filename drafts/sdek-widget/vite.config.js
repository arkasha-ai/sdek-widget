import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import cssInjectedByJs from 'vite-plugin-css-injected-by-js';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    vue(),
    // CSS прямо в JS-бандл — удобно для embed/iframe
    cssInjectedByJs(),
  ],

  resolve: {
    alias: {
      // vue3-openlayers использует ESM — убеждаемся что Vite правильно его резолвит
    },
  },

  build: {
    lib: {
      entry:    resolve(__dirname, 'src/index.js'),
      name:     'SdekPvzWidget',
      fileName: 'SdekPvzWidget',
      formats:  ['es', 'umd'],
    },
    rollupOptions: {
      external: ['vue', 'ol', 'vue3-openlayers'],
      output: {
        globals: {
          vue:              'Vue',
          ol:               'ol',
          'vue3-openlayers': 'Vue3Openlayers',
        },
      },
    },
  },
});
