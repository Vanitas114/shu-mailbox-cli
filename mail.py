"""只读邮件列表查询，参照邮箱页面加载的 Coremail 前端。"""
from __future__ import annotations
from email.utils import getaddresses
from datetime import datetime

BASE = 'https://newmail.shu.edu.cn/coremail'
FOLDERS = {'1': ('收件箱', 1), '2': ('待办邮件', -5), '3': ('草稿箱', 2), '4': ('已发送', 3)}

class MailError(Exception):
    pass

def call(session, sid, func, body):
    endpoint = BASE + ('/XT/jsp/mail.jsp' if func == 'getAllFolders' else '/s/json')
    payload = {'data': body} if func == 'getAllFolders' else {'json': body}
    content_type = 'application/x-www-form-urlencoded; charset=UTF-8' if func == 'getAllFolders' else 'text/x-json; tz="Asia/Shanghai"'
    response = session.post(endpoint, params={'sid': sid, 'func': func},
        **payload, headers={'Accept':'text/x-json', 'Content-Type':content_type,
                           'Origin':'https://newmail.shu.edu.cn', 'Referer':BASE+'/XT/index.jsp'},
        allow_redirects=False, timeout=30)
    if response.status_code != 200:
        raise MailError(f'邮箱接口返回 HTTP {response.status_code}，会话可能已过期')
    try:
        data = response.json()
    except ValueError:
        raise MailError('邮箱返回了无法识别的数据，可能是会话失效或接口发生变化') from None
    if not isinstance(data, dict) or data.get('code') != 'S_OK':
        code = data.get('code', '未知错误') if isinstance(data, dict) else '未知错误'
        raise MailError(f'邮箱查询失败：{code}')
    if 'var' not in data:
        raise MailError('邮箱返回结果缺少列表数据')
    return data

def walk_folders(value):
    if isinstance(value, list):
        for item in value:
            yield from walk_folders(item)
    elif isinstance(value, dict):
        if 'id' in value:
            yield value
        for key in ('items', 'children'):
            if key in value:
                yield from walk_folders(value[key])

def list_messages(session, sid, fid, page=1, size=20):
    if page < 1 or not 1 <= size <= 100:
        raise ValueError('页码或每页数量不正确')
    params = {'start':(page-1)*size, 'limit':size, 'mode':'count',
              'order':'deferredDate' if fid == -5 else 'date', 'desc':fid != -5,
              'returnTotal':True, 'returnTag':False, 'summaryWindowSize':0}
    if fid == -5:
        folder_data = call(session, sid, 'getAllFolders', {'stats':'true', 'threads':'false'})['var']
        folders = list(walk_folders(folder_data))
        virtual = next((f for f in folders if str(f.get('id')) == '-5'), None)
        if not virtual or not isinstance(virtual.get('vp'), dict):
            raise MailError('无法识别待办邮件的筛选条件')
        ids = [f['id'] for f in folders if isinstance(f.get('id'), int) and f['id'] > 0 and f['id'] != 4]
        if not ids:
            raise MailError('无法获取待办邮件所需的文件夹列表')
        params.update({'fids': ids, 'skipLockedFolders':True})
        params.update(virtual['vp'])
    else:
        params['fid'] = fid
    data = call(session, sid, 'mbox:listMessages', params)
    payload = data['var']
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload[k] for k in ('items','messages','list') if isinstance(payload.get(k), list)), None)
    else:
        rows = None
    if rows is None or any(not isinstance(row, dict) for row in rows):
        raise MailError('邮箱列表格式与预期不同，无法解析')
    total = data.get('total', data.get('totalCount'))
    if isinstance(payload, dict):
        total = payload.get('total', payload.get('totalCount', total))
    return [metadata(row, fid) for row in rows], total

def address(value):
    if not value:
        return '—'
    if isinstance(value, list):
        return ', '.join(address(v) for v in value)
    if isinstance(value, dict):
        name = value.get('name') or value.get('trueName') or ''
        addr = value.get('address') or value.get('email') or ''
        return f'{name} <{addr}>' if name and addr else str(name or addr or '—')
    return str(value)

def format_date(value):
    if value is None or value == '': return '—'
    if isinstance(value, (int, float)):
        try: return datetime.fromtimestamp(value / 1000 if value > 1e11 else value).strftime('%Y-%m-%d %H:%M')
        except (OSError, OverflowError, ValueError): return str(value)
    return str(value)

def metadata(row, folder):
    incoming = folder in (1, -5)
    return {'person':address(row.get('from') if incoming else row.get('to')),
            'subject':str(row.get('subject') or '（无主题）'),
            'date':format_date(row.get('sentDate') if folder == 3 else row.get('receivedDate') or row.get('sentDate'))}

def show(rows, total, folder, page):
    print(f'\n{folder} · 第 {page} 页' + (f' · 共 {total} 封' if total is not None else ''))
    if not rows:
        print('本页没有邮件。')
    for i, row in enumerate(rows, 1):
        print(f"\n{i}. {row['subject']}\n   联系人：{row['person']}\n   日期：{row['date']}")

def menu(session, sid):
    while True:
        print('\n选择邮箱：1 收件箱  2 待办邮件  3 草稿箱  4 已发送  q 退出')
        choice = input('请输入选择：').strip().lower()
        if choice in ('q', 'quit', 'exit'): return
        if choice not in FOLDERS:
            print('请输入 1、2、3、4 或 q。'); continue
        name, fid = FOLDERS[choice]
        page = 1
        while True:
            try:
                rows, total = list_messages(session, sid, fid, page)
                show(rows, total, name, page)
            except MailError as e:
                print(f'查询失败：{e}'); break
            print('\nn 下一页  p 上一页  r 刷新  b 返回  q 退出')
            action = input('请输入选择：').strip().lower()
            if action == 'q': return
            if action == 'b': break
            if action == 'n':
                if len(rows) < 20 or (isinstance(total, int) and page*20 >= total): print('已经是最后一页。')
                else: page += 1
            elif action == 'p': page = max(1,page-1)
            elif action != 'r': print('请输入 n、p、r、b 或 q。')
