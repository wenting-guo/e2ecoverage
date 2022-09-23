import sys
import os
import datetime
from concurrent.futures import ThreadPoolExecutor

import asyncio
import gitlab
from loguru import logger

from scripts import md_utils
from scripts.web_utils import getEarliestNote

sys.path.append('./utils')
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


async def scan_issue(project_id):
    """
    :param project_id: 项目 id
    :return:dict
    """
    now_time = datetime.datetime.now()
    project_info = gl.projects.get(project_id)

    # 当月 issue(kind/bug) 平均修复时间
    # 获取所有 open 的 bugs 并合计其创建总时长
    open_bugs = project_info.issues.list(all=True, labels='kind/bug', state='opened')
    open_bugs_created_at_total_time = datetime.timedelta()
    for bug in open_bugs:
        created_at_time_format = datetime.datetime.strptime(bug.created_at, UTC_FORMAT)
        open_bugs_created_at_total_time = (now_time - created_at_time_format) + open_bugs_created_at_total_time

    # 获取所有截止当天为止30天以内close的bugs并合计其花费时长
    close_bugs = project_info.issues.list(all=True, labels='kind/bug', state='closed')
    close_bugs_closed_at_total_time = datetime.timedelta()
    for bug in close_bugs:
        closed_at_time_format = datetime.datetime.strptime(bug.closed_at, UTC_FORMAT)
        created_at_time_format = datetime.datetime.strptime(bug.created_at, UTC_FORMAT)
        if (now_time - closed_at_time_format).days <= 30:
            close_bugs_closed_at_total_time = (
                                                      closed_at_time_format - created_at_time_format) + \
                                              close_bugs_closed_at_total_time
    if len(open_bugs) == 0 and len(close_bugs) == 0:
        average_fix_time_per_month = datetime.timedelta(days=0)
    else:
        average_fix_time_per_month = (open_bugs_created_at_total_time + close_bugs_closed_at_total_time) / (
                len(open_bugs) + len(close_bugs))

    average_fix_time_per_month_thresholds = {'30d': 'teal',
                                             '60d': 'green',
                                             '90d': 'yellow',
                                             '91d': 'red'}

    # 检查 badges 目录下是否有 project name 目录，如果没有则创建
    if not os.path.exists(parent_path + "/badges/" + project_info.name):
        os.mkdir(parent_path + "/badges/" + project_info.name)
    average_fix_time_per_month_svg_file = parent_path + "/badges/" + project_info.name + '/average_fix_time_perMonth.svg'
    md_utils.make_Badge_string("Bug Average Fix",
                               str(average_fix_time_per_month.days) + 'd',
                               average_fix_time_per_month_thresholds,
                               average_fix_time_per_month_svg_file)
    # 未分类issue最长等待时间
    no_kind_issue = project_info.issues.list(all=True, labels=[None], state='opened')
    if len(no_kind_issue) == 0:
        earliest_time = datetime.timedelta(days=0)
    else:
        earliest_time = now_time - datetime.datetime.strptime(no_kind_issue[0].created_at, UTC_FORMAT)
        for i in no_kind_issue:
            created_at_time_format = datetime.datetime.strptime(i.created_at, UTC_FORMAT)
            if now_time - created_at_time_format > earliest_time:
                earliest_time = now_time - datetime.datetime.strptime(i.created_at, UTC_FORMAT)
    earliest_issue_thresholds = {'7d': 'green',
                                 '30d': 'yellow',
                                 '31d': 'red'}
    earliest_issue_svg_file = parent_path + "/badges/" + project_info.name + '/earliest_issue.svg'
    md_utils.make_Badge_string("Untriage Issue", str(earliest_time.days) + 'd',
                               earliest_issue_thresholds, earliest_issue_svg_file)
    # 当月 issue 平均回复时间
    open_issue_comment_reply_total_time = datetime.timedelta()
    close_issue_comment_reply_total_time = datetime.timedelta()

    # 全部open的issue总回复时间
    open_issues = project_info.issues.list(all=True, state='opened')

    open_issues_pools = ThreadPoolExecutor(10)  # 10 个线程池
    open_issues_loop = asyncio.get_event_loop()
    open_issues_tasks = []
    issue_create_time_list = []
    if len(open_issues) != 0:
        for oi in open_issues:
            issue_create_time = datetime.datetime.strptime(oi.created_at, UTC_FORMAT)
            issue_create_time_list.append(issue_create_time)
            # 找到 open issue最早的 comment
            t = open_issues_loop.run_in_executor(open_issues_pools, getEarliestNote, project_info, oi)
            open_issues_tasks.append(t)  # 添加到 task
        res = await asyncio.gather(*open_issues_tasks)

        for index, i in enumerate(res):
            issue_comment_reply_time = i - issue_create_time_list[index]
            open_issue_comment_reply_total_time += issue_comment_reply_time

    # 30天内的close issue总回复时间
    close_issues = project_info.issues.list(all=True, state='closed')
    now_time = datetime.datetime.now()
    close_issue_within30 = []
    close_issue_within30_pools = ThreadPoolExecutor(10)  # 10 个线程池
    close_issue_within30_loop = asyncio.get_event_loop()
    close_issue_within30_tasks = []

    issue_create_time_list = []

    if len(close_issues) != 0:
        for i in close_issues:
            # 找到30天以内关闭的issue
            closed_at_time_format = datetime.datetime.strptime(i.closed_at, UTC_FORMAT)
            if (now_time - closed_at_time_format).days <= 30:
                close_issue_within30.append(i)
        if len(close_issue_within30) != 0:
            for ci in close_issue_within30:
                issue_create_time = datetime.datetime.strptime(ci.created_at, UTC_FORMAT)
                # 找到close issue最早的comment
                issue_create_time_list.append(issue_create_time)
                t = close_issue_within30_loop.run_in_executor(close_issue_within30_pools, getEarliestNote, project_info,
                                                              ci)
                close_issue_within30_tasks.append(t)
            # try:
            res = await asyncio.gather(*close_issue_within30_tasks)
            for index, i in enumerate(res):
                issue_comment_reply_time = i - issue_create_time_list[index]
                # 计算30天内的close issue的最早comment回复时间的总和
                close_issue_comment_reply_total_time += issue_comment_reply_time

    if len(open_issues) + len(close_issues) != 0:
        average_reply_time = (open_issue_comment_reply_total_time + close_issue_comment_reply_total_time) / (
                len(open_issues) + len(close_issues))
    else:
        average_reply_time = datetime.timedelta(days=0)
    average_reply_time_thresholds = {'1d': 'teal',
                                     '7d': 'green',
                                     '30d': 'yellow',
                                     '31d': 'red'}
    average_reply_time_svg_file = parent_path + "/badges/" + project_info.name + '/average_reply_time.svg'
    md_utils.make_Badge_string("Reply Issue", str(average_reply_time.days) + 'd',
                               average_reply_time_thresholds, average_reply_time_svg_file)
    print_msg = f"\n======================= {project_info.name} ==================="
    print_msg += (
        f"\n"
        f"open_bugs: {len(open_bugs)}\n"
        f"close_bugs: {len(close_bugs)}\n"
        f"close_bugs_closed_at_total_time: {close_bugs_closed_at_total_time}\n"
        f"open_bugs_created_at_total_time: {open_bugs_created_at_total_time}\n"
        f"average_fix_time_perMonth: {average_fix_time_per_month}\n"
        f"earliest_time: {earliest_time}\n"
        f"openIssue_comment_replyTotalTime: {open_issue_comment_reply_total_time}\n"
        f"close_issue_comment_reply_total_time: {close_issue_comment_reply_total_time}\n"
        f"open_issues: {len(open_issues)}\n"
        f"close_issues: {len(close_issues)}\n"
        f"average_reply_time: {average_reply_time.days}\n"
        f"======================= {project_info.name} end ================\n"

    )
    logger.info(print_msg)
    # return "Issue 徽章已生成, 请查看本项目仓库中 badges 目录"
    return {
        "open_bugs": len(open_bugs),
        "close_bugs": len(close_bugs),
        "close_bugs_closed_at_totalTime": close_bugs_closed_at_total_time,
        "open_bugs_created_at_totalTime": open_bugs_created_at_total_time,
        "average_fix_time_perMonth": average_fix_time_per_month,
        "earliest_time": earliest_time,
        "openIssue_comment_replyTotalTime": open_issue_comment_reply_total_time,
        "close_issue_comment_reply_total_time": close_issue_comment_reply_total_time,
        "len(open_issues)": len(open_issues),
        "len(close_issues)": len(close_issues),
        "average_reply_time": average_reply_time.days
    }
