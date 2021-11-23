from .argument import ArgSession, Argument
from ..responses import ResponseMsg
import arxiv, datetime


class ArxivSession(ArgSession):
    def __init__(self, user_id):
        ArgSession.__init__(self, user_id=user_id)
        self._max_delta = 60
        self.session_type = 'arXiv'
        self.strict_commands = ['arxiv', 'paper', '今日天文']
        self.description = '基于python的arxiv包进行文章搜索'
        self.arg_list = [Argument(key='query', alias_list=['-q', '-s', '--search', '--query'],
                                  required=True, get_next=True,
                                  ask_text='你想阅读什么领域？或输入搜索关键词（结果从新到旧显示）',
                                  help_text='查询关键词，规则见https://arxiv.org/help/api/user-manual#_query_interface')]
        self.default_arg = self.arg_list[0]
        self.query_string = None
        self.results = None

    def internal_handle(self, request):
        if not self.query_string:
            query_msg = self.arg_dict['query'].value
            alias = {'宇宙': 'CO', '星系': 'GA', '恒星': 'SR', '太阳': 'SR', '高能': 'HE',
                     '行星': 'EP', '地球': 'EP', '仪器': 'IM', '方法': 'IM', '技术': 'IM',
                     '天文': '*'}
            for key, value in alias.items():
                if key in query_msg:
                    self.query_string = f'astro-ph.{value}'
                    break
            if not self.query_string:
                self.query_string = query_msg
            # 开始搜索
            self.results = search_by_query(query=self.query_string, max_results=100)
            # 如果未找到结果，退出
            if not self.results:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】使用[{self.query_string}]无搜索结果')
            else:
                responses = []
            # 尝试根据catalogue进行筛选
            new_results = filter_primary(self.results, primary_cat=self.query_string)
            if new_results:
                self.results = new_results
            # 尝试根据日期进行筛选
            new_results = filter_today(self.results)
            if new_results:
                self.results = new_results
                responses.append(ResponseMsg(f'【{self.session_type}】使用[{self.query_string}]找到{len(self.results)}条今天的结果'))
            else:
                responses.append(ResponseMsg(f'【{self.session_type}】使用[{self.query_string}]找到{len(self.results)}条过去的结果'))
            # 如果只有一条，直接显示
            if len(self.results)==1:
                self.deactivate()
                responses.append(ResponseMsg(paper_brief(self.results[0])))
            else:
                responses.append(ResponseMsg(f'【{self.session_type}】输入1到{len(self.results)}之间的数字查看简报'))
            return responses
        else:
            try:
                i = int(request.msg)
            except ValueError:
                self.deactivate()
                return ResponseMsg(f'【{self.session_type}】输入不合法，退出')
            if i > 0:
                i -= 1
            try:
                brief = paper_brief(self.results[i])
            except IndexError:
                return ResponseMsg(f'【{self.session_type}】超出范围，请输入1到{len(self.results)}之间的数字')
            else:
                return ResponseMsg(brief)


# 搜索arxiv文章，100条以上时间会激增
def search_by_query(query='astro-ph.*', max_results=100):
    s = arxiv.Search(query=query, max_results=max_results,
                     sort_by=arxiv.SortCriterion.LastUpdatedDate,
                     sort_order=arxiv.SortOrder.Descending)
    return list(s.get())


# 只看当天文章
def filter_today(input_list):
    output_list = []
    for result in input_list:
        if datetime.date.today()==result.published.date():
            output_list.append(result)
    return output_list


# 只看某个主要cat的文章
def filter_primary(input_list, primary_cat):
    output_list = []
    for result in input_list:
        if result.primary_category==primary_cat:
            output_list.append(result)
    return output_list


# 输出文章简报
def paper_brief(result: arxiv.Result):
    authors = []
    for author in result.authors:
        authors.append(author.name)
    brief = f'{result.title}\n'
    brief += ', '.join(authors)
    brief += '\n'
    brief += ', '.join(result.categories)
    brief += f'\n{result.published.date().isoformat()} {result.entry_id}\n\n'
    brief += f'{result.summary}'
    return brief

