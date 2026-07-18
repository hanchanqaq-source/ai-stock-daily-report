import type React from 'react';
import { useEffect, useState } from 'react';
import { Check, Download, Pencil, RotateCcw, Trash2, Upload, UserPlus, UsersRound } from 'lucide-react';
import { Card, InlineAlert } from '../components/common';
import { usePortfolioUsers } from '../contexts/PortfolioUserContext';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { workspacePortfolioApi, type WorkspacePortfolioBackupPreviewDto, type WorkspacePortfolioRestorePointDto } from '../api/workspacePortfolio';

const TEXT = {
  zh: {
    documentTitle: '用户管理 - DSA', title: '用户管理',
    description: '为本人、家人或其他独立持仓建立用户档案。',
    addTitle: '新增用户', placeholder: '输入用户名称，例如：家人A', add: '添加用户',
    listTitle: '用户档案', current: '当前用户', primary: '默认用户', switchTo: '切换到此用户',
    rename: '重命名', save: '保存', remove: '删除用户', emptyName: '请输入用户名称。',
    storageError: '本地数据库暂时不可用；当前页面改动可能不会在重启后保留，请稍后重试。',
    noticeTitle: '本地持久化', notice: '用户、股票持仓和基金持仓按当前用户分开保存到本机数据库；刷新页面或重启程序后仍会保留。',
    backupTitle: '本机数据备份与恢复', backupDescription: '仅导出用户、股票快速持仓和基金快速持仓；不包含设置、密钥、DPAPI 凭证或日志。',
    export: '导出备份文件', choose: '选择备份文件', noFile: '尚未选择备份文件', preview: '预览导入内容',
    replaceNotice: '导入会覆盖当前本机工作台数据；确认前会自动创建一个本机恢复点。', confirmImport: '确认覆盖导入',
    previewSummary: '将导入 {users} 个用户、{stocks} 条股票持仓、{funds} 条基金持仓。', imported: '导入完成，已创建恢复点。',
    restoreLatest: '恢复最近一个恢复点', restored: '恢复完成，已创建新的恢复点。', backupError: '备份文件无效或本机数据库暂时不可用，请检查文件后重试。',
  },
  en: {
    documentTitle: 'User Profiles - DSA', title: 'User profiles',
    description: 'Create separate profiles for yourself, family members, or other portfolios.',
    addTitle: 'Add user', placeholder: 'Enter a user name, for example: Family A', add: 'Add user',
    listTitle: 'Profiles', current: 'Current user', primary: 'Default user', switchTo: 'Switch to this user',
    rename: 'Rename', save: 'Save', remove: 'Delete user', emptyName: 'Enter a user name.',
    storageError: 'The local database is temporarily unavailable. Current changes may not survive a restart.',
    noticeTitle: 'Local persistence', notice: 'Users, stock holdings, and fund holdings are stored separately per user in the local database and survive refreshes and restarts.',
    backupTitle: 'Local data backup and restore', backupDescription: 'Only users and quick stock/fund holdings are exported. Settings, secrets, DPAPI credentials, and logs are excluded.',
    export: 'Export backup file', choose: 'Choose backup file', noFile: 'No backup file selected', preview: 'Preview import',
    replaceNotice: 'Import replaces this device’s workspace data. A local restore point is created before confirmation.', confirmImport: 'Confirm replace and import',
    previewSummary: 'Will import {users} users, {stocks} stock holdings, and {funds} fund holdings.', imported: 'Import completed and a restore point was created.',
    restoreLatest: 'Restore latest restore point', restored: 'Restore completed and a new restore point was created.', backupError: 'The backup file is invalid or local storage is unavailable. Check the file and try again.',
  },
} as const;

