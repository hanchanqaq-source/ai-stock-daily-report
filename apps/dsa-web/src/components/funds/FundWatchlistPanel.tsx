import type React from 'react';
import { Pencil, Plus, Save, Star, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { usePortfolioUsers, type FundWatchlistItem } from '../../contexts/PortfolioUserContext';
import type { UiLanguage } from '../../i18n/uiText';
import { Card, EmptyState, InlineAlert } from '../common';

type FundWatchlistPanelProps = {
  language: UiLanguage;
};

type Feedback = { variant: 'success' | 'danger'; message: string } | null;

const FundWatchlistPanel: React.FC<FundWatchlistPanelProps> = ({ language }) => {
  const {
    activeUser,
    activeFundWatchlist,
    persistenceStatus,
    addFundWatchlistItem,
    updateFundWatchlistItem,
    removeFundWatchlistItem,
  } = usePortfolioUsers();
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingRemoveId, setPendingRemoveId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [saving, setSaving] = useState(false);

  const resetForm = () => {
    setCode('');
    setName('');
    setNotes('');
    setEditingId(null);
  };

  const startEditing = (item: FundWatchlistItem) => {
    setCode(item.code);
    setName(item.name);
    setNotes(item.notes ?? '');
    setEditingId(item.id);
    setPendingRemoveId(null);
    setFeedback(null);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const normalizedName = name.trim().replace(/\s+/g, ' ');
    const normalizedNotes = notes.trim() || undefined;
    if (!/^\d{6}$/.test(code) || !normalizedName) {
      setFeedback({
        variant: 'danger',
        message: language === 'zh' ? '请输入 6 位基金代码和基金名称。' : 'Enter a six-digit fund code and fund name.',
      });
      return;
    }
    if (activeFundWatchlist.some((item) => item.code === code && item.id !== editingId)) {
      setFeedback({
        variant: 'danger',
        message: language === 'zh' ? '该基金已经在当前用户的自选中。' : 'This fund is already in the current user watchlist.',
      });
      return;
    }

    setSaving(true);
    setFeedback(null);
    const success = editingId
      ? await updateFundWatchlistItem({ id: editingId, code, name: normalizedName, notes: normalizedNotes })
      : await addFundWatchlistItem({ code, name: normalizedName, notes: normalizedNotes });
    setSaving(false);
    if (!success) {
      setFeedback({
        variant: 'danger',
        message: language === 'zh' ? '保存失败，已重新读取本机数据库状态，请重试。' : 'Save failed. Local database state was reloaded; please retry.',
      });
      return;
    }
    setFeedback({
      variant: 'success',
      message: language === 'zh'
        ? (editingId ? '基金自选已更新。' : '基金已加入自选。')
        : (editingId ? 'Fund watchlist item updated.' : 'Fund added to watchlist.'),
    });
    resetForm();
  };

  const confirmRemove = async (itemId: string) => {
    setFeedback(null);
    const success = await removeFundWatchlistItem(itemId);
    setPendingRemoveId(null);
    if (success) {
      setFeedback({
        variant: 'success',
        message: language === 'zh' ? '基金已移出自选，不影响基金持仓。' : 'Fund removed from watchlist. Fund holdings were not changed.',
      });
    } else {
      setFeedback({
        variant: 'danger',
        message: language === 'zh' ? '移出失败，已重新读取本机数据库状态，请重试。' : 'Removal failed. Local database state was reloaded; please retry.',
      });
    }
  };

  const busy = saving || persistenceStatus === 'loading';

  return (
    <div className="space-y-4" data-testid="fund-watchlist-panel">
      {persistenceStatus === 'error' && (
        <InlineAlert
          variant="danger"
          title={language === 'zh' ? '本机保存状态异常' : 'Local persistence error'}
          message={language === 'zh' ? '界面已尝试重新读取数据库；请检查本机后端后重试。' : 'The page tried to reload the database state. Check the local backend and retry.'}
        />
      )}
      {feedback && <InlineAlert variant={feedback.variant} message={feedback.message} />}

      <Card padding="md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-foreground">
              {editingId
                ? (language === 'zh' ? '编辑基金自选' : 'Edit fund watchlist item')
                : (language === 'zh' ? '添加基金自选' : 'Add fund to watchlist')}
            </h2>
            <p className="mt-1 text-sm text-secondary-text">
              {language === 'zh'
                ? `只保存到 ${activeUser.name} 的本机自选列表，不会自动加入持仓。`
                : `Saved only to ${activeUser.name}'s local watchlist; it is not added to holdings.`}
            </p>
          </div>
          <span className="rounded-full border border-border px-3 py-1 text-xs text-secondary-text">
            {language === 'zh' ? `当前 ${activeFundWatchlist.length} 只` : `${activeFundWatchlist.length} funds`}
          </span>
        </div>

        <form className="mt-5 grid gap-4 lg:grid-cols-2" onSubmit={submit}>
          <label className="text-sm text-secondary-text">
            <span className="mb-1 block">{language === 'zh' ? '基金代码' : 'Fund code'}</span>
            <input
              aria-label={language === 'zh' ? '基金代码' : 'Fund code'}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-cyan"
              inputMode="numeric"
              maxLength={6}
              placeholder="例如 000001"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            />
          </label>
          <label className="text-sm text-secondary-text">
            <span className="mb-1 block">{language === 'zh' ? '基金名称' : 'Fund name'}</span>
            <input
              aria-label={language === 'zh' ? '基金名称' : 'Fund name'}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-cyan"
              maxLength={100}
              placeholder={language === 'zh' ? '输入基金全称' : 'Enter the fund name'}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="text-sm text-secondary-text lg:col-span-2">
            <span className="mb-1 block">{language === 'zh' ? '备注（可选）' : 'Notes (optional)'}</span>
            <textarea
              aria-label={language === 'zh' ? '备注（可选）' : 'Notes (optional)'}
              className="min-h-24 w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-cyan"
              maxLength={1000}
              placeholder={language === 'zh' ? '例如：等待回调、关注行业变化' : 'For example: wait for pullback, monitor sector changes'}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2 lg:col-span-2">
            <button
              type="submit"
              className="btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={busy || !/^\d{6}$/.test(code) || !name.trim()}
            >
              {editingId ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {saving
                ? (language === 'zh' ? '保存中' : 'Saving')
                : editingId
                  ? (language === 'zh' ? '保存修改' : 'Save changes')
                  : (language === 'zh' ? '加入自选' : 'Add to watchlist')}
            </button>
            {editingId && (
              <button type="button" className="btn-secondary flex items-center gap-2" disabled={busy} onClick={resetForm}>
                <X className="h-4 w-4" />{language === 'zh' ? '取消编辑' : 'Cancel edit'}
              </button>
            )}
          </div>
        </form>
      </Card>

      {activeFundWatchlist.length === 0 ? (
        <EmptyState
          icon={<Star className="h-7 w-7" />}
          title={language === 'zh' ? '当前用户还没有基金自选' : 'No funds in this user watchlist'}
          description={language === 'zh' ? '在上方手动输入基金代码和名称；本阶段不会自动联网补全。' : 'Enter a fund code and name above. This stage does not fetch data automatically.'}
        />
      ) : (
        <Card padding="none">
          <div className="divide-y divide-border" data-testid="fund-watchlist-items">
            {activeFundWatchlist.map((item) => (
              <article key={item.id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-foreground">{item.name}</h3>
                    <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-secondary-text">{item.code}</span>
                  </div>
                  <p className="mt-2 break-words text-sm text-secondary-text">
                    {item.notes || (language === 'zh' ? '暂无备注' : 'No notes')}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <button type="button" className="btn-secondary flex items-center gap-2 text-sm" disabled={busy} onClick={() => startEditing(item)}>
                    <Pencil className="h-4 w-4" />{language === 'zh' ? '编辑' : 'Edit'}
                  </button>
                  {pendingRemoveId === item.id ? (
                    <>
                      <button type="button" className="btn-secondary flex items-center gap-2 border-red-400/40 text-sm text-red-100 hover:bg-red-500/15" disabled={busy} onClick={() => void confirmRemove(item.id)}>
                        <Trash2 className="h-4 w-4" />{language === 'zh' ? '确认移出' : 'Confirm remove'}
                      </button>
                      <button type="button" className="btn-secondary text-sm" disabled={busy} onClick={() => setPendingRemoveId(null)}>
                        {language === 'zh' ? '取消' : 'Cancel'}
                      </button>
                    </>
                  ) : (
                    <button type="button" className="btn-secondary flex items-center gap-2 text-sm" disabled={busy} onClick={() => setPendingRemoveId(item.id)}>
                      <Trash2 className="h-4 w-4" />{language === 'zh' ? '移出自选' : 'Remove'}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default FundWatchlistPanel;
