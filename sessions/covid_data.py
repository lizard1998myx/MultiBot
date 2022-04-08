from .argument import ArgSession, Argument
from ..responses import ResponseMsg
from ..paths import PATHS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException
import pandas as pd
import numpy as np
import time, os, bs4, datetime, re, json

CACHE_DIR = PATHS['cache']
webdriver_dir = PATHS['webdriver']
N_DAYS_TO_CURE = 21  # 假设无症状感染者康复的天数
PROVINCE_RECHECK = ['上海', '吉林', '北京', '福建']  # 需要检查无症状感染者的省份


class CovidDataSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self.session_type = '疫情数据查询'
        self.strict_commands = ['疫情数据', '感染数', '本土疫情']
        self.description = '查找全国本土疫情确诊/无症状数据，来源百度/腾讯。'
        self.arg_list = [Argument(key='region', alias_list=['-r'],
                                  required=False, get_next=True,
                                  ask_text='查看具体省份全部数据（默认大陆各省本土疫情）',
                                  default_value=None),
                         Argument(key='sort-by', alias_list=['-s', '-k'],
                                  required=False, get_next=True,
                                  ask_text='排序依据（新增/现有/累计/治愈/死亡）',
                                  default_value='新增'),
                         Argument(key='top-num', alias_list=['-t', '-n'],
                                  required=False, get_next=True,
                                  ask_text='排序时输出省份数（默认5），负数表示倒数',
                                  default_value=5),
                         Argument(key='no-cache', alias_list=['-nc'],
                                  help_text='不启用缓存，需要搜索更长时间'),
                         Argument(key='baidu-source', alias_list=['-bd', '-bs'],
                                  help_text='使用百度源'),
                         Argument(key='tencent-source', alias_list=['-tct', '-ts'],
                                  help_text='使用腾讯源（默认）'),
                         Argument(key='tencent-source-old', alias_list=['-tct-old', '-tso'],
                                  help_text='使用旧的腾讯源'),
                         ]
        self.default_arg = self.arg_list[0]
        self.data_source = CovidDataTencentAdvanced()
        self.detail_description = '默认输出本土新增数目前5个省份的数据，可通过参数修改。' \
                                  '公布数据表示前一天病例数，数据在上午10点左右更新密集，可能有部分省份更新缓慢。\n' \
                                  '举例，发送“疫情数据 -s 现有 -r 福建”，以现有病例数查看福建本土疫情形势。'

    def internal_handle(self, request):
        self.deactivate()
        responses = []

        # 检查s参数（sort by）
        sort_by = self.arg_dict['sort-by'].value
        default_sort_by = '新增'

        # 检查tct/tct-old参数，换源
        if self.arg_dict['baidu-source'].called:
            self.data_source = CovidData()
        elif self.arg_dict['tencent-source'].called:
            self.data_source = CovidDataTencentAdvanced()
        elif self.arg_dict['tencent-source-old'].called:
            self.data_source = CovidDataTencent()
            default_sort_by = '现有'  # 旧腾讯源没有新增

        # 检查nc参数，获取数据
        if self.arg_dict['no-cache'].called or not self.data_source.load_cache():
            self.data_source.load()
        else:
            self.data_source.load_cache()
        df = self.data_source.df

        # 检查t参数
        try:
            top_num = int(self.arg_dict['top-num'].value)
        except ValueError:
            top_num = 5
            responses.append(ResponseMsg(f'【{self.session_type}】输出数量非法，使用默认值'))

        # 检查r参数，获取数据
        if self.arg_dict['region'].value is None:  # default, all locals
            # cols = ['省份', '新增', '现有', '累计', '治愈', '死亡']
            cols = list(df.columns)
            try:
                cols.remove('地区')  # 去掉地区列
            except ValueError:
                pass

            df_local = df[df['地区'] == '本土病例']
            try:
                df_local = df_local.sort_values(sort_by, ascending=False)
            except KeyError:  # not exist
                df_local = df_local.sort_values(default_sort_by, ascending=False)

            if top_num > 0:
                responses.append(ResponseMsg(f'【{self.session_type} - 本土数据】\n'
                                             f'{self.data_source.update_time} '
                                             f'({self.data_source.get_days_passed()} days ago)\n'
                                             f'{df_local[:top_num].to_string(columns=cols, index=False)}'))
            elif top_num < 0:
                responses.append(ResponseMsg(f'【{self.session_type} - 本土数据】\n'
                                             f'{self.data_source.update_time} '
                                             f'({self.data_source.get_days_passed()} days ago)\n'
                                             f'{df_local[top_num:].to_string(columns=cols, index=False)}'))
            else:
                responses.append(ResponseMsg(f'【{self.session_type}】空白输出'))
        else:
            df_new = df[df['省份'] == self.arg_dict['region'].value]
            try:
                df_new = df_new.sort_values(sort_by, ascending=False)
            except KeyError:
                df_new = df_new.sort_values(default_sort_by, ascending=False)

            # cols = ['地区', '新增', '现有', '累计', '治愈', '死亡']
            cols = list(df.columns)
            try:
                cols.remove('省份')  # 去掉省份列
            except ValueError:
                pass

            if len(df_new) == 0:
                responses.append(ResponseMsg(f'【{self.session_type}】空白输出'))
            else:
                df_new.sort_values(sort_by, ascending=False)
                responses.append(ResponseMsg(f'【{self.session_type} - 全省数据】\n'
                                             f'{self.data_source.update_time} '
                                             f'({self.data_source.get_days_passed()} days ago)\n'
                                             f'{df_new.to_string(columns=cols, index=False)}'))

        return responses


class CovidDataUpdateSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 30
        self.session_type = '更新疫情感染数据缓存'
        self.strict_commands = ['疫情数据缓存', '更新疫情数据']
        self.description = '手动进行疫情感染数据缓存更新'
        self.arg_list = [Argument(key='confirm', alias_list=['-y'],
                                  required=True,
                                  ask_text='查询时间较长，任意回复以开始查询'),
                         Argument(key='baidu-source', alias_list=['-bd', '-bs'],
                                  help_text='使用百度源'),
                         Argument(key='tencent-source', alias_list=['-tct', '-ts'],
                                  help_text='使用腾讯源（默认）'),
                         Argument(key='tencent-source-old', alias_list=['-tct-old', '-tso'],
                                  help_text='使用旧的腾讯源'),
                         ]

    def internal_handle(self, request):
        self.deactivate()
        source_list = []
        responses = []
        if self.arg_dict['baidu-source'].called:
            source_list.append(CovidData)
        if self.arg_dict['tencent-source-old'].called:
            source_list.append(CovidDataTencent)
        if self.arg_dict['tencent-source'].called or len(source_list) == 0:
            source_list.append(CovidDataTencentAdvanced)

        for source in source_list:
            start = time.time()
            covid_data_cache_update(source_class=source)
            responses.append(ResponseMsg(f'【{self.session_type}】{source.__name__} [{time.time()-start:.2f} s] done'))

        return responses


