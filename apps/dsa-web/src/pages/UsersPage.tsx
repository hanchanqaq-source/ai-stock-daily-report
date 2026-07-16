import type React from 'react';
import { useEffect, useState } from 'react';
import { Check, Pencil, Trash2, UserPlus, UsersRound } from 'lucide-react';
import { Card, InlineAlert } from '../components/common';
import { usePortfolioUsers } from '../contexts/PortfolioUserContext';
import { useUiLanguage } from '../contexts/UiLanguageContext';

const TEXT = {
  zh: {
    documentTitle: '用户管理 - DSA', title: '用户管理',
    description: '为本人、家人或其他独立持仓建立用户档案。',
    addTitle: '新增用户', placeholder: '输入用户名称，例如：家人A', add: '添加用户',
    listTitle: '用户档案', current: '当前用户', primary: '默认用户', switchTo: '切换到此用户',
    rename: '重命名', save: '保存', remove: '删除用户', emptyName: '请输入用户名称。',
    noticeTitle: 'Build B 数据边界', notice: '股票持仓和基金持仓已按当前用户分开保存于本次运行内存；切换用户不会串用。刷新页面仍会恢复，正式持久化属于 Build E。',
  },
  en: {
    documentTitle: 'User Profiles - DSA', title: 'User profiles',
    description: 'Create separate profiles for yourself, family members, or other portfolios.',
    addTitle: 'Add user', placeholder: 'Enter a user name, for example: Family A', add: 'Add user',
    listTitle: 'Profiles', current: 'Current user', primary: 'Default user', switchTo: 'Switch to this user',
    rename: 'Rename', save: 'Save', remove: 'Delete user', emptyName: 'Enter a user name.',
    noticeTitle: 'Build B data boundary', notice: 'Stock and fund holdings are separated by active user in runtime memory. Switching users does not mix data. Refresh still resets data; durable persistence belongs to Build E.',
  },
} as const;

const UsersPage: React.FC = () => {
  const { language } = useUiLanguage();
  const text = TEXT[language];
  const { users, activeUser, activeUserId, addUser, renameUser, removeUser, setActiveUserId } = usePortfolioUsers();
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [message, setMessage] = useState<string | null>(null);

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
