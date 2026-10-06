import React, { useEffect, useState } from 'react';
import {
  getRecoveredSources,
  recoverSources,
  reviewRecoveredSource,
  RecoveredSourceItem,
  apiErrorMessage,
} from '../../services/api';

interface Props {
  projectId: string;
  reviewer: string;
}

export const SourceRecoveryPanel: React.FC<Props> = ({ projectId, reviewer }) => {
  const [items, setItems] = useState<RecoveredSourceItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getRecoveredSources(projectId).then(setItems).catch(() => setItems([]));
  }, [projectId]);

  const run = async () => {
    setBusy(true);
    setError('');
    try {
      await recoverSources(projectId);
      setItems(await getRecoveredSources(projectId));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const review = async (id: string, decision: 'approved' | 'rejected') => {
    try {
      await reviewRecoveredSource(projectId, id, decision, reviewer);
      setItems(await getRecoveredSources(projectId));
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  return (
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm" aria-label="استرجاع المصادر">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-bold">استرجاع المصادر (آيات وأحاديث)</h2>
        <button type="button" disabled={busy} onClick={run} className="rounded-lg border px-3 py-1 text-xs">
          {busy ? 'جارٍ البحث...' : 'استرجاع المصادر'}
        </button>
      </div>
      {error && <p className="mb-2 text-xs text-rose-700">{error}</p>}
      {items.length === 0 && <p className="text-xs text-slate-400">لا توجد نتائج بعد.</p>}
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs font-bold">
              {item.source} — {item.reference} ({Math.round(item.confidence * 100)}%)
            </p>
            <p className="mt-1 whitespace-pre-wrap text-slate-700">{item.full_text}</p>
            {item.status === 'candidate' && (
              <div className="mt-2 flex gap-2">
                <button type="button" onClick={() => review(item.id, 'approved')} className="rounded border px-2 py-0.5 text-xs">
                  اعتماد
                </button>
                <button type="button" onClick={() => review(item.id, 'rejected')} className="rounded border px-2 py-0.5 text-xs">
                  رفض
                </button>
              </div>
            )}
            {item.status !== 'candidate' && (
              <span className="text-[11px] text-emerald-700">{item.status === 'rejected' ? 'مرفوض' : 'مصدر مسترجع'}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
};

