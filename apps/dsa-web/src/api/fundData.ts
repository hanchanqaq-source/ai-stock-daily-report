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
};
