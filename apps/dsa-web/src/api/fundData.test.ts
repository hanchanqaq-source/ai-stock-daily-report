import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('./index', () => ({ default: apiClientMock }));

import { fundDataApi } from './fundData';

describe('fundDataApi', () => {
  beforeEach(() => apiClientMock.post.mockReset());

  it('sends only the fixed localhost read-only fund request contract', async () => {
    apiClientMock.post.mockResolvedValue({
      data: { status: 'unavailable', providerLabel: 'AKShare 公开基金数据', readOnly: true },
    });

    await fundDataApi.fetchAksharePublicFund('000001');

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/provider-readonly/akshare/fund', {
      mode: 'fund-public-readonly',
      provider: 'akshare_fund_public',
      code: '000001',
      sections: ['profile', 'nav', 'holdings'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
  });

  it('sends the fixed read-only comparison contract with no enabled capabilities', async () => {
    apiClientMock.post.mockResolvedValue({
      data: { status: 'unavailable', providerLabel: 'AKShare 公开基金数据', readOnly: true },
    });

    await fundDataApi.compareAksharePublicFunds(['000001', '110022']);

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/provider-readonly/akshare/funds/compare', {
      mode: 'fund-comparison-readonly',
      provider: 'akshare_fund_public',
      codes: ['000001', '110022'],
      sections: ['profile', 'nav', 'holdings', 'industry-exposure'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
  });

  it('sends the fixed read-only D3 evidence contract with no enabled capabilities', async () => {
    apiClientMock.post.mockResolvedValue({
      data: { status: 'unavailable', providerLabel: 'AKShare 公开基金数据', readOnly: true },
    });

    await fundDataApi.fetchAkshareFundIndustryCycle(['000001']);

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/provider-readonly/akshare/funds/industry-cycle', {
      mode: 'fund-industry-cycle-readonly',
      provider: 'akshare_fund_public',
      codes: ['000001'],
      sections: ['funds', 'disclosed-holdings', 'industry-cycle-evidence', 'productivity-proxy-evidence'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
  });

  it('sends only normalized weights and targets for the D4 current-user review', async () => {
    apiClientMock.post.mockResolvedValue({
      data: { status: 'unavailable', providerLabel: 'AKShare 公开基金数据', readOnly: true },
    });

    await fundDataApi.fetchAkshareFundPortfolioAdvice([
      { code: '000001', weightPct: 60, targetWeightPct: 50 },
      { code: '110022', weightPct: 40, targetWeightPct: 50 },
    ], 'balanced');

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/provider-readonly/akshare/funds/portfolio-advice', {
      mode: 'fund-portfolio-advice-readonly',
      provider: 'akshare_fund_public',
      positions: [
        { code: '000001', weightPct: 60, targetWeightPct: 50 },
        { code: '110022', weightPct: 40, targetWeightPct: 50 },
      ],
      riskProfile: 'balanced',
      sections: ['portfolio-allocation', 'nav-risk', 'disclosed-overlap', 'industry-cycle', 'allocation-guidance'],
      humanApproved: true,
      readOnly: true,
      allowAccountRead: false,
      allowTrading: false,
      allowNotificationSend: false,
      allowAiCall: false,
      allowPersistence: false,
    });
    const body = apiClientMock.post.mock.calls[0][1];
    expect(body).not.toHaveProperty('userId');
    expect(body.positions[0]).not.toHaveProperty('amount');
    expect(body.positions[0]).not.toHaveProperty('cost');
  });
});
