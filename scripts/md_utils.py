import configparser
import os
import re
import sys
import anybadge

sys.path.append('.')
sys.path.append('./scripts')
from scripts.getgithub import getgithub
from scripts import getgitlab
from scripts.getgitlab import getgitlab
import shutil
from git.repo import Repo

current_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(current_path)

def mdtable2array(md_file):
    #https://stackoverflow.com/questions/66185838/python-convert-markdown-table-to-json-with
    with open(md_file) as f:
        md_table = f.read()
        result = []
        header = ""
        header_line = ""
        segment_line = ""
        for n, line in enumerate(md_table.split('\n')):
            data = {}
            if len(line) <=1 or line.find('|') == -1:
                continue;
            if len(segment_line) == 0 and re.match(".*\|-*\|.*",line) :
                segment_line = line
                continue;
            if len(header) == 0:
                header_line = line
                header = [t.strip() for t in line.split('|')[1:-1]]
                continue;
            values = [t.strip() for t in line.split('|')[1:-1]]
            for col, value in zip(header, values):
                data[col] = value
            result.append(data)
    return header_line, segment_line, result

def getrootpath():
    global rootpath
    #rootpath = os.getcwd()[0:os.getcwd().find("e2ecoverage")]+ "e2ecoverage"
    current_path = os.path.dirname(os.path.realpath(__file__))
    rootpath = os.path.dirname(current_path)
    sys.path.append(str(rootpath))
    return rootpath

def getCaseFile():
    rootpath = getrootpath()
    # 读取测试用例路径配置文件
    cf = configparser.ConfigParser()
    configpath = rootpath + "/case/casepath.ini"
    cf.read(configpath)
    return cf

def getcasepath(cf, section, option):
    cf = getCaseFile()
    casepath = rootpath + cf.get(str(section), str(option))
    return str(casepath)

def Create_folder(filename):
    filename = filename.strip()
    filename = filename.rstrip("\\")
    isExists = os.path.exists(filename)
    if not isExists:
        os.makedirs(filename)

def downloadcase(project):
    # 读取配置文件
    cf = getCaseFile()
    list = cf.items(project)

    # 创建case本地文件夹
    localpath = rootpath + "/case/" + project
    Create_folder(localpath)

    # 获取gitlab项目的ProjectID
    projectid = cf.get('ProjectID', project)

    # 通过isdigit()来判断projectid是否为数字，是数字默认为gitlab项目
    if projectid.isdigit() == True:
        git = getgitlab()
        masterbranch = git.checkMasterBranch(projectid)
        for modular, gitpath in list:
            print("开始下载:" + modular)
            filename = localpath + "/" + modular + ".md"
            git.gitDownload(projectid, gitpath, filename, masterbranch)
    else:
        for modular, gitpath in list:
            print("开始下载:" + modular)
            filename = localpath + "/" + modular + ".md"
            getgithub().githubDownload(projectid, gitpath, filename)

    # TODO 增加是否完成check
    return list


def parseReadmeFile(readmeFile):
    with open(readmeFile, 'r') as readmeF:
        readmeLines= readmeF.readlines()
    caseObj = {}
    for i in readmeLines:
        if i.startswith("###") and i.__contains__("_testcase.md"):
            caseName = i.split("./")[1].split("_")[0].strip("\r\n")
            caseObj[caseName] = 'docs/test/' + i.split("./")[1].split(")")[0].strip("\r\n")
    return caseObj


def caculate(md_file):
    a, b, result = mdtable2array(md_file)
    complete = 0
    if "是否完成" in a:
        isfinishkey = "是否完成"
    else:
        isfinishkey = "Status"
    for r in result:
        if r[isfinishkey].find("[x]") != -1:
            complete += 1
    casecount = len(result) - 1
    percentage = round(complete*100.0/casecount, 2)
    print("DEBUG complete", complete)
    print("DEBUG casecount", casecount)
    print("DEBUG percentage", percentage)
    return complete, casecount, percentage

