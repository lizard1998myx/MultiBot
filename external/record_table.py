# created in 20220427
import pandas as pd
import os


class RecordNotFoundError(Exception):
    pass


class RecordTable:
    def __init__(self, table_file, string_cols=None):
        if string_cols is None:
            string_cols = []
        self.table_file = table_file
        self._current_records = []  # current records that are viewed
        self._string_cols = string_cols  # 转化为string的列

    def is_exist(self):
        return os.path.exists(self.table_file)

    def get_dfl(self) -> list:
        if os.path.exists(self.table_file):
            df = pd.read_excel(self.table_file)
            for col in self._string_cols:
                df[col] = df[col].astype(str)
            return df.to_dict('records')
        else:
            # 新建表格
            return []

    def find_all(self, **kwargs) -> list:
        for k in kwargs.keys():
            if k not in self._string_cols:
                raise KeyError('仅支持string')
        if not self.is_exist():
            return []
        df = pd.read_excel(self.table_file)
        for col in self._string_cols:
            df[col] = df[col].astype(str)
        for k, v in kwargs.items():
            if v is not None:
                df = df[df[k].astype(str) == str(v)]  # filter
        return df.to_dict('records')

    def append_full(self, item: dict):
        # 读取原数据
        dfl = self.get_dfl()
        dfl.append(item)
        # 保存数据
        pd.DataFrame(dfl).to_excel(self.table_file, index=False)

    # 删除一条记录
    def delete(self, record, from_new=True):
        dfl = self.get_dfl()
        if from_new:
            dfl = dfl[::-1]
        for i, r in enumerate(dfl):  # from new
            if r == record:
                dfl = dfl[:i] + dfl[i+1:]
                pd.DataFrame(dfl).to_excel(self.table_file, index=False)
                return
        raise RecordNotFoundError

    # 替换一条记录
    def replace(self, record_old, record_new):
        dfl = self.get_dfl()
        for i, r in enumerate(dfl):
            if r == record_old:
                dfl = dfl[:i] + [record_new] + dfl[i+1:]
                pd.DataFrame(dfl).to_excel(self.table_file, index=False)
                return
        raise RecordNotFoundError

    @staticmethod
    def list_single_record(record) -> str:
        return str(record)

    def list_records(self, record_list=None) -> str:
        if record_list is None:
            record_list = self.get_dfl()
        self._current_records = record_list  # loaded to current_records list
        msg = ''
        for i, r in enumerate(record_list):
            msg += f'{i + 1}. {self.list_single_record(r)}\n'
        msg = msg[:-1]
        return msg

    def pop_by_index(self, index, from_new=True):
        i_del = int(index) - 1  # possible ValueError
        if i_del < 0 or i_del >= len(self._current_records):
            raise IndexError('超出范围')
        self.delete(record=self._current_records[i_del], from_new=from_new)
        return self._current_records[i_del]

