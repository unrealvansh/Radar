import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    base: '/app/',
    plugins: [react()],
    build: {
        outDir: '../frontend/app',
        emptyOutDir: true,
        chunkSizeWarningLimit: 400,
    },
    server: { proxy: { '/api': 'http://localhost:5000' } },
    test: { environment: 'node' },
});
