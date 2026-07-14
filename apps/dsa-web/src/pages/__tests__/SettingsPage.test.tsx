import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import SettingsPage from '../SettingsPage';

describe('SettingsPage App-M4.1 workspace shell', () => {
  it('shows interface and keys as the default tab with disabled credential controls', () => {
    render(<SettingsPage />);

    expect(screen.getByRole('heading', { name: '设置工作台' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /接口与密钥/ })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('heading', { name: '接口与密钥' })).toBeInTheDocument();
    expect(screen.getByText('AI 模型接口')).toBeInTheDocument();
    expect(screen.getByText('行情数据接口')).toBeInTheDocument();
    expect(screen.getByText('通知接口')).toBeInTheDocument();
    expect(screen.getAllByDisplayValue('App-M4.1 暂不保存真实密钥')).toHaveLength(3);
    expect(screen.getAllByRole('button', { name: '配置（App-M4.1 暂不可用）' }).every((button) => button.hasAttribute('disabled'))).toBe(true);
  });

  it('switches to data source management and shows AkShare public read-only disabled status', () => {
    render(<SettingsPage />);

    fireEvent.click(screen.getByRole('tab', { name: /数据源管理/ }));

    expect(screen.getByRole('heading', { name: '数据源管理' })).toBeInTheDocument();
    expect(screen.getByText('AkShare 公开 A 股行情')).toBeInTheDocument();
    expect(screen.getByText('公开只读行情')).toBeInTheDocument();
    expect(screen.getByText('默认状态：关闭')).toBeInTheDocument();
    expect(screen.getByText('无账户读取')).toBeInTheDocument();
    expect(screen.getByText('无交易权限')).toBeInTheDocument();
    expect(screen.getByText('无密钥要求')).toBeInTheDocument();
    expect(screen.getAllByText('状态：后续接入')).toHaveLength(4);
  });

  it('switches to connection testing without issuing network or storage calls', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const storageSetSpy = vi.spyOn(Storage.prototype, 'setItem');
    const indexedDbOpenSpy = 'indexedDB' in globalThis ? vi.spyOn(indexedDB, 'open') : null;

    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: /连接测试/ }));
    fireEvent.click(screen.getByRole('button', { name: '开始连接测试' }));

    expect(screen.getByRole('heading', { name: '连接测试' })).toBeInTheDocument();
    expect(screen.getByText('App-M4.1 尚未启用真实连接测试。')).toBeInTheDocument();
    expect(screen.queryByText('连接成功')).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(storageSetSpy).not.toHaveBeenCalled();
    expect(indexedDbOpenSpy?.mock.calls.length ?? 0).toBe(0);
  });

  it('does not render real-looking credentials or account data', () => {
    const { container } = render(<SettingsPage />);

    expect(container.textContent).not.toMatch(/sk-[A-Za-z0-9]{12,}/);
    expect(container.textContent).not.toMatch(/Bearer\s+[A-Za-z0-9._-]+/i);
    expect(container.textContent).not.toMatch(/https:\/\/[^\s]*webhook/i);
    expect(container.textContent).not.toMatch(/账户余额|持仓账户|交易账号/);
  });
});
