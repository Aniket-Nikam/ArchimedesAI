import { apiFetch } from '../api';
import { useState, useCallback } from 'react';
import { UploadCloud, FileText, XCircle, X, ChevronDown, ChevronUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function PdfUpload({ user, onComplete }: { user: any, onComplete: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [results, setResults] = useState<any>(null);
  const [expanded, setExpanded] = useState(true);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragging(true);
    else if (e.type === 'dragleave') setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setStatus('idle');
      } else {
        setErrorMsg('Only PDF files are supported.');
        setStatus('error');
      }
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setErrorMsg('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', String(user.id));

    try {
      const res = await apiFetch('/api/upload/', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }

      setStatus('analyzing');
      const data = await res.json();
      setResults(data);
      setStatus('success');
      onComplete();
    } catch (e: any) {
      setErrorMsg(e.message);
      setStatus('error');
    }
  };

  const reset = () => {
    setFile(null);
    setStatus('idle');
    setResults(null);
    setErrorMsg('');
  };

  if (status === 'success' && results) {
    return (
      <div className="pdf-results-panel">
        <div className="pdf-results-header" onClick={() => setExpanded(!expanded)}>
          <div className="pdf-header-left">
            <FileText size={16} className="text-accent" />
            <span className="pdf-title">{results.metadata.title || file?.name}</span>
            <span className="pdf-badge">PDF Analysis</span>
          </div>
          <div className="pdf-header-right">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            <button className="pdf-close" onClick={reset}><X size={14} /></button>
          </div>
        </div>

        {expanded && (
          <div className="pdf-results-body">
            <div className="pdf-meta-grid">
              <div className="pdf-meta-item">
                <span className="pdf-meta-label">Length</span>
                <span className="pdf-meta-value">{results.pages} pages</span>
              </div>
              <div className="pdf-meta-item">
                <span className="pdf-meta-label">Related Work Found</span>
                <span className="pdf-meta-value">{results.related_papers?.length || 0} papers</span>
              </div>
            </div>

            <div className="pdf-analysis-section">
              <h4>Abstract & Claims</h4>
              <p className="pdf-abstract">{results.metadata.abstract}</p>
              
              <div className="pdf-claims">
                {results.metadata.key_claims?.map((claim: string, i: number) => (
                  <div key={i} className="pdf-claim-item">
                    <span className="pdf-claim-bullet">•</span>
                    {claim}
                  </div>
                ))}
              </div>
            </div>

            <div className="pdf-analysis-section">
              <h4>Literature Verification</h4>
              <div className="pdf-markdown">
                <p className="workspace-notice">This comparison uses short text excerpts and limited related literature. It cannot establish missing citations or validate the full paper.</p>
                <ReactMarkdown>{results.claim_analysis}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="pdf-upload-container">
      <div
        className={`pdf-dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <UploadCloud size={32} className="pdf-upload-icon" />
            <p>Drag & drop a PDF paper here</p>
            <span>or <label className="pdf-browse">browse files<input type="file" accept="application/pdf" onChange={e => {
              if (e.target.files?.length) {
                setFile(e.target.files[0]);
                setStatus('idle');
              }
            }} hidden /></label></span>
          </>
        ) : (
          <div className="pdf-selected">
            <FileText size={24} className="text-accent" />
            <div className="pdf-file-info">
              <span className="pdf-filename">{file.name}</span>
              <span className="pdf-filesize">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <button className="pdf-remove" onClick={reset}><X size={16} /></button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="pdf-error">
          <XCircle size={14} />
          {errorMsg}
        </div>
      )}

      {file && status === 'idle' && (
        <button className="pdf-submit-btn" onClick={handleUpload}>
          Analyze Paper
        </button>
      )}

      {(status === 'uploading' || status === 'analyzing') && (
        <div className="pdf-loading">
          <div className="spinner"></div>
          <span>{status === 'uploading' ? 'Uploading PDF...' : 'AI is reading and verifying claims against literature...'}</span>
        </div>
      )}
    </div>
  );
}
