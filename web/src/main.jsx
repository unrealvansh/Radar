import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MotionConfig } from 'motion/react';
import App from './App.jsx';
import { RadarProvider } from './store.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <MotionConfig reducedMotion="user">
            <RadarProvider>
                <App />
            </RadarProvider>
        </MotionConfig>
    </StrictMode>
);
