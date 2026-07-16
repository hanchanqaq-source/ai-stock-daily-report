import apiClient from './index';

export type FundDataSource = {
  provider: string;
  source_kind: string;
  source_status: string;
  fetched_at: string;
  effective_at: string | null;
  report_period: string | null;
  stale: boolean;
  stale_reason: string;
  confidence: string | null;
  missing_fields: string[];
  missing_reasons: Record<string, string>;
};

export type FundProfile = {
  code: string;
  name: string | null;
  fund_type: string | null;
  manager: string | null;
  scale: string | null;
  scale_currency: string | null;
  inception_date: string | null;
  source: FundDataSource;
};

export type FundNavSnapshot = {
  code: string;
  unit_nav: string | null;
  accumulated_nav: string | null;
  daily_change_pct: string | null;
  nav_date: string | null;
  source: FundDataSource;
};

export type FundHoldingPosition = {
  security_code: string;
  security_name: string;
  weight_pct: string;
  industry: {
    status: 'mapped' | 'unknown' | 'ambiguous' | 'unmapped';
    industry_code: string | null;
    industry_name: string | null;
    source: FundDataSource;
  };
};

export type FundHoldingsSnapshot = {
  code: string;
  report_period: string;
  positions: FundHoldingPosition[];
  disclosed_total_pct: string;
  source: FundDataSource;
};

export type FundDataBundle = {
  code: string;
  requested_sections: string[];
  data_status: 'available' | 'partial' | 'missing' | 'stale' | 'provider_error';
  source: FundDataSource;
  profile: FundProfile | null;
  nav: FundNavSnapshot | null;
  holdings: FundHoldingsSnapshot | null;
  missing_sections: string[];
  reason: string;
};

export type FundPublicReadonlyResponse = {
  status: 'completed-readonly' | 'unavailable' | 'blocked' | 'timeout';
  providerLabel: string;
  readOnly: true;
  bundle?: FundDataBundle;
  errorCode?: string;
};

export type FundIndustryExposure = {
  code: string;
  report_date: string;
  industries: Array<{
    industry_name: string;
    weight_pct: string;
    market_value_cny_10k: string | null;
  }>;
  disclosed_total_pct: string;
  top3_concentration_pct: string;
  source: FundDataSource;
};

export type FundComparisonItem = {
  code: string;
  data_status: 'available' | 'partial' | 'missing';
  bundle: FundDataBundle;
  industry_exposure: FundIndustryExposure | null;
  top10_holdings_concentration_pct: string | null;
  missing_sections: string[];
  warnings: string[];
};

export type FundPairOverlap = {
  left_code: string;
  right_code: string;
  common_holdings: Array<{
    security_code: string;
    security_name: string;
    left_weight_pct: string;
    right_weight_pct: string;
    overlap_weight_pct: string;
  }>;
  disclosed_holdings_overlap_pct: string;
  common_industries: Array<{
    industry_name: string;
    left_weight_pct: string;
    right_weight_pct: string;
    overlap_weight_pct: string;
  }>;
  disclosed_industry_overlap_pct: string;
  holdings_scope: 'latest-disclosed-top-holdings';
  industry_scope: 'provider-disclosed-industry-allocation';
  warnings: string[];
};

export type FundComparisonResult = {
  requested_codes: string[];
  data_status: 'available' | 'partial' | 'missing';
  source: FundDataSource;
  funds: FundComparisonItem[];
  pair_overlaps: FundPairOverlap[];
  missing_funds: string[];
  reason: string;
};

export type FundComparisonReadonlyResponse = {
  status: 'completed-readonly' | 'unavailable' | 'blocked' | 'timeout';
  providerLabel: string;
  readOnly: true;
  comparison?: FundComparisonResult;
  errorCode?: string;
};

export type IndustryCycleEvidence = {
  industry_name: string;
  board_code: string;
  data_status: 'available' | 'partial' | 'missing';
  phase: 'recovery' | 'expansion' | 'overheated' | 'slowdown' | 'contraction' | 'insufficient';
  confidence: string;
  metrics: {
    as_of_date: string | null;
    return_20d_pct: string | null;
    return_60d_pct: string | null;
    turnover_change_20d_pct: string | null;
    breadth_rise_ratio_pct: string | null;
    relative_strength_20d_pct: string | null;
    median_dynamic_pe: string | null;
    median_pb: string | null;
    constituent_count: number;
    breadth_sample_count: number;
  };
  productivity: {
    status: 'improving' | 'stable' | 'weakening' | 'insufficient';
    report_period: string | null;
    effective_at: string | null;
    revenue_yoy_median_pct: string | null;
    profit_yoy_median_pct: string | null;
    roe_median_pct: string | null;
    gross_margin_median_pct: string | null;
    operating_cashflow_positive_ratio_pct: string | null;
    covered_constituents: number;
    total_constituents: number;
    confidence: string;
    missing_dimensions: string[];
    scope: 'operating-productivity-proxy-not-total-factor-productivity';
  };
  source_interfaces: string[];
  evidence_dates: string[];
  missing_evidence: string[];
  warnings: string[];
  cycle_scope: 'market-cycle-evidence-not-trading-advice';
};

