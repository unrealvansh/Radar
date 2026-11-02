import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { daysUntil, listItems } from '../api.js';
import { FilterBar } from '../components/Controls.jsx';
import OppCard from '../components/OppCard.jsx';
import { useRadar } from '../store.jsx';

const INDIA = [[7.5, 68], [33.5, 97.5]];
// Standard OpenStreetMap tiles (no key needed); styles.css darkens them to match the app
const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export default function MapView({ filters, setFilters }) {
    const { home } = useRadar();
    const [items, setItems] = useState(null);
    const [selected, setSelected] = useState(null);   // city name, or 'online'
    const mapEl = useRef(null);
    const map = useRef(null);
    const layer = useRef(null);

    useEffect(() => {
        listItems({ ...filters, limit: 600 }, home).then(setItems).catch(() => setItems([]));
    }, [filters, home]);

    // Group by city; online/remote items without a place go in their own tray
    const { cities, online } = useMemo(() => {
        const byCity = new Map();
        const online = [];
        for (const it of items || []) {
            if (it.lat !== null && it.lat !== undefined && it.mode !== 'online' && it.mode !== 'remote') {
                const c = byCity.get(it.city) || { name: it.city, lat: it.lat, lon: it.lon, items: [], urgent: false };
                c.items.push(it);
                const d = daysUntil(it.deadline);
                if (d !== null && d >= 0 && d <= 3) c.urgent = true;
                byCity.set(it.city, c);
            } else if (it.mode === 'online' || it.mode === 'remote') {
                online.push(it);
            }
        }
        return { cities: [...byCity.values()].sort((a, b) => b.items.length - a.items.length), online };
    }, [items]);

    // Map setup, once
    useEffect(() => {
        const m = L.map(mapEl.current, { zoomControl: false, attributionControl: true, minZoom: 4, maxBounds: [[-5, 55], [45, 110]] });
        L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(m);
        L.control.zoom({ position: 'bottomright' }).addTo(m);
        m.fitBounds(INDIA);
        if (home) {
            L.circle([home.lat, home.lon], {
                radius: home.radius * 1000, color: '#1a8cff', weight: 1, opacity: 0.6, fillOpacity: 0.06, interactive: false,
            }).addTo(m);
            L.marker([home.lat, home.lon], {
                icon: L.divIcon({ className: '', html: '<span class="home-dot" aria-hidden="true"></span>', iconSize: [18, 18] }),
                keyboard: false, interactive: false,
            }).addTo(m);
        }
        map.current = m;
        layer.current = L.layerGroup().addTo(m);
        return () => m.remove();
    }, [home]);

    // City markers: size by count, bronze ring when something there closes within 3 days
    useEffect(() => {
        const g = layer.current;
        if (!g) return;
        g.clearLayers();
        const max = Math.max(1, ...cities.map(c => c.items.length));
        cities.forEach(c => {
            const size = Math.round(30 + 26 * Math.sqrt(c.items.length / max));
            const html = `<button class="pin ${c.urgent ? 'is-urgent' : ''} ${selected === c.name ? 'is-on' : ''}" style="--s:${size}px"
                                  aria-label="${c.name}: ${c.items.length} opportunit${c.items.length === 1 ? 'y' : 'ies'}">
                              <b>${c.items.length}</b></button>`;
            const marker = L.marker([c.lat, c.lon], {
                icon: L.divIcon({ className: 'pin-wrap', html, iconSize: [size, size] }),
                title: c.name, riseOnHover: true,
            });
            marker.on('click', () => {
                setSelected(c.name);
                map.current.flyTo([c.lat, c.lon], Math.max(map.current.getZoom(), 8), { duration: 1.1 });
            });
            g.addLayer(marker);
        });
    }, [cities, selected]);

    const selCity = cities.find(c => c.name === selected);
    const list = selected === 'online' ? online : selCity?.items || [];

    const reset = () => {
        setSelected(null);
        map.current?.flyToBounds(INDIA, { duration: 1 });
    };

    return (
        <section className="mapview">
            <div className="map" ref={mapEl} aria-label="Map of opportunities by city" />
            <div className="map-top">
                <FilterBar filters={filters} setFilters={setFilters} hideSearch />
            </div>

            <motion.div className="map-cities" initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
                <h1>{items === null ? 'Loading map' : `${cities.length} cities`}</h1>
                <ul>
                    {online.length > 0 && (
                        <li><button aria-pressed={selected === 'online'} onClick={() => setSelected('online')}>
                            <span>Online and remote</span><b>{online.length}</b></button></li>
                    )}
                    {cities.slice(0, 12).map(c => (
                        <li key={c.name}>
                            <button aria-pressed={selected === c.name} onClick={() => {
                                setSelected(c.name);
                                map.current.flyTo([c.lat, c.lon], 9, { duration: 1.1 });
                            }}>
                                <span>{c.name}{c.urgent && <i className="dot-urgent" title="Something closes within 3 days" />}</span>
                                <b>{c.items.length}</b>
                            </button>
                        </li>
                    ))}
                </ul>
            </motion.div>

            <AnimatePresence>
                {selected && (
                    <motion.aside className="map-panel" key={selected}
                                  initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}
                                  transition={{ type: 'spring', stiffness: 260, damping: 30 }}>
                        <div className="map-panel-head">
                            <h2>{selected === 'online' ? 'Online and remote' : selected}</h2>
                            <span>{list.length} open</span>
                            <button className="btn-outline" onClick={reset}>Show all of India</button>
                        </div>
                        <div className="map-panel-list">
                            {list.map((it, i) => <OppCard key={it.id} item={it} index={i} compact />)}
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </section>
    );
}
