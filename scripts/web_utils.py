# -*- coding: utf-8 -*- 

from gitlab import GitlabError, GitlabGetError
import gitlab
import os, re
import json
from git.repo import Repo
import anybadge
import logging
import sys

sys.path.append('.')
sys.path.append('./scripts')
from scripts.getgitlab import getgitlab
import scripts.md_utils as md_utils
from scripts.getgitlab import *
from scripts import db_utils
from scripts import md_utils

import dateutil.relativedelta
import datetime

### refer: https://github.com/jongracecox/anybadge

# 1.实例化 Logging类
logger = logging.getLogger(__name__)
# 2.记录器 Logger.setLevel() 设置日志等级
logger.setLevel(level=logging.INFO)
# 3.自定义格式化formatter 
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# 4.输出到console/文件
# 控制台
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
# 文件
file_handler = logging.FileHandler("e2e-web.log")
file_handler.setFormatter(formatter)
# 5.添加处理程序，可以在一个logger添加读个handler
logger.addHandler(console_handler)
logger.addHandler(file_handler)

gitlab_cfg = {
    "url": "https://gitlab.daocloud.cn",
    "token": "PxG2VPUgaEhxtMrwhT6e"
}

current_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(current_path)
prjJsFile = parent_path + '/case/projects.json'
cfgFile = parent_path + '/case/casepath.ini'
UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%f+08:00"

# 登陆gitlab
gl = gitlab.Gitlab(gitlab_cfg["url"], private_token=gitlab_cfg["token"])


def readFile(filePath):
    with open(filePath, "r") as prjFile:
        projectData = json.load(prjFile)
    return projectData


def getAllPrj(keyword):
    projects = gl.projects.list(search=keyword)
    projectIds = {(x.id, x.name) for x in projects}
    return dict(projectIds)


def getRegisteredPrj():
    return readFile(prjJsFile)


def registerPrj(ID):
    repo = Repo(parent_path)
    repo.remote().pull  # 拉取最新的代码
    logger.info("repo.active_branch:")
    logger.info(repo.active_branch)
    try:
        projectInfo = gl.projects.get(ID)
    except GitlabGetError as e:
        return "Gitlab project Not Found 项目注册失败, 请检查ID是否正确"
    if projectInfo is None:
        return "项目注册失败, 请检查ID是否正确"
    projectData = readFile(prjJsFile)
    logger.info("projects.json已注册项目: ", projectData)
    if str(ID) in projectData.keys():
        return "项目已注册，无需再次注册"
    try:
        # 1 将new projectID写入case/projects.json文件
        projectData[str(projectInfo.id)] = projectInfo.name
        with open(prjJsFile, "w", encoding="utf-8") as newFile:
            json.dump(projectData, newFile, indent=2, sort_keys=True, ensure_ascii=False)
        # 把更新的projects.json上传到gitlab e2e-test-coverage仓库里保存
        repo.index.add(prjJsFile)
        repo.index.commit('registerPrj service commit updated projects.json')
        repo.remote().push(repo.active_branch)
    except GitlabError as e:
        return "gitlab err: {0}".format(e)
    return "项目注册成功, 请使用扫描接口生成coverage徽章"


def scanPrj(ID):
    repo = Repo(parent_path)
    repo.remote().pull  # 拉取最新的代码

    projectInfo = gl.projects.get(ID)
    # 1 确认项目是否已注册到projects.json文件中
    projectData = readFile(prjJsFile)
    prjName = projectData[str(ID)]
    if str(ID) not in projectData.keys():
        return 'Project ID不存在, 请确认是否已注册'

    # 2 读取配置文件case/casepath.ini
    cf = md_utils.getCaseFile()
    # 确认是否有[ProjectID]中是否有新注册的项目的key&value;如果没有则加入
    iniProjects = cf.options('ProjectID')
    if prjName not in iniProjects:
        cf.set('ProjectID', prjName, ID)
    # 确认[ProjectID]中是否有project这个标签,如果没有则将已注册项目写入
    prjItems = cf.sections()
    if prjName not in prjItems:
        git = getgitlab()
        # 2 解析docs/test/readme.md文件获取testcase.md文件名及路径
        localpath = parent_path + "/case/" + prjName
        md_utils.Create_folder(localpath)
        git.gitDownload(ID, "docs/test/README.md", localpath + "/README.md", projectInfo.default_branch)
        caseList = md_utils.parseReadmeFile(localpath + "/README.md")
        # 2 根据case/casepath.ini中的项目case下载md文件到case/目录中
        cf.add_section(prjName)
        for k, v in caseList.items():
            cf.set(prjName, k, v)
        with open(cfgFile, 'w') as configfile:
            cf.write(configfile)
        repo.index.add(parent_path + "/case/casepath.ini")

    # 3 计算完成率生成徽章svg文件，将应该push到仓库的文件push到remote仓库
    try:
        md_utils.generateBadges(prjName, "")
    except GitlabError as e:
        return "gitlab err: {0}".format(e)
        # 4 将new/updated files git add到远程仓库中
    repo.index.add(parent_path + "/badges/")
    repo.index.commit('scanPrj service commit updated casepath.ini or badges')
    repo.remote().push(repo.active_branch)
    return "coverage徽章已生成, 请查看本项目仓库中badges目录"


