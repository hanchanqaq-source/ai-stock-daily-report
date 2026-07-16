import type React from 'react';
import { useEffect, useState } from 'react';
import { ImageUp, PlusCircle } from 'lucide-react';
import { Drawer } from '../common/Drawer';
import { InlineAlert } from '../common/InlineAlert';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';

type EntryMode = 'manual' | 'screenshot';
type AssetType = 'fund' | 'stock';

type QuickHoldingEntryDrawerProps = {
  isOpen: boolean;
  initialMode: EntryMode;
  fixedAssetType?: AssetType;
  onClose: () => void;
};

const inputClass = 'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground';

const QuickHoldingEntryDrawerContent: React.FC<QuickHoldingEntryDrawerProps> = ({ isOpen, initialMode, fixedAssetType, onClose }) => {
  const { activeUser, activeUserId, addFundHolding, addStockHolding } = usePortfolioUsers();
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
  };

  const handleSubmit = (event: React.FormEvent) => {
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
      addFundHolding(activeUserId, {
        code: normalizedCode,
        name: normalizedName || normalizedCode,
        amount: numericAmount,
        profit: Number(profit) || 0,
        targetAllocation: targetAllocation ? Number(targetAllocation) : undefined,
        notes: notes.trim() || undefined,
      });
      setFeedback(`已添加到 ${activeUser.name} 的基金持仓。`);
    } else {
      const numericQuantity = Number(quantity);
      const numericAverageCost = Number(averageCost);
      if (!Number.isFinite(numericQuantity) || numericQuantity <= 0 || !Number.isFinite(numericAverageCost) || numericAverageCost < 0) {
        setFeedback('请填写有效的持有数量和平均成本。');
        return;
      }
      addStockHolding(activeUserId, {
        code: normalizedCode,
        name: normalizedName || normalizedCode,
        quantity: numericQuantity,
        averageCost: numericAverageCost,
        securitiesAccount: securitiesAccount.trim() || '默认证券账户',
        notes: notes.trim() || undefined,
      });
      setFeedback(`已添加到 ${activeUser.name} 的股票持仓。`);
    }
    resetManualForm();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    setFileName(file.name);
    setFeedback('截图已载入预览。真实文字和数字识别将在 M2.2 接入，当前不会自动写入持仓。');
  };

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title="持仓快速录入" width="max-w-xl">
      <div className="space-y-5">
        <InlineAlert variant="info" title={`录入到：${activeUser.name}`} message="新增内容只归属于当前用户，保存前请确认用户选择正确。" />

        <div className="grid grid-cols-2 gap-2 rounded-2xl border border-border/70 bg-background/40 p-1">
          <button type="button" className={mode === 'manual' ? 'btn-primary' : 'btn-secondary'} onClick={() => setMode('manual')}>
            <span className="inline-flex items-center gap-2"><PlusCircle className="h-4 w-4" />手动录入</span>
          </button>
          <button type="button" className={mode === 'screenshot' ? 'btn-primary' : 'btn-secondary'} onClick={() => setMode('screenshot')}>
            <span className="inline-flex items-center gap-2"><ImageUp className="h-4 w-4" />截图识别</span>
          </button>
        </div>

        {mode === 'manual' ? (
          <form className="space-y-4" onSubmit={handleSubmit}>
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
            <button type="submit" className="btn-primary w-full">确认添加持仓</button>
          </form>
        ) : (
          <div className="space-y-4">
            <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-cyan/40 bg-cyan/5 px-6 py-10 text-center">
              <ImageUp className="h-8 w-8 text-cyan" />
              <span className="font-medium text-foreground">选择支付宝、基金或券商持仓截图</span>
              <span className="text-xs text-secondary">支持 PNG、JPG、WEBP；当前只在本机预览，不上传。</span>
              <input className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFileChange} />
            </label>
            {previewUrl ? (
              <div className="space-y-3 rounded-2xl border border-border/70 p-3">
                <p className="text-xs text-secondary">截图预览：{fileName}</p>
                <img src={previewUrl} alt="持仓截图预览" className="max-h-80 w-full rounded-xl object-contain" />
              </div>
            ) : null}
            <div className="rounded-2xl border border-border/70 bg-background/30 p-4">
              <h3 className="font-semibold text-foreground">识别结果确认区</h3>
              <p className="mt-2 text-sm leading-6 text-secondary">M2.2 接入识别后，这里会列出代码、名称、金额、数量和收益。你确认或修改后，才会写入当前用户持仓。</p>
              <button type="button" className="btn-secondary mt-4 w-full" disabled>等待识别服务接入</button>
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
