import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import cssInjectedByJs from 'vite-plugin-css-injected-by-js';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.includes('.ce.'),
        },
      },
    }),
    // CSS прямо в JS-бандл — удобно для embed/iframe
    cssInjectedByJs(),
  ],

  resolve: {
    alias: {
      // vue3-openlayers использует template compiler — нужен ESM-билд с runtime compiler
      vue: 'vue/dist/vue.esm-bundler.js',
    },
  },

  build: {
    lib: {
      entry:    resolve(__dirname, 'src/index.js'),
      name:     'SdekPvzWidget',
      fileName: 'SdekPvzWidget',
      formats:  ['umd'],
    },
    rollupOptions: {
      external: ['ol'],
      output: {
        inlineDynamicImports: true,
        entryFileNames: 'SdekPvzWidget.js',
        globals: {
          ol: 'ol',
        },
      },
    },
  },
});
