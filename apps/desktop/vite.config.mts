import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import electron from 'vite-plugin-electron';
import renderer from 'vite-plugin-electron-renderer';

/** file:// and app:// cannot load crossorigin module scripts on macOS packaged builds. */
function stripCrossoriginForElectron(): { name: string; transformIndexHtml: (html: string) => string } {
  return {
    name: 'strip-crossorigin-for-electron',
    transformIndexHtml(html) {
      return html.replace(/\s+crossorigin/g, '');
    },
  };
}

export default defineConfig({
  // Relative base so /assets/* from public/ resolve under app:// and file:// in packaged Electron.
  base: './',
  plugins: [
    tailwindcss(),
    react(),
    stripCrossoriginForElectron(),
    electron([
      {
        entry: 'electron/main.ts',
        vite: {
          build: {
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron'],
            },
          },
        },
      },
      {
        entry: 'electron/preload.ts',
        onstart(options) {
          options.reload();
        },
        vite: {
          build: {
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron'],
            },
          },
        },
      },
    ]),
    renderer(),
  ],
  server: {
    port: 5173,
  },
  build: {
    outDir: 'dist',
    modulePreload: false,
  },
});
