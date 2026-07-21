import { Check, Keyboard, Landmark, Star } from 'lucide-react';
import { useMemo, useState } from 'react';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import type { UiLanguage } from '../../i18n/uiText';
import { parseFundCodeInput } from './fundAnalysisSource';

export type FundAnalysisSource = 'manual' | 'holdings' | 'watchlist';

export type FundAnalysisSelection = {
  source: FundAnalysisSource;
  codes: string[];
};

type FundAnalysisSourceSelectorProps = {
  language: UiLanguage;
  minimum: number;
  maximum: number;
  inputLabel: string;
  placeholder: string;
  onSelectionChange: (selection: FundAnalysisSelection) => void;
};

type FundOption = {
  code: string;
  name: string;
};

const SOURCE_META = {
  zh: {
    manual: { label: '手动输入', description: '直接输入基金代码' },
    holdings: { label: '我的持仓', description: '当前用户的基金持仓' },
    watchlist: { label: '我的自选', description: '当前用户的基金自选' },
  },
  en: {
    manual: { label: 'Manual input', description: 'Enter fund codes directly' },
    holdings: { label: 'My holdings', description: 'Active-user fund holdings' },
    watchlist: { label: 'My watchlist', description: 'Active-user fund watchlist' },
  },
} as const;

function uniqueOptions(items: readonly FundOption[]): FundOption[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.code)) return false;
    seen.add(item.code);
    return true;
  });
}