def getEarliestNote(projectInfo, issueID):
    # 找到issue最早的comment
    issueInfo = projectInfo.issues.get(issueID.iid, lazy=True)
    notes = issueInfo.notes.list()
    if len(notes) != 0:
        earliest_comm_createTime = datetime.datetime.strptime(notes[0].created_at, UTC_FORMAT)
        for n in notes:
            try:
                i_note = issueInfo.notes.get(n.id)
            except GitlabError as e:
                print("gitlab err: {0}".format(e))
            if datetime.datetime.strptime(i_note.created_at, UTC_FORMAT) < earliest_comm_createTime:
                earliest_comm_createTime = datetime.datetime.strptime(i_note.created_at, UTC_FORMAT)
    else:
        earliest_comm_createTime = datetime.datetime.now()
    return earliest_comm_createTime


def scanIssue(ID):
    now_time = datetime.datetime.now()
    projectInfo = gl.projects.get(ID)
    ### 当月issue(kind/bug) 平均修复时间
    # 获取所有open的bugs并合计其创建总时长
    open_bugs = projectInfo.issues.list(all=True, labels='kind/bug', state='opened')
    open_bugs_created_at_totalTime = datetime.timedelta()
    for i in open_bugs:
        created_at_timeFormat = datetime.datetime.strptime(i.created_at, UTC_FORMAT)
        open_bugs_created_at_totalTime = (now_time - created_at_timeFormat) + open_bugs_created_at_totalTime
    # 获取所有截止当天为止30天以内close的bugs并合计其花费时长
    close_bugs = projectInfo.issues.list(all=True, labels='kind/bug', state='closed')
    close_bugs_in30 = 0
    close_bugs_closed_at_totalTime = datetime.timedelta()
    for i in close_bugs:
        closed_at_timeFormat = datetime.datetime.strptime(i.closed_at, UTC_FORMAT)
        created_at_timeFormat = datetime.datetime.strptime(i.created_at, UTC_FORMAT)
        if (now_time - closed_at_timeFormat).days <= 30:
            close_bugs_in30 += 1
            close_bugs_closed_at_totalTime = (
                                                     closed_at_timeFormat - created_at_timeFormat) + close_bugs_closed_at_totalTime
    if len(open_bugs) == 0 and close_bugs_in30 == 0:
        average_fix_time_perMonth = datetime.timedelta(days=0)
    else:
        average_fix_time_perMonth = (open_bugs_created_at_totalTime + close_bugs_closed_at_totalTime) / (
                len(open_bugs) + close_bugs_in30)
    print("open_bugs: ", len(open_bugs), "close_bugs_in30: ", close_bugs_in30, "close_bugs_closed_at_totalTime: ",
          close_bugs_closed_at_totalTime, "open_bugs_created_at_totalTime: ", open_bugs_created_at_totalTime)
    print('average_fix_time_perMonth: ', average_fix_time_perMonth)
    # white, silver, gray, black, red, brightred, maroon, olive, lime, brightyellow, yellow, green, yellowgreen, aqua, teal, blue, navy, fuchsia, purple, orange, lightgrey
    average_fix_time_perMonth_thresholds = {'30d': 'teal',
                                            '60d': 'green',
                                            '90d': 'yellow',
                                            '91d': 'red'}
    # 检查badges目录下是否有project name目录，如果没有则创建
    if not os.path.exists(parent_path + "/badges/" + projectInfo.name):
        os.mkdir(parent_path + "/badges/" + projectInfo.name)
    average_fix_time_perMonth_svgFile = parent_path + "/badges/" + projectInfo.name + '/average_fix_time_perMonth.svg'
    average_fix_time_perMonth_badge = md_utils.make_Badge_string("Bug Average Fix",
                                                                 str(average_fix_time_perMonth.days) + 'd',
                                                                 average_fix_time_perMonth_thresholds,
                                                                 average_fix_time_perMonth_svgFile)

    ### 未分类issue最长等待时间
    no_kind_issue = projectInfo.issues.list(all=True, labels=[None], state='opened')
    if len(no_kind_issue) == 0:
        earliest_time = datetime.timedelta(days=0)
    else:
        earliest_issue = no_kind_issue[0]
        earliest_time = now_time - datetime.datetime.strptime(no_kind_issue[0].created_at, UTC_FORMAT)
        for i in no_kind_issue:
            created_at_timeFormat = datetime.datetime.strptime(i.created_at, UTC_FORMAT)
            if now_time - created_at_timeFormat > earliest_time:
                earliest_time = now_time - datetime.datetime.strptime(i.created_at, UTC_FORMAT)
                earliest_issue = i
    print('earliest_time: ', earliest_time)
    earliest_issue_thresholds = {'7d': 'green',
                                 '30d': 'yellow',
                                 '31d': 'red'}
    earliest_issue_svgFile = parent_path + "/badges/" + projectInfo.name + '/earliest_issue.svg'
    earliest_issue_badge = md_utils.make_Badge_string("Untriage Issue", str(earliest_time.days) + 'd',
                                                      earliest_issue_thresholds, earliest_issue_svgFile)

    ### 当月 issue 平均回复时间
    openIssue_comment_replyTotalTime = datetime.timedelta()
    closeIssue_comment_replyTotalTime = datetime.timedelta()
    # 全部open的issue总回复时间
    open_issues = projectInfo.issues.list(all=True, state='opened')
    open_issue_replyTime = datetime.timedelta()
    if len(open_issues) != 0:
        for oi in open_issues:
            issue_createTime = datetime.datetime.strptime(oi.created_at, UTC_FORMAT)
            # 找到open issue最早的comment
            earliest_comm_createTime = getEarliestNote(projectInfo, oi)
            # 计算issue回复时间
            issue_comment_replyTime = earliest_comm_createTime - issue_createTime
            # 计算全部open issue的最早comment回复时间的总和
            openIssue_comment_replyTotalTime = openIssue_comment_replyTotalTime + issue_comment_replyTime
    print('openIssue_comment_replyTotalTime: ', openIssue_comment_replyTotalTime)
    # 30天内的close issue总回复时间
    close_issues = projectInfo.issues.list(all=True, state='closed')
    now_time = datetime.datetime.now()
    closeIssue_within30 = []
    if len(close_issues) != 0:
        for i in close_issues:
            # 找到30天以内关闭的issue
            closed_at_timeFormat = datetime.datetime.strptime(i.closed_at, UTC_FORMAT)
            if (now_time - closed_at_timeFormat).days <= 30:
                closeIssue_within30.append(i)
        if len(closeIssue_within30) != 0:
            for ci in closeIssue_within30:
                issue_createTime = datetime.datetime.strptime(ci.created_at, UTC_FORMAT)
                # 找到close issue最早的comment
                earliest_comm_createTime = getEarliestNote(projectInfo, ci)
                # 计算close issue回复时间
                issue_comment_replyTime = earliest_comm_createTime - issue_createTime
                # 计算30天内的close issue的最早comment回复时间的总和
                closeIssue_comment_replyTotalTime = closeIssue_comment_replyTotalTime + issue_comment_replyTime
    print('closeIssue_comment_replyTotalTime: ', closeIssue_comment_replyTotalTime)
    print('len(open_issues): ', len(open_issues), ', len(close_issues): ', len(close_issues))
    if len(open_issues) + len(close_issues) != 0:
        average_replyTime = (openIssue_comment_replyTotalTime + closeIssue_comment_replyTotalTime) / (
                len(open_issues) + len(close_issues))
    else:
        average_replyTime = datetime.timedelta(days=0)
    average_replyTime_thresholds = {'1d': 'teal',
                                    '7d': 'green',
                                    '30d': 'yellow',
                                    '31d': 'red'}
    average_replyTime_svgFile = parent_path + "/badges/" + projectInfo.name + '/average_replyTime.svg'
    average_replyTime_badge = md_utils.make_Badge_string("Reply Issue", str(average_replyTime.days) + 'd',
                                                         average_replyTime_thresholds, average_replyTime_svgFile)

    return "Issue徽章已生成, 请查看本项目仓库中badges目录"


