import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Built into frontend/explore so the Flask server on the phone only serves static files.
export default defineConfig({
    base: '/explore/',
    plugins: [react()],
    build: {
        outDir: '../frontend/explore',
        emptyOutDir: true,
        chunkSizeWarningLimit: 400,
    },
    server: { proxy: { '/api': 'http://localhost:5000' } },
    test: { environment: 'node' },
});
