import pandas as pd
from .paths import PATHS
import os

# columns: type, platform, user_id
PERM_FILE = os.path.join(PATHS['data'], 'permissions.xlsx')
PERM_KEYS = {'super': '',  # 超级用户密码
             'debug': '',
             'InfoSession': '',
             'WebImgSession': '',
             }


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