# datetime range用于查询issues_statistics定位月份,例如
# dt_createdAfter = datetime(year=2022, month=4,day=1, hour=00, minute=00, second=01)
# dt_createdBefore = datetime(year=2022, month=4,day=30, hour=23, minute=59, second=59)
cur_year = datetime.datetime.now().year
datetime_range = {
    '01': {'dt_createdAfter': datetime.datetime(cur_year, 1, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 1, 31, 23, 59, 59)},
    '02': {'dt_createdAfter': datetime.datetime(cur_year, 2, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 2, 28, 23, 59, 59)},
    '03': {'dt_createdAfter': datetime.datetime(cur_year, 3, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 3, 31, 23, 59, 59)},
    '04': {'dt_createdAfter': datetime.datetime(cur_year, 4, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 4, 30, 23, 59, 59)},
    '05': {'dt_createdAfter': datetime.datetime(cur_year, 5, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 5, 31, 23, 59, 59)},
    '06': {'dt_createdAfter': datetime.datetime(cur_year, 6, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 6, 30, 23, 59, 59)},
    '07': {'dt_createdAfter': datetime.datetime(cur_year, 7, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 7, 31, 23, 59, 59)},
    '08': {'dt_createdAfter': datetime.datetime(cur_year, 8, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 8, 31, 23, 59, 59)},
    '09': {'dt_createdAfter': datetime.datetime(cur_year, 9, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 9, 30, 23, 59, 59)},
    '10': {'dt_createdAfter': datetime.datetime(cur_year, 10, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 10, 31, 23, 59, 59)},
    '11': {'dt_createdAfter': datetime.datetime(cur_year, 11, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 11, 30, 23, 59, 59)},
    '12': {'dt_createdAfter': datetime.datetime(cur_year, 12, 1, 00, 00, 00),
           'dt_createdBefore': datetime.datetime(cur_year, 12, 31, 23, 59, 59)}
}


