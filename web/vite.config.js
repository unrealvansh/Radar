import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Built into frontend/app so the Flask server on the phone only serves static files (at /).
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
