import { useState } from 'react';
import { motion } from 'motion/react';
import { unlock } from '../api.js';
import { useRadar } from '../store.jsx';
import { RadarMark } from './Icons.jsx';

export default function Login() {
    const { setLocked } = useRadar();
    const [token, setToken] = useState('');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    const submit = async e => {
        e.preventDefault();
        setBusy(true);
        setError('');
        try {
            if (await unlock(token.trim())) setLocked(false);
            else setError('That token was not accepted. Copy it again from the server log.');
        } catch {
            setError('Could not reach the server. Check that it is running.');
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="login">
            <motion.form className="login-card" onSubmit={submit}
                         initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}>
                <RadarMark size={48} />
                <h1>Radar</h1>
                <p>Internships, jobs and hackathons from 70+ sites. Enter the access token printed when the server
                    starts. It is also saved in <code>data/access_token.txt</code>.</p>
                <label htmlFor="token">Access token</label>
                <input id="token" type="password" autoComplete="current-password" value={token}
                       onChange={e => setToken(e.target.value)} required autoFocus />
                {error && <p className="login-error" role="alert">{error}</p>}
                <button className="btn-primary" type="submit" disabled={busy}>{busy ? 'Checking' : 'Unlock'}</button>
                <div className="legal"><a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a></div>
            </motion.form>
        </div>
    );
}