const FundAnalysisSourceSelector = ({
  language,
  minimum,
  maximum,
  inputLabel,
  placeholder,
  onSelectionChange,
}: FundAnalysisSourceSelectorProps) => {
  const { activeUser, activeFundHoldings, activeFundWatchlist, persistenceStatus } = usePortfolioUsers();
  const [source, setSource] = useState<FundAnalysisSource>('manual');
  const [manualText, setManualText] = useState('');
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);

  const holdings = useMemo(
    () => uniqueOptions(activeFundHoldings.map(({ code, name }) => ({ code, name }))),
    [activeFundHoldings],
  );
  const watchlist = useMemo(
    () => uniqueOptions(activeFundWatchlist.map(({ code, name }) => ({ code, name }))),
    [activeFundWatchlist],
  );
  const sourceOptions = source === 'holdings' ? holdings : source === 'watchlist' ? watchlist : [];

  const publish = (nextSource: FundAnalysisSource, codes: string[]) => {
    setSelectedCodes(codes);
    onSelectionChange({ source: nextSource, codes });
  };

  const switchSource = (nextSource: FundAnalysisSource) => {
    if (nextSource === source) return;
    setSource(nextSource);
    publish(nextSource, nextSource === 'manual' ? parseFundCodeInput(manualText) : []);
  };

  const updateManualText = (value: string) => {
    setManualText(value);
    publish('manual', parseFundCodeInput(value));
  };

  const toggleCode = (code: string) => {
    const selected = selectedCodes.includes(code);
    let nextCodes: string[];
    if (selected) {
      nextCodes = selectedCodes.filter((item) => item !== code);
    } else if (maximum === 1) {
      nextCodes = [code];
    } else if (selectedCodes.length < maximum) {
      nextCodes = [...selectedCodes, code];
    } else {
      return;
    }
    publish(source, nextCodes);
  };

  const sourceCount = (candidate: FundAnalysisSource) => (
    candidate === 'holdings' ? holdings.length : candidate === 'watchlist' ? watchlist.length : null
  );
  const rangeText = minimum === maximum ? String(minimum) : `${minimum}–${maximum}`;

  return (
    <section className="mt-4 space-y-3" data-testid="fund-analysis-source-selector">
      <div>
        <p className="text-sm font-medium text-foreground">{language === 'zh' ? '选择基金来源' : 'Choose fund source'}</p>
        <p className="mt-1 text-xs leading-5 text-secondary-text">
          {language === 'zh'
            ? `只读取当前用户“${activeUser.name}”的本机列表；选择代码不会自动查询。`
            : `Only local lists for the active user “${activeUser.name}” are shown. Selecting codes never starts a lookup.`}
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-3" role="group" aria-label={language === 'zh' ? '基金来源' : 'Fund source'}>
        {(['manual', 'holdings', 'watchlist'] as const).map((candidate) => {
          const meta = SOURCE_META[language][candidate];
          const count = sourceCount(candidate);
          const Icon = candidate === 'manual' ? Keyboard : candidate === 'holdings' ? Landmark : Star;
          return (
            <button
              key={candidate}
              type="button"
              aria-pressed={source === candidate}
              className={`rounded-lg border p-3 text-left transition-colors ${source === candidate ? 'border-cyan bg-cyan/10' : 'border-border hover:border-cyan/50'}`}
              onClick={() => switchSource(candidate)}
            >
              <span className="flex items-center gap-2 text-sm font-medium text-foreground"><Icon className="h-4 w-4 text-cyan" />{meta.label}{count !== null ? ` (${count})` : ''}</span>
              <span className="mt-1 block text-xs text-secondary-text">{meta.description}</span>
            </button>
          );
        })}
      </div>

      {source === 'manual' ? (
        <label className="block text-sm text-secondary-text">
          <span className="mb-1 block">{inputLabel}</span>
          <input
            aria-label={inputLabel}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-cyan"
            inputMode="numeric"
            placeholder={placeholder}
            value={manualText}
            onChange={(event) => updateManualText(event.target.value)}
          />
        </label>
      ) : sourceOptions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border px-4 py-5 text-sm text-secondary-text">
          {persistenceStatus === 'loading'
            ? (language === 'zh' ? '正在读取本机列表……' : 'Loading the local list…')
            : persistenceStatus === 'error'
              ? (language === 'zh' ? '本机列表读取失败，请先检查工作台数据状态后重试。' : 'The local list could not be loaded. Check workspace data status and retry.')
            : source === 'holdings'
              ? (language === 'zh' ? '当前用户还没有基金持仓，请先到“基金持仓”录入。' : 'The active user has no fund holdings. Add holdings first.')
              : (language === 'zh' ? '当前用户还没有基金自选，请先到“基金自选”添加。' : 'The active user has no fund watchlist items. Add watchlist items first.')}
        </div>
      ) : (
        <div className="grid max-h-64 gap-2 overflow-y-auto pr-1 sm:grid-cols-2" data-testid={`fund-source-${source}-options`}>
          {sourceOptions.map((item) => {
            const selected = selectedCodes.includes(item.code);
            const limitReached = !selected && maximum > 1 && selectedCodes.length >= maximum;
            return (
              <button
                key={item.code}
                type="button"
                aria-label={`${language === 'zh' ? '选择' : 'Select'} ${item.code} ${item.name}`}
                aria-pressed={selected}
                disabled={limitReached}
                className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left disabled:cursor-not-allowed disabled:opacity-45 ${selected ? 'border-cyan bg-cyan/10' : 'border-border hover:border-cyan/50'}`}
                onClick={() => toggleCode(item.code)}
              >
                <span className="min-w-0"><span className="block truncate text-sm text-foreground">{item.name}</span><span className="block text-xs text-secondary-text">{item.code}</span></span>
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${selected ? 'border-cyan bg-cyan text-background' : 'border-border'}`}>{selected && <Check className="h-3.5 w-3.5" />}</span>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className={selectedCodes.length > maximum ? 'text-amber-300' : 'text-secondary-text'}>
          {language === 'zh'
            ? `已选择 ${selectedCodes.length} 只，需要 ${rangeText} 只`
            : `${selectedCodes.length} selected; ${rangeText} required`}
        </span>
        {selectedCodes.length > 0 && <span className="text-secondary-text">{selectedCodes.join(' · ')}</span>}
      </div>
    </section>
  );
};

export default FundAnalysisSourceSelector;
