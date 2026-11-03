import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MotionConfig } from 'motion/react';
import App from './App.jsx';
import { RadarProvider } from './store.jsx';
import './styles.css';

// Motion is on unless the user turns on Radar's own "Reduce motion" setting
let reduce = false;
try { reduce = localStorage.getItem('radar_reduce_motion') === '1'; } catch { /* storage blocked */ }
document.documentElement.classList.toggle('reduce-motion', reduce);

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <MotionConfig reducedMotion={reduce ? 'always' : 'never'}>
            <RadarProvider>
                <App />
            </RadarProvider>
        </MotionConfig>
    </StrictMode>
);
