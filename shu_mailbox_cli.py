#!/usr/bin/env python3
"""Read-only SHU mail proof of concept. Authentication is held in memory only."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor' / 'shu-sso-poc'))
from src.client import ShuSSO
from src.qr import render_qr_terminal
from mail import menu

MAIL = 'https://newmail.shu.edu.cn/'
ALLOWED = {'newsso.shu.edu.cn', 'oauth.shu.edu.cn', 'newmail.shu.edu.cn'}

class FlowError(Exception): pass

def checked_get(session, url, *, limit=12):
    for _ in range(limit):
        host = urlparse(url).hostname
        if urlparse(url).scheme != 'https' or host not in ALLOWED:
            raise FlowError('登录跳转指向未预期的站点，已停止')
        r = session.get(url, allow_redirects=False, timeout=25)
        if r.is_redirect:
            url = urljoin(r.url, r.headers['Location'])
            continue
        r.raise_for_status()
        return r
    raise FlowError('登录跳转次数过多')

def bootstrap(client):
    r = checked_get(client.sess, MAIL)
    match = re.search(r'/oauth2/login/([^/?#]+)', urlparse(r.url).path)
    if not match:
        raise FlowError('没有获取到邮箱 SSO 登录参数，页面可能已变更')
    return match.group(1)

def login(client, timeout, style):
    state = bootstrap(client)
    info = client.wecom_qrcode_info(state=state)
    if not info.get('key'):
        raise FlowError('无法取得企微二维码，请检查网络或 SSO 页面是否变更')
    print('\n请使用企业微信扫描二维码，并在手机上确认登录：', flush=True)
    if not render_qr_terminal(info['confirm_url'], style=style):
        raise FlowError('缺少 qrcode 依赖；请先安装 requirements.txt')
    print(f'\n等待扫码（最多 {timeout} 秒）...', flush=True)
    statuses = {'QRCODE_SCAN_NEVER':'等待扫码','QRCODE_SCAN_ING':'已扫码，请在手机上确认','QRCODE_SCAN_SUCC':'扫码确认成功','QRCODE_SCAN_ERR':'二维码已失效'}
    result = client.wecom_wait_scan(info['key'], state=state, timeout=timeout,
        poll_log=lambda status, _: print(statuses.get(status, str(status)), flush=True))
    if not result.get('ok'):
        raise FlowError('扫码未完成：' + str(result.get('reason') or result.get('status')))
    red = client.wecom_redeem(result['auth_code'], state)
    if not red.get('ok') or not red.get('location'):
        raise FlowError('SSO 回调没有返回可用的跳转')
    landing = checked_get(client.sess, urljoin('https://newsso.shu.edu.cn/', red['location']))
    sid = parse_qs(urlparse(landing.url).query).get('sid', [None])[0]
    if urlparse(landing.url).hostname != 'newmail.shu.edu.cn' or not sid:
        raise FlowError('扫码后未取得邮箱会话（停在 ' + str(urlparse(landing.url).hostname) + urlparse(landing.url).path + '）')
    print('已取得邮箱会话。', flush=True)
    return sid

def main():
    p=argparse.ArgumentParser(description='shu-mailbox-cli：上海大学邮箱只读工具')
    p.add_argument('--scan-timeout', type=int, default=180)
    p.add_argument('--qr-style', choices=['block','ascii'], default='block')
    args=p.parse_args()
    try:
        client=ShuSSO()
        client.sess.verify = True
        sid = login(client,args.scan_timeout,args.qr_style)
        menu(client.sess, sid)
        return 0
    except Exception as exc:
        print('运行失败：'+type(exc).__name__+'：'+str(exc).split('?',1)[0],file=sys.stderr)
        return 1

if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: print('\n已取消'); sys.exit(130)

