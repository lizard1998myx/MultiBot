import pandas as pd
from .paths import PATHS
import os

# columns: type, platform, user_id
PERM_FILE = os.path.join(PATHS['data'], 'permissions.xlsx')
# columns: type, key
PERM_KEY_FILE = os.path.join(PATHS['data'], 'permission_keys.xlsx')
PERM_KEYS = {'super': 'default_key',
             'debug': '',
             'InfoSession': 'default_key',
             'WebImgSession': '',
             'Ipv6AddrSession': '',
             }

try:  # update with file
    for record in pd.read_excel(PERM_KEY_FILE).to_dict('records'):
        PERM_KEYS[record['type']] = record['key']
except FileNotFoundError:
    records = []
    for k, v in PERM_KEYS.items():
        records.append({'type': k, 'key': v})
    pd.DataFrame(records).to_excel(PERM_KEY_FILE, index=False)
    print(f'【MultiBot】please update your permission keys in {PERM_KEY_FILE}')


def get_permissions():
    # 如果权限列表不存在
    if not os.path.exists(PERM_FILE):
        return {}

    df = pd.read_excel(PERM_FILE)
    perm_list = {}
    for t in set(df['type']):
        df_t = df[df['type'] == t]
        perm_t = {}
        for p in set(df_t['platform']):
            df_p = df_t[df_t['platform'] == p]
            list_p = []  # 初始化，通常里面会包含内容
            for u in df_p['user_id']:
                if u == 'all':
                    list_p = []  # 表示全部通过
                    break
                else:
                    list_p.append(str(u))
            perm_t[p] = list_p
        perm_list[t] = perm_t

    return perm_list
