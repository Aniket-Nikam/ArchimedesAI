import { apiFetch } from '../api';
import { useState } from 'react';
import { Table, Download, Loader, X } from 'lucide-react';

export default function DataMatrix({ report }: { report: any }) {
  const [data, setData] = useState<any[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const generateMatrix = async () => {
    setIsLoading(true);
    setError('');
    try {
      const allPapers = [
        ...(report.seminal || []),
        ...(report.citations || []),
        ...(report.citations_depth2 || []),
      ];
      
      // Deduplicate
      const seen = new Set<string>();
      const papers = allPapers.filter((p: any) => {
        if (seen.has(p.title)) return false;
        seen.add(p.title);
        return true;
      });

      const res = await apiFetch('/api/extract/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers: papers.slice(0, 15) }) // Send top 15
      });
      
      if (!res.ok) throw new Error('Failed to generate matrix');
      
      const json = await res.json();
      if (json.extracted_data && Array.isArray(json.extracted_data)) {
        setData(json.extracted_data);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!data) return;
    const escapeCsv = (val: string) => `"${String(val || '').replace(/"/g, '""')}"`;
    const headers = ['Title', 'Methodology', 'Sample Size', 'Key Metric', 'Limitations'];
    let csv = headers.map(escapeCsv).join(',') + '\n';
    
    for (const row of data) {
      const vals = [
        row.title || '',
        row.methodology || '',
        row.sample_size || '',
        row.key_metric || '',
        row.limitations || ''
      ].map(escapeCsv);
      csv += vals.join(',') + '\n';
    }
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'archimedes_data_matrix.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!data && !isLoading && !error) {
    return (
      <div className="matrix-prompt">
        <button className="matrix-generate-btn" onClick={generateMatrix}>
          <Table size={16} />
          Generate Data Extraction Matrix
        </button>
      </div>
    );
  }

  return (
    <div className="matrix-container">
      <div className="matrix-header">
        <div className="matrix-title">
          <Table size={16} />
          Data Extraction Matrix
        </div>
        <div className="matrix-actions">
          {data && (
            <button className="matrix-dl-btn" onClick={handleDownload} title="Download CSV">
              <Download size={14} />
            </button>
          )}
          <button className="matrix-close-btn" onClick={() => { setData(null); setError(''); }}>
            <X size={14} />
          </button>
        </div>
      </div>
      
      <div className="matrix-content">
        {isLoading ? (
          <div className="matrix-loading">
            <Loader size={20} className="spin" />
            <span>Extracting statistical data from top 15 papers using AI...</span>
          </div>
        ) : error ? (
          <div className="matrix-error">⚠️ {error}</div>
        ) : data && data.length > 0 ? (
          <div className="matrix-table-wrapper">
            <table className="matrix-table">
              <thead>
                <tr>
                  <th>Paper Title</th>
                  <th>Methodology</th>
                  <th>Sample Size (N)</th>
                  <th>Key Metric</th>
                  <th>Limitations</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i}>
                    <td className="m-title">{row.title}</td>
                    <td>{row.methodology}</td>
                    <td>{row.sample_size}</td>
                    <td>{row.key_metric}</td>
                    <td>{row.limitations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="matrix-empty">No data extracted.</div>
        )}
      </div>
    </div>
  );
}