export type FundIndustryCycleResult = {
  requested_codes: string[];
  data_status: 'available' | 'partial' | 'missing';
  fetched_at: string;
  provider: string;
  benchmark_code: string;
  financial_report_period: string | null;
  funds: Array<{
    code: string;
    name: string | null;
    holdings_report_period: string | null;
    industry_links: Array<{
      industry_name: string;
      fund_weight_pct: string;
      scope: 'provider-disclosed-industry-allocation' | 'latest-disclosed-top-holdings-provider-industry';
    }>;
    analyzed_weight_pct: string;
    unclassified_holdings: string[];
    omitted_industries: number;
    warnings: string[];
  }>;
  industries: IndustryCycleEvidence[];
  missing_evidence: string[];
  warnings: string[];
  method: 'deterministic-explainable-features-inspired-by-market-state-analysis';
};

export type FundIndustryCycleReadonlyResponse = {
  status: 'completed-readonly' | 'unavailable' | 'blocked' | 'timeout';
  providerLabel: string;
  readOnly: true;
  cycle?: FundIndustryCycleResult;
  errorCode?: string;
};

export type FundPortfolioAdviceResult = {
  data_status: 'available' | 'partial';
  risk_level: 'high' | 'medium' | 'low' | 'insufficient';
  total_amount: string;
  total_profit: string;
  holding_count: number;
  unique_fund_count: number;
  top_fund_weight_pct: string;
  top3_weight_pct: string;
  public_evidence_codes: string[];
  public_evidence_coverage_pct: string;
  funds: Array<{
    code: string; name: string; amount: string; weight_pct: string; profit: string;
    target_allocation_pct: string | null; target_drift_pct: string | null; public_evidence_included: boolean;
  }>;
  findings: Array<{ category: string; severity: 'high' | 'medium'; title: string; evidence: string }>;
  suggestions: Array<{ priority: 'high' | 'medium' | 'low'; title: string; reason: string; action_scope: string }>;
  missing_evidence: string[];
  warnings: string[];
  scope: 'active-user-in-memory-fund-portfolio-review';
  advice_boundary: 'educational-review-not-investment-order';
};

export type FundPortfolioAdviceReadonlyResponse = {
  status: 'completed-readonly' | 'unavailable' | 'blocked' | 'timeout';
  providerLabel: string;
  readOnly: true;
  advice?: FundPortfolioAdviceResult;
  errorCode?: string;
};

export type FundPortfolioAdviceHolding = {
  code: string;
  name: string;
  amount: number;
  profit: number;
  targetAllocation?: number;
};

export const fundDataApi = {
  async fetchAksharePublicFund(code: string): Promise<FundPublicReadonlyResponse> {
    const response = await apiClient.post<FundPublicReadonlyResponse>('/api/v1/provider-readonly/akshare/fund', {
      mode: 'fund-public-readonly',
      provider: 'akshare_fund_public',
      code,
      sections: ['profile', 'nav', 'holdings'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
    return response.data;
  },

  async compareAksharePublicFunds(codes: string[]): Promise<FundComparisonReadonlyResponse> {
    const response = await apiClient.post<FundComparisonReadonlyResponse>('/api/v1/provider-readonly/akshare/funds/compare', {
      mode: 'fund-comparison-readonly',
      provider: 'akshare_fund_public',
      codes,
      sections: ['profile', 'nav', 'holdings', 'industry-exposure'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
    return response.data;
  },

  async fetchAkshareFundIndustryCycle(codes: string[]): Promise<FundIndustryCycleReadonlyResponse> {
    const response = await apiClient.post<FundIndustryCycleReadonlyResponse>(
      '/api/v1/provider-readonly/akshare/funds/industry-cycle',
      {
        mode: 'fund-industry-cycle-readonly',
        provider: 'akshare_fund_public',
        codes,
        sections: ['funds', 'disclosed-holdings', 'industry-cycle-evidence', 'productivity-proxy-evidence'],
        humanApproved: true,
        readOnly: true,
        allowAccountRead: false,
        allowTrading: false,
        allowNotificationSend: false,
        allowAiCall: false,
        allowPersistence: false,
      },
    );
    return response.data;
  },

  async fetchAkshareFundPortfolioAdvice(holdings: FundPortfolioAdviceHolding[]): Promise<FundPortfolioAdviceReadonlyResponse> {
    const response = await apiClient.post<FundPortfolioAdviceReadonlyResponse>(
      '/api/v1/provider-readonly/akshare/funds/portfolio-advice',
      {
        mode: 'fund-portfolio-advice-readonly',
        provider: 'akshare_fund_public',
        holdings: holdings.map((item) => ({ ...item, targetAllocation: item.targetAllocation ?? null })),
        sections: ['portfolio-concentration', 'overlap', 'industry-cycle', 'target-drift'],
        humanApproved: true,
        readOnly: true,
        allowAccountRead: false,
        allowTrading: false,
        allowNotificationSend: false,
        allowAiCall: false,
        allowPersistence: false,
      },
    );
    return response.data;
  },
};