class CovidData:
    def __init__(self):
        self.webdriver_dir = webdriver_dir
        self.cache_header = 'covid-data-baidu'
        self.cache_dir = CACHE_DIR
        self.update_time = None
        self._time_pattern = "%Y-%m-%d-%H-%M-%S"
        self.df = None

    def save_cache(self):
        filename = os.path.join(CACHE_DIR,
                                f'{self.cache_header}_{self.update_time}.xlsx')
        self.df.to_excel(filename, index=False)

    def load_cache(self):
        cache_file_list = []
        for filename in os.listdir(self.cache_dir):
            if filename[:len(self.cache_header)] == self.cache_header:
                cache_file_list.append(filename)
        cache_file_list.sort(reverse=True)  # new ones in the front
        if cache_file_list:
            filename = cache_file_list[0]
            self.df = pd.read_excel(os.path.join(self.cache_dir, filename))
            self.update_time = filename.replace(f'{self.cache_header}_', '').replace('.xlsx', '')
            return True
        else:
            return False

    def load(self):
        self._get_dataframe(self._get_soup_with_selenium())
        self.update_time = datetime.datetime.now().strftime(self._time_pattern)

    def get_days_passed(self):
        if self.update_time is None:
            return -1
        else:
            t = datetime.datetime.strptime(self.update_time, self._time_pattern)
            delta = datetime.datetime.now() - t
            return delta.days

    def _get_soup_with_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)

        try:
            driver.get('https://voice.baidu.com/act/newpneumonia/newpneumonia')
            driver.find_element_by_xpath('//div[@id="nationTable"]/div/span').click()

            driver.find_element_by_id('fixedTableHeader').click()  # move to location

            provinces = list(driver.find_elements_by_xpath('//div[@id="nationTable"]/table/tbody/tr/td/div/span[2]/..'))
            incomplete_list = []

            for i, p in enumerate(provinces):
                try:
                    p.click()
                except ElementClickInterceptedException:
                    if p.text not in ['香港', '澳门', '台湾']:
                        incomplete_list.append(i)
                        print(f'fail to click {p.text}')

            retries = 5

            while incomplete_list:
                if retries > 0:
                    print(f'retry: {incomplete_list}')
                    time.sleep(0.2)
                    retries -= 1
                else:
                    print('max retries, pass')
                    break
                new_incomplete = []
                for i in incomplete_list:
                    try:
                        provinces[i].click()
                    except ElementClickInterceptedException:
                        new_incomplete.append(i)
                        print(f'fail to click {provinces[i].text}')
                incomplete_list = new_incomplete

            s = driver.page_source

            soup = bs4.BeautifulSoup(s, 'html.parser')
        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()
        return soup

    def _get_dataframe(self, soup):
        table = soup.find('div', {'id': 'nationTable'})

        table_head = ['省份']
        for i in table.thead.tr:
            table_head.append(i.text)

        records = []
        current_province = ''

        for tag in table.tbody.children:
            if tag.attrs:  # total table, as province
                current_record = []
                for i in tag.children:
                    t = i.text
                    if t == '-':  # 转为0
                        current_record.append(0)
                    elif t.isdigit():  # 转为数字
                        current_record.append(int(t))
                    else:
                        current_record.append(t)
                # current_record.insert(0, current_record[0])
                current_record.insert(1, '全省')  # 将省份名挤到第一位，第二位设置为全省
                current_province = current_record[0]
                records.append(current_record)
            else:  # sub table of current province
                for subtag in tag.td.table.tbody.children:
                    current_record = [current_province]
                    for i in subtag.children:
                        t = i.text
                        if t == '-':  # 转为0
                            current_record.append(0)
                        elif t.isdigit():  # 转为数字
                            current_record.append(int(t))
                        else:
                            current_record.append(t)
                    records.append(current_record)

        # 更新部分地区无症状数据
        for region in PROVINCE_RECHECK:
            data_dict = self._get_region_data(region=region)
            infections = self._get_infections_from_data(data_dict=data_dict,
                                                        table_heads=table_head,
                                                        n_days=N_DAYS_TO_CURE)
            if infections is not None:
                records.append(infections)

        # 计算本土病例
        local_data = {}
        head_skip = 2  # skip 两列
        for i in records:
            if i[0] in ['香港', '澳门', '台湾']:  # 排除港澳台
                continue
            if i[0] not in local_data.keys():  # 新条目
                local_data[i[0]] = np.zeros(shape=len(table_head) - head_skip,
                                            dtype='int')
            try:
                if i[1] in ['全省', '无症状']:  # 总数/无症状
                    local_data[i[0]] += np.array(i[head_skip:])
                elif '境外' in i[1]:  # 减去境外
                    local_data[i[0]] -= np.array(i[head_skip:])
            except Exception:
                del local_data[i[0]]  # 数据错误，删除条目
        for p, n in local_data.items():
            records.append([p, '本土病例'] + list(n))  # 更新数据

        df = pd.DataFrame(data=records, columns=table_head)

        # mod: 2022-03-29, baidu removed current cases since 2022-03-18
        if '现有' not in df.columns:
            df['现有'] = df['累计'] - df['治愈'] - df['死亡']

        self.df = df

    # 获取地区页面的数据
    def _get_region_data(self, region='上海'):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)

        try:
            # driver.get('https://voice.baidu.com/act/newpneumonia/newpneumonia')
            driver.get(f'https://voice.baidu.com/newpneumonia/getv2?'
                       f'from=mola-virus&stage=publish&target=trend&isCaseIn=1&area={region}')

            res = re.search(r'{"status":.*]}', driver.page_source)
            data = json.loads(res.group())
        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()
        return data

    # 从地区页面数据获取无症状感染数
    @staticmethod
    def _get_infections_from_data(data_dict, table_heads, n_days=30):
        province = data_dict['data'][0]['name']
        for d in data_dict['data'][0]['trend']['list']:
            if d['name'] == '新增无症状':
                num_list = np.array(d['data'])
                results = {'省份': province,
                           '地区': '无症状',
                           '新增': num_list[-1],
                           '累计': np.sum(num_list),
                           '治愈': np.sum(num_list[:-1*n_days]),
                           '现有': np.sum(num_list[-1*n_days:]),
                           '死亡': 0}
                result_list = []
                for key in table_heads:
                    result_list.append(results.get(key, 0))
                return result_list
        return None