def make_Badge(describe, percentage, thresholds, svgpath):
    badge = anybadge.Badge(str(describe), percentage, thresholds=thresholds)
    badge.write_badge(svgpath, overwrite=True)

def make_Badge_string(describe, percentage, thresholds, svgpath):
    badge = anybadge.Badge(label=str(describe), value=str(percentage), thresholds=thresholds, semver=True)
    badge.write_badge(svgpath, overwrite=True)

def returncolor(percentage):
    if percentage<=float(30):
        return "red"
    if percentage >float(30) and percentage<=float(50):
        return "orange"
    if percentage >float(50) and percentage<=float(70):
        return "yellow"
    else:
        return "green"

def generateBadges(prjName, repo_path):
    if repo_path == "":
        repo_path = parent_path
    repo = Repo(repo_path)
    repo.remote().pull #拉取最新的代码

    projectlist = downloadcase(prjName)
    badgepath = parent_path + "/badges/" + prjName
    Create_folder(badgepath)
    # 统计总完成数、总用例数
    completeCount = 0
    caseCount = 0
    # svg颜色
    thresholds = {1: 'red',
                2: 'green'}
    coverage_thresholds = {30: 'red',
                         50: 'orange',
                         70: 'yellow',
                         85: 'green'}

    # markdown case项目目录
    castpath = parent_path + "/case/" + prjName
    for modular, gitpath in projectlist:
        # 拼装 markdowncase 文件
        mdpath = castpath + "/" + modular +".md"
        print(mdpath)
        # 计算
        complete, mdpathcasecount, percentage = caculate(mdpath)
        # 汇总整体用例数据
        completeCount = completeCount + complete
        caseCount = caseCount + mdpathcasecount
        # 生成百分比徽章
        make_Badge(modular + " Coverage%", percentage, coverage_thresholds, badgepath + "/" + modular + 'Coverage.svg')
        # 生成完成数/case总数徽章
        fraction = str(complete) + "/" + str(mdpathcasecount)
        make_Badge_string(modular + " Coverage", fraction, {fraction: returncolor(percentage)}, badgepath + "/" + modular + 'Coverage2.svg')

        # ------- 可直接使用整体数据徽章（后续可删除）-------
        # 完成数
        completesvg = badgepath + "/" + modular + 'Complete.svg'
        make_Badge("Complete", complete, thresholds, completesvg)
        # 生成总数
        countsvg = badgepath + "/" + modular + 'Count.svg'
        make_Badge("CaseCount", mdpathcasecount, thresholds, countsvg)
    # -----------------------------------------------
    # 统计总体用例覆盖率
    # ------- 可直接使用整体数据徽章（后续可删除）-------
    completeCount_svg = badgepath + "/" + prjName + 'Complete.svg'
    make_Badge("Complete", completeCount, thresholds, completeCount_svg)
    caseCount_svg = badgepath + "/" + prjName + 'Count.svg'
    make_Badge("CaseCount", caseCount, thresholds, caseCount_svg)
    # -----------------------------------------------
    # 百分比
    percentageCount = round(completeCount * 100.0 / caseCount, 2)
    percentageCount_svg = badgepath + "/" + prjName + 'Coverage.svg'
    make_Badge("E2E Test Coverage%", percentageCount, coverage_thresholds, percentageCount_svg)
    # 完成数/case总数
    print("完成数/case总数: ", completeCount, caseCount)
    CaseCount = str(completeCount) + "/" + str(caseCount)
    CaseCount_svg = badgepath + "/" + prjName + 'Coverage2.svg'
    make_Badge_string("E2E Test Coverage", CaseCount, {CaseCount: returncolor(percentageCount)}, CaseCount_svg)

    shutil.rmtree(castpath)
    repo.index.add(parent_path + "/badges/" )
    repo.index.commit('generateBadges function commit updated casepath.ini or badges')
    repo.remote().push(repo.active_branch)

if __name__ == '__main__':
    caculate("/Users/xujiewei/dev/kpanda/docs/test/performance_testcase.md")