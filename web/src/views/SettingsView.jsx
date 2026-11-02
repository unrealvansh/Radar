import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { api, lock } from '../api.js';
import { IconCopy, IconLocate, IconLock, IconX } from '../components/Icons.jsx';
import { useRadar } from '../store.jsx';

const RADII = [25, 50, 100, 300];

export default function SettingsView() {
    const { settings, saveSettings, home, saveHome, toast } = useRadar();
    const [name, setName] = useState('');
    const [keywords, setKeywords] = useState([]);
    const [kwInput, setKwInput] = useState('');
    const [cities, setCities] = useState([]);
    const [city, setCity] = useState(home?.city || '');
    const [radius, setRadius] = useState(home?.radius || 50);

    useEffect(() => {
        if (!settings) return;
        setName(settings.display_name || '');
        setKeywords(settings.keywords);
    }, [settings]);
    useEffect(() => { api('/api/cities').then(r => setCities(r.cities || [])).catch(() => {}); }, []);
    useEffect(() => { setCity(home?.city || ''); setRadius(home?.radius || 50); }, [home]);

    const attempt = async (work, ok) => {
        try { await work(); if (ok) toast(ok); } catch (e) { if (e.message !== 'unauthorized') toast('That did not work. Check that the server is running.'); }
    };

    const addKeyword = () => {
        const k = kwInput.trim().toLowerCase().replace(/,/g, '');
        if (k && !keywords.includes(k)) setKeywords([...keywords, k]);
        setKwInput('');
    };

    const useGps = () => {
        if (!window.isSecureContext || !navigator.geolocation) {
            toast('GPS only works on the HTTPS link. Pick your city below instead.');
            return;
        }
        toast('Finding your location');
        navigator.geolocation.getCurrentPosition(async pos => {
            const lat = Number(pos.coords.latitude.toFixed(4)), lon = Number(pos.coords.longitude.toFixed(4));
            attempt(async () => {
                const r = await api(`/api/cities?lat=${lat}&lon=${lon}`);
                const name = r.nearest.km <= 60 ? r.nearest.name : 'your location';
                await saveHome({ city: name, lat, lon, radius });
            }, 'Location saved');
        }, err => toast(err.code === 1 ? 'Location permission was denied. Pick your city instead.' : 'Could not get your location. Pick your city instead.'),
        { timeout: 10000, maximumAge: 600000 });
    };

    const saveCity = () => {
        const c = cities.find(x => x.name === city);
        if (!c) { toast('Pick a city first.'); return; }
        attempt(() => saveHome({ city: c.name, lat: c.lat, lon: c.lon, radius }), `Location set to ${c.name}`);
    };

    const copyTopic = async () => {
        try { await navigator.clipboard.writeText(settings.ntfy_topic); toast('Topic copied'); }
        catch { toast('Copy failed. Select the text and copy it yourself.'); }
    };

    const card = (i, children) => (
        <motion.section className="panel settings-card" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06, duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}>{children}</motion.section>
    );

    return (
        <div className="page settings">
            {card(0, <>
                <h2>Profile</h2>
                <p className="hint">Used for the greeting on Home.</p>
                <label htmlFor="set-name">Display name</label>
                <div className="row">
                    <input id="set-name" className="field" maxLength={40} value={name} onChange={e => setName(e.target.value)} placeholder="Your name" />
                    <button className="btn-primary" onClick={() => attempt(() => saveSettings({ display_name: name.trim() }), 'Name saved')}>Save</button>
                </div>
            </>)}

            {card(1, <>
                <h2>Location</h2>
                <p className="hint">{home ? `Showing opportunities within ${home.radius} km of ${home.city} first.` : 'Set your city to see nearby opportunities first.'}</p>
                <button className="btn-outline" onClick={useGps}><IconLocate />Use my current location</button>
                <label htmlFor="set-city">Or pick your city</label>
                <select id="set-city" className="field" value={city} onChange={e => setCity(e.target.value)}>
                    <option value="">Choose a city</option>
                    {[...cities].sort((a, b) => a.name.localeCompare(b.name)).map(c => (
                        <option key={c.name} value={c.name}>{c.name}{c.region !== c.name ? `, ${c.region}` : ''}{c.count ? ` (${c.count} open)` : ''}</option>
                    ))}
                </select>
                <label id="radius-label">Search radius</label>
                <div className="pillars" role="group" aria-labelledby="radius-label">
                    {RADII.map(r => (
                        <button key={r} aria-pressed={radius === r} onClick={() => setRadius(r)}>
                            {radius === r && <motion.span className="pillar-hl" layoutId="radius-hl" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                            <span>{r} km</span>
                        </button>
                    ))}
                </div>
                <div className="row">
                    <button className="btn-primary" onClick={saveCity}>Save location</button>
                    {home && <button className="btn-outline" onClick={() => attempt(() => saveHome(null), 'Location cleared')}>Clear</button>}
                </div>
            </>)}

            {card(2, <>
                <h2>Interests</h2>
                <p className="hint">Jobs must match one of these to show up, and Picks rank by how many match. Applies from the next scan.</p>
                <div className="kw-box" onClick={() => document.getElementById('kw-input').focus()}>
                    {keywords.map(k => (
                        <motion.span key={k} className="kw" layout initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}>
                            {k}<button type="button" aria-label={`Remove ${k}`} onClick={() => setKeywords(keywords.filter(x => x !== k))}><IconX /></button>
                        </motion.span>
                    ))}
                    <input id="kw-input" value={kwInput} placeholder="Add a keyword, press Enter" aria-label="Add interest keyword"
                           onChange={e => setKwInput(e.target.value)}
                           onKeyDown={e => {
                               if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addKeyword(); }
                               if (e.key === 'Backspace' && !kwInput && keywords.length) setKeywords(keywords.slice(0, -1));
                           }} />
                </div>
                <div className="row">
                    <button className="btn-primary" onClick={() => attempt(() => saveSettings({ keywords: keywords.join(', ') }), 'Interests saved. They apply from the next scan.')}>Save interests</button>
                </div>
            </>)}

            {card(3, <>
                <h2>Notifications</h2>
                <p className="hint">Install the ntfy app and subscribe to this private topic for deadline reminders and the morning digest.</p>
                <code className="code-box">{settings?.ntfy_topic || 'Loading'}</code>
                <div className="row">
                    <button className="btn-outline" onClick={copyTopic}><IconCopy />Copy topic</button>
                    <button className="btn-outline" onClick={() => attempt(async () => {
                        const r = await api('/api/notify/test', { method: 'POST' });
                        if (r.status !== 'ok') throw new Error('push');
                    }, 'Test notification sent')}>Send a test notification</button>
                </div>
            </>)}

            {card(4, <>
                <h2>This device</h2>
                <p className="hint">Keys: <kbd>Ctrl K</kbd> search, <kbd>g</kbd> then <kbd>h f m c b s</kbd> to jump between pages.</p>
                <div className="row">
                    <button className="btn-outline" onClick={lock}><IconLock />Lock this device</button>
                </div>
                <p className="hint" style={{ marginTop: 14 }}>Read the <a href="/terms.html">terms of use</a> and the <a href="/privacy.html">privacy policy</a>.</p>
            </>)}
        </div>
    );
}
