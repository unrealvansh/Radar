import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MotionConfig } from 'motion/react';
import App from './App.jsx';
import { hasToken } from './api.js';
import { RadarProvider } from './store.jsx';
import './styles.css';

if (!hasToken()) {
    location.replace('/');  // log in on the main Radar app first; the token is shared
} else {
    createRoot(document.getElementById('root')).render(
        <StrictMode>
            <MotionConfig reducedMotion="user">
                <RadarProvider>
                    <App />
                </RadarProvider>
            </MotionConfig>
        </StrictMode>
    );
}
