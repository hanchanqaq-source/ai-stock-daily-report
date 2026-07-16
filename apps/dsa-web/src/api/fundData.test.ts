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
});
