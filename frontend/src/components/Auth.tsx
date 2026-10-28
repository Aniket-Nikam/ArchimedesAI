import { apiFetch, setCsrfToken } from '../api';
import { useState } from 'react';
import { LogIn, UserPlus, User, Mail, Lock, AlertCircle } from 'lucide-react';

export default function Auth({ onLogin }: { onLogin: (user: any) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pending) return;
    setPending(true);
    setError('');
    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
    const payload = isLogin ? { username, password } : { username, email, password };

    try {
      const res = await apiFetch(`${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Authentication failed');
      setCsrfToken(data.csrf_token);
      onLogin(data.user);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  };

  const switchTab = (login: boolean) => {
    setIsLogin(login);
    setError('');
  };

  return (
    <div className="auth-container">
      {/* Left — Branding */}
      <div className="auth-brand">
        <div className="brand-content">
          <div className="brand-logo" aria-hidden="true">A.</div>
          <h1 className="brand-title">Archimedes</h1>
          <p className="brand-subtitle">
            Start with a question. Build an evidence trail.
          </p>

          <div className="brand-features">
            <div className="brand-feature">
              <span className="feature-icon">🔍</span>
              <span className="feature-text">Discover papers across arXiv, Semantic Scholar and PubMed</span>
            </div>
            <div className="brand-feature">
              <span className="feature-icon">🔗</span>
              <span className="feature-text">Follow citation connections and keep a reading list</span>
            </div>
            <div className="brand-feature">
              <span className="feature-icon">🧠</span>
              <span className="feature-text">Compare findings, methods and gaps with AI assistance</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right — Form */}
      <div className="auth-form-panel">
        <div className="auth-form-container">
          <div className="auth-form-header">
            <h2 className="auth-form-title">
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="auth-form-desc">
              {isLogin
                ? 'Sign in to continue your research journey'
                : 'Start exploring academic research today'}
            </p>
          </div>

          <div className="auth-tabs">
            <button
              className={`auth-tab ${isLogin ? 'active' : ''}`}
              onClick={() => switchTab(true)}
            >
              Sign In
            </button>
            <button
              className={`auth-tab ${!isLogin ? 'active' : ''}`}
              onClick={() => switchTab(false)}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="input-group">
              <input
                type="text"
                aria-label="Username"
                autoComplete="username"
                maxLength={30}
                placeholder="Username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
              />
              <User size={18} className="input-icon" />
            </div>

            {!isLogin && (
              <div className="input-group">
                <input
                  type="email"
                  aria-label="Email"
                  autoComplete="email"
                  maxLength={254}
                  placeholder="Email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
                <Mail size={18} className="input-icon" />
              </div>
            )}

            <div className="input-group">
              <input
                type="password"
                aria-label="Password"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                minLength={isLogin ? undefined : 8}
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
              <Lock size={18} className="input-icon" />
            </div>

            {error && (
              <div className="auth-error" role="alert">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <button type="submit" className="submit-btn" disabled={pending} aria-busy={pending}>
              {isLogin ? (
                <><LogIn size={18} /> Sign In</>
              ) : (
                <><UserPlus size={18} /> Create Account</>
              )}
            </button>
          </form>
          <p className="auth-fine-print">Your research and reading list stay in your account. AI output is a starting point: always verify the original papers.</p>
        </div>
      </div>
    </div>
  );
}