const UsersPage: React.FC = () => {
  const { language } = useUiLanguage();
  const text = TEXT[language];
  const { users, activeUser, activeUserId, persistenceStatus, addUser, renameUser, removeUser, setActiveUserId, replaceWorkspaceState } = usePortfolioUsers();
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [backupData, setBackupData] = useState<unknown>(null);
  const [preview, setPreview] = useState<WorkspacePortfolioBackupPreviewDto | null>(null);
  const [restorePoints, setRestorePoints] = useState<WorkspacePortfolioRestorePointDto[]>([]);
  const [backupBusy, setBackupBusy] = useState(false);

  useEffect(() => { document.title = text.documentTitle; }, [text.documentTitle]);

  const handleAdd = () => {
    const created = addUser(newName);
    if (!created) { setMessage(text.emptyName); return; }
    setNewName(''); setMessage(null); setActiveUserId(created.id);
  };

  const saveRename = () => {
    if (!editingId || !renameUser(editingId, editingName)) { setMessage(text.emptyName); return; }
    setEditingId(null); setEditingName(''); setMessage(null);
  };

  const loadRestorePoints = async () => setRestorePoints(await workspacePortfolioApi.listRestorePoints());

  const exportBackup = async () => {
    setBackupBusy(true); setMessage(null);
    try {
      const backup = await workspacePortfolioApi.exportBackup();
      const url = URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url; link.download = `股票基金质量分析系统-本机数据备份-${new Date().toISOString().slice(0, 10)}.json`;
      link.click(); URL.revokeObjectURL(url);
    } catch { setMessage(text.backupError); } finally { setBackupBusy(false); }
  };

  const chooseBackup = async (file: File | null) => {
    setBackupFile(file); setPreview(null); setBackupData(null); setMessage(null);
    if (!file) return;
    try { setBackupData(JSON.parse(await file.text())); } catch { setMessage(text.backupError); }
  };

  const previewImport = async () => {
    if (!backupData) return;
    setBackupBusy(true); setMessage(null);
    try { setPreview(await workspacePortfolioApi.previewBackup(backupData)); } catch { setPreview(null); setMessage(text.backupError); } finally { setBackupBusy(false); }
  };

  const confirmImport = async () => {
    if (!backupData || !preview) return;
    setBackupBusy(true); setMessage(null);
    try {
      const result = await workspacePortfolioApi.importBackup(backupData);
      replaceWorkspaceState(result.state); setMessage(text.imported); setPreview(null); setBackupFile(null); setBackupData(null);
      await loadRestorePoints();
    } catch { setMessage(text.backupError); } finally { setBackupBusy(false); }
  };

  const restoreLatest = async () => {
    const latest = restorePoints[0];
    if (!latest) return;
    setBackupBusy(true); setMessage(null);
    try { const result = await workspacePortfolioApi.restoreBackup(latest.id); replaceWorkspaceState(result.state); setMessage(text.restored); await loadRestorePoints(); } catch { setMessage(text.backupError); } finally { setBackupBusy(false); }
  };

  useEffect(() => { void loadRestorePoints().catch(() => undefined); }, []);

  return (
    <div className="min-h-screen space-y-5 p-4 md:p-6" data-testid="users-workbench">
      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <UsersRound className="h-6 w-6 text-cyan" aria-hidden="true" />
          <h1 className="text-xl font-semibold text-foreground md:text-2xl">{text.title}</h1>
        </div>
        <p className="text-sm text-secondary">{text.description}</p>
        <p className="text-xs text-secondary">{text.current}: <span className="font-medium text-foreground">{activeUser.name}</span></p>
      </section>

      <InlineAlert variant="info" title={text.noticeTitle} message={text.notice} />
      {persistenceStatus === 'error' ? <InlineAlert variant="warning" message={text.storageError} /> : null}

      <Card padding="md">
        <h2 className="font-semibold text-foreground">{text.backupTitle}</h2>
        <p className="mt-1 text-xs leading-5 text-secondary">{text.backupDescription}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className="btn-secondary flex items-center gap-2 text-sm" disabled={backupBusy} onClick={() => void exportBackup()}><Download className="h-4 w-4" />{text.export}</button>
          <label className="btn-secondary flex cursor-pointer items-center gap-2 text-sm"><Upload className="h-4 w-4" />{text.choose}<input className="sr-only" type="file" accept="application/json,.json" onChange={(event) => void chooseBackup(event.target.files?.[0] ?? null)} /></label>
          {restorePoints[0] ? <button type="button" className="btn-secondary flex items-center gap-2 text-sm" disabled={backupBusy} onClick={() => void restoreLatest()}><RotateCcw className="h-4 w-4" />{text.restoreLatest}</button> : null}
        </div>
        <p className="mt-3 text-xs text-secondary">{backupFile ? backupFile.name : text.noFile}</p>
        {backupData && !preview ? <button type="button" className="btn-secondary mt-3 text-sm" disabled={backupBusy} onClick={() => void previewImport()}>{text.preview}</button> : null}
        {preview ? <div className="mt-3 rounded-xl border border-amber-400/25 bg-amber-400/5 p-3 text-sm"><p className="text-foreground">{text.previewSummary.replace('{users}', String(preview.users)).replace('{stocks}', String(preview.stockHoldings)).replace('{funds}', String(preview.fundHoldings))}</p><p className="mt-1 text-xs text-secondary">{text.replaceNotice}</p><button type="button" className="btn-primary mt-3 text-sm" disabled={backupBusy} onClick={() => void confirmImport()}>{text.confirmImport}</button></div> : null}
      </Card>

      <Card padding="md">
        <h2 className="font-semibold text-foreground">{text.addTitle}</h2>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            className="input-surface input-focus-glow h-11 flex-1 rounded-xl border bg-transparent px-4 text-sm text-foreground"
            value={newName}
            placeholder={text.placeholder}
            aria-label={text.placeholder}
            onChange={(event) => setNewName(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') handleAdd(); }}
          />
          <button type="button" className="btn-primary flex h-11 items-center justify-center gap-2 px-5 text-sm" onClick={handleAdd}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />{text.add}
          </button>
        </div>
        {message ? <p className="mt-2 text-xs text-danger">{message}</p> : null}
      </Card>

      <section className="space-y-3">
        <h2 className="font-semibold text-foreground">{text.listTitle}</h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {users.map((user) => {
            const active = user.id === activeUserId;
            const editing = user.id === editingId;
            return (
              <Card key={user.id} padding="md" className={active ? 'border-cyan/50 bg-cyan/[0.04]' : ''}>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    {editing ? (
                      <input
                        className="input-surface input-focus-glow h-10 w-full rounded-xl border bg-transparent px-3 text-sm text-foreground"
                        value={editingName}
                        aria-label={text.rename}
                        onChange={(event) => setEditingName(event.target.value)}
                        onKeyDown={(event) => { if (event.key === 'Enter') saveRename(); }}
                      />
                    ) : (
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-foreground">{user.name}</p>
                        {user.isPrimary ? <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-secondary">{text.primary}</span> : null}
                        {active ? <span className="rounded-full border border-cyan/30 bg-cyan/10 px-2 py-0.5 text-[11px] text-cyan">{text.current}</span> : null}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {editing ? (
                      <button type="button" className="btn-secondary flex items-center gap-2 text-sm" onClick={saveRename}><Check className="h-4 w-4" />{text.save}</button>
                    ) : (
                      <button type="button" className="btn-secondary flex items-center gap-2 text-sm" onClick={() => { setEditingId(user.id); setEditingName(user.name); }}><Pencil className="h-4 w-4" />{text.rename}</button>
                    )}
                    {!active ? <button type="button" className="btn-secondary text-sm" onClick={() => setActiveUserId(user.id)}>{text.switchTo}</button> : null}
                    {!user.isPrimary ? <button type="button" className="btn-secondary flex items-center gap-2 text-sm" onClick={() => removeUser(user.id)}><Trash2 className="h-4 w-4" />{text.remove}</button> : null}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default UsersPage;