class CovidDataTencent(CovidData):
    def __init__(self):
        CovidData.__init__(self)
        self.cache_header = 'covid-data-tencent'

    def _get_soup_with_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)

        try:
            driver.get('https://news.qq.com/zt2020/page/feiyan.htm#/')

            provinces = list(driver.find_elements_by_xpath('/html/body/div[1]/div[2]/div[4]/'
                                                           'div[3]/table[2]/tbody/tr[1]/th/p[1]/span'))
            incomplete_list = []

            for i, p in enumerate(provinces):
                try:
                    p.click()
                except ElementClickInterceptedException:
                    incomplete_list.append(i)
                    print(f'fail to click {p.text}')

            retries = 5

            while incomplete_list:
                if retries > 0:
                    print(f'retry: {incomplete_list}')
                    time.sleep(0.2)
                    retries -= 1
                else:
                    print('max retries, pass')
                    break
                new_incomplete = []
                for i in incomplete_list:
                    try:
                        provinces[i].click()
                    except ElementClickInterceptedException:
                        new_incomplete.append(i)
                        print(f'fail to click {provinces[i].text}')
                incomplete_list = new_incomplete

            s = driver.page_source

            soup = bs4.BeautifulSoup(s, 'html.parser')
        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()
        return soup

    def _get_dataframe(self, soup):
        table = soup.find(id='listWraper')

        table_head = ['省份']  # 地区, 现有, 累计, 治愈, 死亡
        for i in table.table.thead.tr.children:
            table_head.append(i.text)
        table_head = table_head[:-1]  # 去掉详情列

        records = []

        for province in table.table.next_sibling.children:
            current_province = province.tr.th.p.span.text
            # 全省数据
            total_record = [current_province, '全省']
            for i in province.find_all(attrs={'class': 'bold'}):
                t = i.text
                if '-' in t:  # 转为0
                    total_record.append(0)
                elif t.isdigit():  # 转为数字
                    total_record.append(int(t))
                else:
                    total_record.append(t)
            records.append(total_record)

            # 地区数据
            for c in province.find_all(attrs={'class': 'city'}):
                current_record = [current_province]
                for i in c.children:
                    t = i.text
                    if '-' in t:  # 转为0
                        current_record.append(0)
                    elif t.isdigit():  # 转为数字
                        current_record.append(int(t))
                    else:
                        current_record.append(t)
                records.append(current_record[:-1])  # 跳过详情列

        # 更新部分地区无症状数据
        for region in PROVINCE_RECHECK:
            data_dict = self._get_region_data(region=region)
            infections = self._get_infections_from_data(data_dict=data_dict,
                                                        table_heads=table_head,
                                                        n_days=N_DAYS_TO_CURE)
            if infections is not None:
                records.append(infections)

        # 计算本土病例
        local_data = {}
        head_skip = 2  # skip 两列
        for i in records:
            if i[0] in ['香港', '澳门', '台湾']:  # 排除港澳台
                continue
            if i[0] not in local_data.keys():  # 新条目
                local_data[i[0]] = np.zeros(shape=len(table_head) - head_skip,
                                            dtype='int')
            try:
                if i[1] in ['全省', '无症状']:  # 总数&无症状
                    local_data[i[0]] += np.array(i[head_skip:])
                elif '境外' in i[1]:  # 减去境外
                    local_data[i[0]] -= np.array(i[head_skip:])
            except Exception:
                del local_data[i[0]]  # 数据错误，删除条目
        for p, n in local_data.items():
            records.append([p, '本土病例'] + list(n))  # 更新数据

        df = pd.DataFrame(data=records, columns=table_head)

        self.df = df

    # 获取地区页面的数据
    def _get_region_data(self, region='上海'):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)

        try:
            driver.get(f'https://api.inews.qq.com/newsqa/v1/query/pubished/daily/list?province={region}')

            res = re.search(r'{"ret":.*]}', driver.page_source)
            data = json.loads(res.group())
        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()
        return data

    # 从地区页面数据获取无症状感染数
    @staticmethod
    def _get_infections_from_data(data_dict, table_heads, n_days=30):
        data_new = data_dict['data'][-1]

        # get increse list
        add_list = []
        for i_data in data_dict['data']:
            add_list.append(int(i_data['wzz_add']))

        results = {'省份': data_new['province'],
                   '地区': '无症状',
                   '新增': data_new['wzz_add'],  # also add_list[-1]
                   '现有': data_new['wzz'],
                   '治愈': np.sum(add_list[:-1*n_days]),
                   '累计': np.sum(add_list)}
        result_list = []
        for key in table_heads:
            result_list.append(results.get(key, 0))
        return result_list


