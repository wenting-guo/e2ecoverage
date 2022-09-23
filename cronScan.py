# -*- coding: utf-8 -*- 
import os
import sys
import time

from git.repo import Repo
import subprocess
from multiprocessing import Process

sys.path.append('.')
sys.path.append('./scripts')
import scripts.md_utils as md_utils
from gitlab import GitlabError, GitlabGetError

current_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(current_path)

if __name__ == '__main__':
    start_time = time.time()
    repo = Repo(current_path)
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
        if '-ui' in i or '-anakin' in i:
            print(i, " is skipped.")
            continue
        else:
            if len(cf.options(i)) != 0:
                print(i, " is skipped.")
                try:
                    md_utils.generateBadges(i, current_path)
                except GitlabError as e:
                    print("gitlab err: {0}".format(e))
    os.system(f"cd badges")
    print("current_path: ", current_path)
    os.system(f"ls {current_path}/badges/")
    os.system("git status")
    os.system("git add .")
    repo.index.commit(f'cronScan {start_time}')
    print("start push。。。")
    for i in range(5):
        try:
            res = subprocess.Popen("git push", shell=True, stdout=subprocess.PIPE)
            print(res.stdout.read())
            res.stdout.close()
            break
        except Exception as e:
            print(f"push错误：{e}")
            time.sleep(2)
    print('scan issue done...')
