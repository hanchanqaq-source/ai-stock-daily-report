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

export type FundRiskProfile = 'conservative' | 'balanced' | 'aggressive';
export type FundRiskDimensionStatus = 'normal' | 'watch' | 'high' | 'insufficient' | 'not-applicable';

export type FundPortfolioAdvicePosition = {
  code: string;
  weightPct: number;
  targetWeightPct: number | null;
};

export type FundPortfolioAdviceResult = {
  requested_codes: string[];
  data_status: 'available' | 'partial' | 'missing';
  fetched_at: string;
  risk_profile: FundRiskProfile;
  positions: Array<{
    code: string;
    weight_pct: string;
    target_weight_pct: string | null;
  }>;
  input_privacy: {
    amount_shared: false;
    cost_basis_shared: false;
    user_identity_shared: false;
    account_read: false;
  };
  concentration: {
    status: FundRiskDimensionStatus;
    largest_fund_weight_pct: string;
    top_two_weight_pct: string;
    herfindahl_index: string;
    effective_fund_count: string;
    attention_thresholds: {
      single_fund_pct: string;
      top_two_pct: string;
      scope: 'monitoring-thresholds-not-prescribed-allocation';
    };
  };
  disclosed_overlap: {
    status: FundRiskDimensionStatus;
    max_disclosed_holdings_overlap_pct: string | null;
    max_disclosed_industry_overlap_pct: string | null;
    highest_pair: string | null;
    pair_count: number;
    scope: 'latest-disclosed-data-lower-bound';
  };
  industry_exposure: {
    status: FundRiskDimensionStatus;
    disclosed_portfolio_coverage_pct: string;
    unclassified_or_undisclosed_pct: string;
    top_industries: Array<{ industry_name: string; portfolio_exposure_pct: string }>;
    top_three_exposure_pct: string;
    report_dates: string[];
    attention_threshold_pct: string;
    scope: 'provider-disclosed-look-through-not-complete-current-portfolio';
  };
  nav_risk: {
    status: FundRiskDimensionStatus;
    weighted_average_fund_volatility_60d_pct: string | null;
    volatility_coverage_pct: string;
    worst_fund_drawdown_120d_pct: string | null;
    funds: Array<{
      code: string;
      data_status: 'available' | 'partial' | 'missing';
      as_of_date: string | null;
      observations: number;
      return_20d_pct: string | null;
      return_60d_pct: string | null;
      annualized_volatility_60d_pct: string | null;
      max_drawdown_120d_pct: string | null;
      missing_evidence: string[];
    }>;
    attention_thresholds: {
      annualized_volatility_pct: string;
      drawdown_magnitude_pct: string;
    };
    scope: 'weighted-average-of-fund-volatility-not-covariance-portfolio-volatility';
  };
  cycle_exposure: {
    status: FundRiskDimensionStatus;
    analyzed_portfolio_exposure_pct: string;
    phase_exposure_pct: Record<string, string>;
    pressure_exposure_pct: string;
    weakening_productivity_proxy_exposure_pct: string;
    financial_report_period: string | null;
    scope: 'selected-disclosed-industry-evidence-not-market-timing-signal';
  };
  allocation_guidance: Array<{
    id: string;
    priority: 'info' | 'watch' | 'high';
    title: string;
    reason: string;
    evidence: string[];
    action: string;
  }>;
  missing_evidence: string[];
  warnings: string[];
  method: 'deterministic-current-user-fund-risk-and-allocation-review';
};

export type FundPortfolioAdviceReadonlyResponse = {
  status: 'completed-readonly' | 'unavailable' | 'blocked' | 'timeout';
  providerLabel: string;
  readOnly: true;
  advice?: FundPortfolioAdviceResult;
  errorCode?: string;
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

  async fetchAkshareFundPortfolioAdvice(
    positions: FundPortfolioAdvicePosition[],
    riskProfile: FundRiskProfile,
  ): Promise<FundPortfolioAdviceReadonlyResponse> {
    const response = await apiClient.post<FundPortfolioAdviceReadonlyResponse>(
      '/api/v1/provider-readonly/akshare/funds/portfolio-advice',
      {
        mode: 'fund-portfolio-advice-readonly',
        provider: 'akshare_fund_public',
        positions,
        riskProfile,
        sections: ['portfolio-allocation', 'nav-risk', 'disclosed-overlap', 'industry-cycle', 'allocation-guidance'],
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