# 2022-04-08: better data
class CovidDataTencentAdvanced(CovidData):
    def __init__(self):
        CovidData.__init__(self)
        self.cache_header = 'covid-data-tencent-advanced'

    def load(self):
        self._get_data_advanced()
        self.update_time = datetime.datetime.now().strftime(self._time_pattern)

    def _get_data_advanced(self):

        # 从selenium获取tree_data
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=self.webdriver_dir)

        try:
            driver.get('https://api.inews.qq.com/newsqa/v1'
                       '/query/inner/publish/modules/list?modules=statisGradeCityDetail,diseaseh5Shelf')
            data = json.loads(re.search('{"ret".*}', driver.page_source).group())
            tree_data = data['data']['diseaseh5Shelf']['areaTree']

        except Exception as e:
            driver.quit()
            raise e
        else:
            driver.quit()

        # tree data组织如下
        # root为国，下一级为省，再下一级为地区
        # 每个节点有三个properties
        # name: 地区名
        # today: confirm, confirmCuts(全部为0), isUpdated, wzz_add
        # total: confirm, dead, heal, wzz, nowConfirm, provinceLocalConfirm(除港澳台)

        today_cols = ['新增', '新增无症状']
        today_keys = ['confirm', 'wzz_add']
        total_cols = ['现有', '现有无症状', '累计', '累计本土',
                      '治愈', '死亡']
        total_keys = ['nowConfirm', 'wzz', 'confirm', 'provinceLocalConfirm',
                      'heal', 'dead']

        table_head = ['省份', '地区'] + today_cols + total_cols

        def get_numbers(knot):
            num_list = []
            for key in today_keys:
                num_list.append(knot['today'].get(key, 0))
            for key in total_keys:
                num_list.append(knot['total'].get(key, 0))
            return num_list

        records = []

        for province in tree_data[0]['children']:
            current_province = province['name']
            records.append([current_province, '全省'] + get_numbers(province))
            for city in province['children']:
                records.append([current_province, city['name']]
                               + get_numbers(city))

        # 计算本土病例
        local_data = {}
        head_skip = 2  # skip 两列
        for i in records:
            if i[0] in ['香港', '澳门', '台湾']:  # 排除港澳台
                continue
            if i[0] not in local_data.keys():  # 新条目
                local_data[i[0]] = np.zeros(shape=len(table_head) - head_skip,
                                            dtype='int')
            try:
                if i[1] in ['全省', '无症状']:  # 总数/无症状
                    local_data[i[0]] += np.array(i[head_skip:])
                elif '境外' in i[1]:  # 减去境外
                    local_data[i[0]] -= np.array(i[head_skip:])
            except Exception:
                del local_data[i[0]]  # 数据错误，删除条目
        for p, n in local_data.items():
            records.append([p, '本土病例'] + list(n))  # 更新数据

        self.df = pd.DataFrame(data=records, columns=table_head)


def covid_data_cache_update(source_class=CovidData):
    cds = source_class()
    cds.load()
    cds.save_cache()


def covid_data_cache_update_schedule():
    for source in [CovidDataTencentAdvanced, CovidData, CovidDataTencent]:
        try:
            covid_data_cache_update(source_class=source)
        except:
            pass