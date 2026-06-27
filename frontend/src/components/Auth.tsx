import { useState } from 'react';
import { LogIn, UserPlus, User, Mail, Lock, AlertCircle } from 'lucide-react';

export default function Auth({ onLogin }: { onLogin: (user: any) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
    const payload = isLogin ? { username, password } : { username, email, password };

    try {
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Authentication failed');
      onLogin(data.user);
    } catch (err: any) {
      setError(err.message);
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
          <div className="brand-logo">🧬</div>
          <h1 className="brand-title">Archimedes</h1>
          <p className="brand-subtitle">
            Your AI-powered research companion. Search academic databases, trace citation trails, and synthesize knowledge — all in one place.
          </p>

          <div className="brand-features">
            <div className="brand-feature">
              <span className="feature-icon">🔍</span>
              <span className="feature-text">Search across arXiv, Semantic Scholar, PubMed & Google Scholar</span>
            </div>
            <div className="brand-feature">
              <span className="feature-icon">🔗</span>
              <span className="feature-text">Automatic citation tracing with 2-level depth exploration</span>
            </div>
            <div className="brand-feature">
              <span className="feature-icon">🧠</span>
              <span className="feature-text">AI-powered synthesis with contradiction & gap analysis</span>
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
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
              <Lock size={18} className="input-icon" />
            </div>

            {error && (
              <div className="auth-error">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <button type="submit" className="submit-btn">
              {isLogin ? (
                <><LogIn size={18} /> Sign In</>
              ) : (
                <><UserPlus size={18} /> Create Account</>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
