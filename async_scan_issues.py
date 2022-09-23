import os
import time
import subprocess
from multiprocessing import Process

from loguru import logger
import asyncio
from git.repo import Repo
from gitlab import GitlabError, GitlabGetError

from utils.scan_issues import scan_issue
from scripts import md_utils

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
    tasks = []
    for project in iniProjects:
        try:
            logger.info(f"开始运行：{project}")
            project_id = cf.get('ProjectID', project)
            tasks.append(asyncio.ensure_future(scan_issue(project_id)))
        except (GitlabError, GitlabGetError) as e:
            logger.error(f"gitlab err: {e}")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
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
    logger.info(f"代码耗时：{time.time() - start_time}")


if __name__ == '__main__':
    p = Process(target=main)
    p.daemon = True
    p.start()
    p.join()