# 此方法已废弃
def getBugStatistics(ID, projName, authorId, authorName):
    projectInfo = gl.projects.get(ID)
    # for历史数据
    stat = projectInfo.issues_statistics.get(scope='all', author_id=authorId, labels='kind/bug',
                                             created_before=datetime.datetime(cur_year, 5, 31, 23, 59, 59))
    cur_month = "2205"
    # for当月数据
    # stat = projectInfo.issues_statistics.get(scope='all',  author_id=authorId, labels='kind/bug', created_after=dt_createdAfter, created_before=dt_createdBefore)
    sql = 'insert into {0} values({1}, \'{2}\', {3}, \'{4}\', {5}, {6}, {7}, {8});'.format("bugStatistics", ID,
                                                                                           projName, authorId,
                                                                                           authorName,
                                                                                           stat.statistics["counts"][
                                                                                               "all"],
                                                                                           stat.statistics["counts"][
                                                                                               "closed"],
                                                                                           stat.statistics["counts"][
                                                                                               "opened"], cur_month)
    return sql


def getNDXProjectInfo():
    # ndx projects id list
    ndxProjectIDs = []
    ndx_descendant_groups = []
    # 存储project id与project members的dict
    # {"projectId_xxx": [{"id": 268, "username":"guangli.bao"}]}
    ndx_project_members = {}

    # 1. 获取ndx group下面的子目录和项目
    ndxGroup = gl.groups.get(102)
    ndxProjects = ndxGroup.projects.list(all=True)
    for j in ndxProjects:
        ndxProjectIDs.append(j.id)

    # 获取ndx下第一级groups
    # subgroups = ndxGroup.subgroups.list()
    # print(len(subgroups))

    # 2. 获取ndx下所有层级的groups
    descendant_groups = ndxGroup.descendant_groups.list(all=True)
    for i in descendant_groups:
        ndx_descendant_groups.append(i.id)
    # 3. 根据下层groups再挨个获取group下的projects
    for i in ndx_descendant_groups:
        descendantGroup = gl.groups.get(i)
        descendantProjects = descendantGroup.projects.list(all=True)
        for j in descendantProjects:
            ndxProjectIDs.append(j.id)

    # for pid in ndxProjectIDs:
    #   ndxProject_mbs = []
    #   ndxProject = gl.projects.get(pid)
    #   users = ndxProject.users.list()
    #   for u in users:
    #     tmp_dict = {}
    #     tmp_dict['projectname'] = ndxProject.name
    #     tmp_dict['id'] = u.id
    #     tmp_dict['username'] = u.username
    #     ndxProject_mbs.append(tmp_dict)
    #   ndx_project_members[pid] = ndxProject_mbs

    return ndxProjectIDs


