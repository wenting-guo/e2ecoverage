# -*- coding: utf-8 -*- 
import os
import sys
import time
import subprocess
from multiprocessing import Process

sys.path.append('.')
sys.path.append('./scripts')
from git.repo import Repo
from gitlab import GitlabError, GitlabGetError


import scripts.web_utils as web_utils
import scripts.md_utils as md_utils
import scripts.github_issue as github_issue

current_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(current_path)


def main():
    start_time = time.time()
    repo = Repo(current_path)

    # 读取case/casepath.ini里面的所有项目标签
    os.system('git config --global user.email "fujia.liu@daocloud.io"')
    os.system('git config --global user.name "fujia.liu"')
    for i in range(5):  # 拉取最新的代码
        try:
            os.system("git fetch --all")
            os.system("git reset --hard origin/main")
            break
        except Exception as e:
            print(f"拉取代码错误:{e}")
            continue
    cf = md_utils.getCaseFile()
    iniProjects = cf.options('ProjectID')
    print("iniProjects: ", iniProjects)
    for i in iniProjects:
        try:
            print('>>>>>', i)
            projID = cf.get('ProjectID', i)
            web_utils.scanIssue(projID)
        except GitlabError as e:
            print("gitlab err: {0}".format(e))

    try:
        print('Generate or update github issue badges')
        github_issue.run_main()
    except Exception as e:
        print("github err: {0}".format(e))

    os.system(f"cd badges")
    print("current_path: ", current_path)
    os.system(f"ls {current_path}/badges/")
    os.system("git status")
    os.system("git add .")
    repo.index.commit(f'cronIssueScan {start_time}')
    print("start push。。。")
    for i in range(5):
        try:
            res = subprocess.Popen("git push", shell=True, stdout=subprocess.PIPE)
            print(res.stdout.read())
            res.stdout.close()
            return
        except Exception as e:
            print(f"push错误：{e}")
            time.sleep(2)
    print('scan issue done...')


if __name__ == '__main__':
    p = Process(target=main)
    p.daemon = True
    p.start()
    p.join()
