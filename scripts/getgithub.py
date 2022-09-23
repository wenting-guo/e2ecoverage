# python-gitlab

from github import Github
import sys

from pymysql import NULL
sys.path.append('.')
sys.path.append('./scripts')
from scripts import db_utils
import datetime

class getgithub:
    # 初始化
    def __init__(self):
        # 服务器地址
        self.url = 'https://github.com/'
        # 前面生成的Access Token
        self.accessToken = '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'

    # 登录
    def login(self):
        gl = Github(self.accessToken)
        return gl

    # 获得project下单个文件
    def githubDownload(self, projectPath, gitfilepath, localpath):
        gl = self.login()
        # 获取repo
        repo =gl.get_repo(projectPath)
        # 获得文件
        f = repo.get_contents(gitfilepath)
        # 存到本地
        with open(localpath, 'wb') as code:
            code.write(f.decoded_content)


cur_year = datetime.datetime.now().year
datetime_range = {
  '01': {'dt_createdAfter': datetime.datetime(cur_year, 1, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 1, 31, 23, 59, 59)},
  '02': {'dt_createdAfter': datetime.datetime(cur_year, 2, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 2, 28, 23, 59, 59)},
  '03': {'dt_createdAfter': datetime.datetime(cur_year, 3, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 3, 31, 23, 59, 59)},
  '04': {'dt_createdAfter': datetime.datetime(cur_year, 4, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 4, 30, 23, 59, 59)},
  '05': {'dt_createdAfter': datetime.datetime(cur_year, 5, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 5, 31, 23, 59, 59)},
  '06': {'dt_createdAfter': datetime.datetime(cur_year, 6, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 6, 30, 23, 59, 59)},
  '07': {'dt_createdAfter': datetime.datetime(cur_year, 7, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 7, 31, 23, 59, 59)},
  '08': {'dt_createdAfter': datetime.datetime(cur_year, 8, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 8, 31, 23, 59, 59)},
  '09': {'dt_createdAfter': datetime.datetime(cur_year, 9, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 9, 30, 23, 59, 59)},
  '10': {'dt_createdAfter': datetime.datetime(cur_year, 10, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 10, 31, 23, 59, 59)},
  '11': {'dt_createdAfter': datetime.datetime(cur_year, 11, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 11, 30, 23, 59, 59)},
  '12': {'dt_createdAfter': datetime.datetime(cur_year, 12, 1, 00, 00, 00), 'dt_createdBefore': datetime.datetime(cur_year, 12, 31, 23, 59, 59)}
}
cur_month = datetime.datetime.now().strftime("%Y%m")
only_month = datetime.datetime.now().strftime("%m")
dt_createdAfter = datetime_range[only_month]['dt_createdAfter']

def getGithubIssues():
    gl = Github("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")
    mysqldb = db_utils.mysqldb()
    githubProjectNames= mysqldb.selectData('select projectName from githubProjects;')
    for prj in githubProjectNames:
        print('>>>>>>>>>project: ', prj[0])
        repo = gl.get_repo(prj[0])
        for label in repo.get_labels():
            if 'bug' in label.name:
                print('bug lables: ', label.name)
                # for history issues
                # issues = repo.get_issues(state='all', labels=[label.name])
                # for current month
                issues = repo.get_issues(state='all', labels=[label.name], since=dt_createdAfter)
                for iss in issues:
                    issNumber = iss.number
                    sql_number = repo.get_issue(number=issNumber).number
                    sql_projectName = prj[0]
                    sql_state = repo.get_issue(number=issNumber).state
                    sql_created_at = repo.get_issue(number=issNumber).created_at
                    sql_github_username = repo.get_issue(number=issNumber).user.login
                    sql_labels = repo.get_issue(number=issNumber).labels
                    sql = 'insert into {0} values({1}, \'{2}\', \'{3}\', \'{4}\', \'{5}\', {6}, \'{7}\');'.format("githubIssueDetail",\
                          sql_number, sql_projectName, sql_state, sql_created_at, sql_github_username, NULL,','.join(i.name for i in sql_labels))
                    mysqldb.insertTable(sql)
    mysqldb.closeDB()


def generateGithubIssueStatistic():
    mysqldb = db_utils.mysqldb()
    # 初始处理包括202206之前的数据：
    # insert into githubBugStatistics (projectName, github_username, allIssues, byMonth) select projectName, \
    # github_username, count(number), date_format(now(), '%Y%m') from githubIssueDetail group by projectName, github_username;

    if cur_month != '202206': 
        # 当月数据处理
        # 1. 此处在重新统计前应先删掉已统计数据
        origin_rows = mysqldb.selectData('select projectName, github_username, byMonth from githubBugStatistics where byMonth = date_format(curdate(), \'%Y%m\');')
        for i in origin_rows:
            mysqldb.deleteData('DELETE FROM {0} where projectName=\'{1} \'and github_username=\'{2}\' and byMonth=\'{3}\';'.format('githubBugStatistics', i[0], i[1], i[2]))
        # 2. 统计issueDetail表
        sql = 'select projectName, github_username, count(number) from githubIssueDetail \
                where date_format(created_at, \'%Y%m\') = date_format(curdate(), \'%Y%m\') group by projectName, github_username;'
        origin_rows = mysqldb.selectData(sql)
        for i in origin_rows:
            mysqldb.insertTable('insert into githubBugStatistics (projectName, github_username, allIssues, byMonth) values\
                                    (\'{0}\', \'{1}\', {2}, \'{3}\')'.format(i[0], i[1], i[2], cur_month))
    mysqldb.closeDB()


# test
if __name__=='__main__':
    #getGithubIssues()
    # generateGithubIssueStatistic()
    getgithub().githubDownload("kubean-io/kubean", "doc/test/kubean_testcase.md", "/Users/xujiewei/dev/e2ecoverage/case/kubean/kubean_testcase.md")