def insertBugStatistics(ndx_project_members):
    mysqldb = db_utils.mysqldb()
    for k, v in ndx_project_members.items():
        for i in v:
            sql = getBugStatistics(k, i['projectname'], i["id"], i["username"])
            mysqldb.insertTable(sql)
    mysqldb.closeDB()


cur_month = datetime.datetime.now().strftime("%Y%m")
only_month = datetime.datetime.now().strftime("%m")
dt_createdAfter = datetime_range[only_month]['dt_createdAfter']
dt_createdBefore = datetime_range[only_month]['dt_createdBefore']


def getNDXPrjIssues(ndxProjectIDs):
    mysqldb = db_utils.mysqldb()

    # 查询上个月的数据
    # select iid from issueDetail where date_format(created_at, '%Y%m') = date_format(DATE_SUB(now(), INTERVAL 1 MONTH), '%Y%m');
    # 此处在更新前应删掉本月的数据: 先查询本月的数据然后再删除
    origin_rows = mysqldb.selectData(
        'select id from issueDetail where date_format(created_at, \'%Y%m\') = date_format(curdate(), \'%Y%m\');')
    rows = tuple(i[0] for i in origin_rows)
    sql = 'DELETE FROM {0} where id in {1};'.format('issueDetail', rows)
    mysqldb.deleteData(sql)
    for pj in ndxProjectIDs:
        ndxProject = gl.projects.get(pj)
        # for历史数据
        issues = ndxProject.issues.list(all=True, labels='kind/bug', created_after=dt_createdAfter,
                                        created_before=dt_createdBefore)
        for ii in issues:
            sql = 'insert into {0} values({1}, {2}, {3}, \'{4}\', \'{5}\', \'{6}\', {7}, \'{8}\', \'{9}\');'.format(
                "issueDetail", \
                ii.id, ii.iid, ii.project_id, ndxProject.name, ii.state, ii.created_at, ii.author['id'],
                ii.author['username'], ','.join(ii.labels))
            mysqldb.insertTable(sql)
    mysqldb.closeDB()


def generateIssueStatistic():
    mysqldb = db_utils.mysqldb()
    # for历史数据处理
    # sql = 'insert into bugStatistics (projectID, projectName, author, authorName, allIssues, byMonth) \
    #         select projectID, projectName, author_id, author_username, count(iid), date_format(DATE_SUB(now(), INTERVAL 1 MONTH), \'%Y%m\') \
    #         from issueDetail group by projectID, projectName, author_id, author_username;'
    # mysqldb.insertTable(sql)

    # 当月数据处理
    # select * from issueDetail where date_format(created_at, '%Y%m') = date_format(curdate(),'%Y%m') group by projectID,projectName, author_id, author_username;
    # 1. 此处在重新统计前应先删掉已统计数据
    origin_rows = mysqldb.selectData(
        'select projectID, author, byMonth from bugStatistics where byMonth = date_format(curdate(), \'%Y%m\');')
    for i in origin_rows:
        mysqldb.deleteData(
            'DELETE FROM {0} where projectID={1} and author={2} and byMonth={3};'.format('bugStatistics', i[0], i[1],
                                                                                         i[2]))
    # 2. 从issueDetail表中按照每个项目/每个人/每个月统计issue数量:
    # sql = 'insert into bugStatistics (projectID, projectName, author, authorName, allIssues, byMonth) \
    #         select projectID, projectName, author_id, author_username, count(iid), {0} from issueDetail \
    #         where date_format(created_at, \'%Y%m\') = date_format(curdate(), \'%Y%m\') group by projectID,projectName, author_id, author_username;'.format(cur_month)
    # 2. 统计issueDetail表
    sql = 'select projectID, projectName, author_id, author_username, count(iid) from issueDetail \
          where date_format(created_at, \'%Y%m\') = date_format(curdate(), \'%Y%m\') group by projectID,projectName, author_id, author_username;'
    origin_rows = mysqldb.selectData(sql)
    for i in origin_rows:
        mysqldb.insertTable('insert into bugStatistics (projectID, projectName, author, authorName, allIssues, byMonth) values\
                           ({0}, \'{1}\', {2}, \'{3}\', {4}, \'{5}\')'.format(i[0], i[1], i[2], i[3], i[4], cur_month))
    mysqldb.closeDB()


# for test
if __name__ == '__main__':
    ndxProjectIDs = getNDXProjectInfo()
    getNDXPrjIssues(ndxProjectIDs)
    generateIssueStatistic()
