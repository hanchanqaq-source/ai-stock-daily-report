import type React from 'react';
import { useEffect, useState } from 'react';
import { ImageUp, PlusCircle } from 'lucide-react';
import { Drawer } from '../common/Drawer';
import { InlineAlert } from '../common/InlineAlert';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import type { QuickFundHolding, QuickStockHolding } from '../../contexts/PortfolioUserContext';

type EntryMode = 'manual' | 'screenshot';
type AssetType = 'fund' | 'stock';
type EditingHolding =
  | { assetType: 'fund'; holding: QuickFundHolding }
  | { assetType: 'stock'; holding: QuickStockHolding };

type QuickHoldingEntryDrawerProps = {
  isOpen: boolean;
  initialMode: EntryMode;
  fixedAssetType?: AssetType;
  editingHolding?: EditingHolding | null;
  onClose: () => void;
};

const inputClass = 'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground';

const QuickHoldingEntryDrawerContent: React.FC<QuickHoldingEntryDrawerProps> = ({ isOpen, initialMode, fixedAssetType, editingHolding, onClose }) => {
  const { activeUser, persistenceStatus, addFundHolding, addStockHolding, updateFundHolding, updateStockHolding } = usePortfolioUsers();
  const [mode, setMode] = useState<EntryMode>(initialMode);
  const [assetType, setAssetType] = useState<AssetType>('fund');
  const selectedAssetType = fixedAssetType ?? assetType;
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [profit, setProfit] = useState('0');
  const [targetAllocation, setTargetAllocation] = useState('');
  const [quantity, setQuantity] = useState('');
  const [averageCost, setAverageCost] = useState('');
  const [securitiesAccount, setSecuritiesAccount] = useState('默认证券账户');
  const [notes, setNotes] = useState('');
  const [feedback, setFeedback] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  const [screenshotConfirmation, setScreenshotConfirmation] = useState(false);

  useEffect(() => {
    setMode(editingHolding ? 'manual' : initialMode);
    if (!editingHolding) { resetManualForm(); return; }
    setCode(editingHolding.holding.code); setName(editingHolding.holding.name); setNotes(editingHolding.holding.notes ?? '');
    if (editingHolding.assetType === 'fund') {
      setAmount(String(editingHolding.holding.amount)); setProfit(String(editingHolding.holding.profit)); setTargetAllocation(editingHolding.holding.targetAllocation == null ? '' : String(editingHolding.holding.targetAllocation));
    } else {
      setQuantity(String(editingHolding.holding.quantity)); setAverageCost(String(editingHolding.holding.averageCost)); setSecuritiesAccount(editingHolding.holding.securitiesAccount);
    }
    setFeedback('');
  // resetManualForm intentionally belongs to this component and does not need a stable identity.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingHolding, initialMode, isOpen]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const resetManualForm = () => {
    setCode('');
    setName('');
    setAmount('');
    setProfit('0');
    setTargetAllocation('');
    setQuantity('');
    setAverageCost('');
    setNotes('');
    setScreenshotConfirmation(false);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const normalizedCode = code.trim();
    const normalizedName = name.trim();
    if (!normalizedCode && !normalizedName) {
      setFeedback('请至少填写代码或名称。');
      return;
    }

    if (selectedAssetType === 'fund') {
      const numericAmount = Number(amount);
      if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
        setFeedback('请填写有效的基金持有金额。');
        return;
      }
      const nextHolding = {
        code: normalizedCode,
        name: normalizedName || normalizedCode,
        amount: numericAmount,
        profit: Number(profit) || 0,
        targetAllocation: targetAllocation ? Number(targetAllocation) : undefined,
        notes: notes.trim() || undefined,
      };
      if (editingHolding?.assetType === 'fund') {
        if (!await updateFundHolding({ ...nextHolding, id: editingHolding.holding.id })) { setFeedback('保存失败，原持仓未被修改，请稍后重试。'); return; }
        setFeedback(`已保存 ${activeUser.name} 的基金持仓。`);
      } else { addFundHolding(nextHolding); setFeedback(`已添加到 ${activeUser.name} 的基金持仓。`); }
    } else {
      const numericQuantity = Number(quantity);
      const numericAverageCost = Number(averageCost);
      if (!Number.isFinite(numericQuantity) || numericQuantity <= 0 || !Number.isFinite(numericAverageCost) || numericAverageCost < 0) {
        setFeedback('请填写有效的持有数量和平均成本。');
        return;
      }
      const nextHolding = {
        code: normalizedCode,
        name: normalizedName || normalizedCode,
        quantity: numericQuantity,
        averageCost: numericAverageCost,
        securitiesAccount: securitiesAccount.trim() || '默认证券账户',
        notes: notes.trim() || undefined,
      };
      if (editingHolding?.assetType === 'stock') {
        if (!await updateStockHolding({ ...nextHolding, id: editingHolding.holding.id })) { setFeedback('保存失败，原持仓未被修改，请稍后重试。'); return; }
        setFeedback(`已保存 ${activeUser.name} 的股票持仓。`);
      } else { addStockHolding(nextHolding); setFeedback(`已添加到 ${activeUser.name} 的股票持仓。`); }
    }
    resetManualForm();
    setPreviewUrl(null);
    setFileName('');
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    setFileName(file.name);
    setScreenshotConfirmation(false);
    setFeedback('截图已载入本机预览。请按截图逐项填写，确认添加后才会写入持仓。');
  };

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title={editingHolding ? '编辑快速持仓' : '持仓快速录入'} width="max-w-xl">
      <div className="space-y-5">
        <InlineAlert variant="info" title={`录入到：${activeUser.name}`} message="新增内容只归属于当前用户，保存前请确认用户选择正确。" />
        {persistenceStatus === 'error' ? <InlineAlert variant="warning" message="本地数据库暂时不可用；本次改动可能不会在重启后保留。" /> : null}

        <div className="grid grid-cols-2 gap-2 rounded-2xl border border-border/70 bg-background/40 p-1">
          <button type="button" className={mode === 'manual' ? 'btn-primary' : 'btn-secondary'} onClick={() => setMode('manual')}>
            <span className="inline-flex items-center gap-2"><PlusCircle className="h-4 w-4" />手动录入</span>
          </button>
          <button type="button" className={mode === 'screenshot' ? 'btn-primary' : 'btn-secondary'} onClick={() => setMode('screenshot')}>
            <span className="inline-flex items-center gap-2"><ImageUp className="h-4 w-4" />截图确认录入</span>
          </button>
        </div>

        {mode === 'manual' ? (
          <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            {screenshotConfirmation ? <InlineAlert variant="info" title="截图待确认录入" message={`正在依据 ${fileName || '当前截图'} 手动填写。截图只在本机预览；请逐项核对，确认添加后才会写入 ${activeUser.name} 的${selectedAssetType === 'fund' ? '基金' : '股票'}持仓。`} /> : null}
            {fixedAssetType ? (
              <InlineAlert variant="info" message={fixedAssetType === 'fund' ? '当前位于基金中心，本次只录入基金持仓。' : '当前位于股票中心，本次只录入股票持仓。'} />
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <button type="button" className={selectedAssetType === 'fund' ? 'btn-primary' : 'btn-secondary'} onClick={() => setAssetType('fund')}>基金</button>
                <button type="button" className={selectedAssetType === 'stock' ? 'btn-primary' : 'btn-secondary'} onClick={() => setAssetType('stock')}>股票</button>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-xs text-secondary"><span>{selectedAssetType === 'fund' ? '基金代码' : '股票代码'}</span><input className={inputClass} value={code} onChange={(event) => setCode(event.target.value)} placeholder={selectedAssetType === 'fund' ? '如 017811' : '如 600519'} /></label>
              <label className="space-y-1 text-xs text-secondary"><span>名称</span><input className={inputClass} value={name} onChange={(event) => setName(event.target.value)} placeholder="代码和名称至少填一项" /></label>
            </div>
            {selectedAssetType === 'fund' ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1 text-xs text-secondary"><span>持有金额</span><input className={inputClass} type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
                <label className="space-y-1 text-xs text-secondary"><span>持有收益</span><input className={inputClass} type="number" step="0.01" value={profit} onChange={(event) => setProfit(event.target.value)} /></label>
                <label className="space-y-1 text-xs text-secondary"><span>目标仓位（%）</span><input className={inputClass} type="number" min="0" max="100" step="0.1" value={targetAllocation} onChange={(event) => setTargetAllocation(event.target.value)} /></label>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1 text-xs text-secondary"><span>持有数量</span><input className={inputClass} type="number" min="0" step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
                <label className="space-y-1 text-xs text-secondary"><span>平均成本</span><input className={inputClass} type="number" min="0" step="0.0001" value={averageCost} onChange={(event) => setAverageCost(event.target.value)} /></label>
                <label className="space-y-1 text-xs text-secondary sm:col-span-2"><span>所属证券账户</span><input className={inputClass} value={securitiesAccount} onChange={(event) => setSecuritiesAccount(event.target.value)} /></label>
              </div>
            )}
            <label className="space-y-1 text-xs text-secondary"><span>备注</span><textarea className="input-surface input-focus-glow min-h-24 w-full rounded-xl border bg-transparent px-4 py-3 text-sm text-foreground" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
            <button type="submit" className="btn-primary w-full">{editingHolding ? '确认保存修改' : '确认添加持仓'}</button>
          </form>
        ) : (
          <div className="space-y-4">
            <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-cyan/40 bg-cyan/5 px-6 py-10 text-center">
              <ImageUp className="h-8 w-8 text-cyan" />
              <span className="font-medium text-foreground">选择支付宝、基金或券商持仓截图</span>
              <span className="text-xs text-secondary">支持 PNG、JPG、WEBP；当前只在本机预览，不上传。</span>
              <input aria-label="选择持仓截图文件" className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFileChange} />
            </label>
            {previewUrl ? (
              <div className="space-y-3 rounded-2xl border border-border/70 p-3">
                <p className="text-xs text-secondary">截图预览：{fileName}</p>
                <img src={previewUrl} alt="持仓截图预览" className="max-h-80 w-full rounded-xl object-contain" />
              </div>
            ) : null}
            <div className="rounded-2xl border border-border/70 bg-background/30 p-4">
              <h3 className="font-semibold text-foreground">本机截图确认区</h3>
              <p className="mt-2 text-sm leading-6 text-secondary">本阶段不自动识别截图，也不会上传、覆盖或直接写入持仓。请先核对截图，再进入手动填写；确认添加后才会保存到当前用户的{selectedAssetType === 'fund' ? '基金' : '股票'}持仓。</p>
              <button type="button" className="btn-primary mt-4 w-full" disabled={!previewUrl} onClick={() => { setMode('manual'); setScreenshotConfirmation(true); setFeedback('请依据截图逐项填写并确认添加。'); }}>
                按截图手动填写并确认
              </button>
            </div>
          </div>
        )}

        {feedback ? <InlineAlert variant="info" message={feedback} /> : null}
      </div>
    </Drawer>
  );
};

export const QuickHoldingEntryDrawer: React.FC<QuickHoldingEntryDrawerProps> = (props) => {
  if (!props.isOpen) return null;
  return <QuickHoldingEntryDrawerContent {...props} />;
};
