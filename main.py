# -*- coding: utf-8 -*- 
import anybadge
import sys
from flask import Flask
from flask import send_file
import subprocess
import os
import scripts.web_utils as web_utils
import scripts.md_utils as md_utils

app=Flask(__name__)

# 功能描述：测试接口
@app.route('/')
def index():
    os.system("git status")
    return 'e2e test - Hello World'

# 功能描述：按照关键字返回查询到的gitlab项目id, name
@app.route('/projects/<keyword>', methods=['GET'])
def projects(keyword):
    return web_utils.getAllPrj(keyword)

# 功能描述：返回当前service里已注册的所有gitlab项目
@app.route('/registeredProjects', methods=['GET'])
def getRegisteredPrj():
    return web_utils.getRegisteredPrj()

# 功能描述：register project based on id to write project id into projects.json
@app.route('/project/<projectId>', methods=['GET'])
def registerPrj(projectId):
    projectRet = web_utils.registerPrj(projectId)
    return projectRet

# 功能描述：手动调此接口执行docs/test测试用例扫描及统计完成率
@app.route('/project/<projectId>', methods=['POST'])
def scanPrj(projectId):
    return web_utils.scanPrj(projectId)

# 功能描述：获取项目issue并生成issue badges
@app.route('/issue/<projectId>', methods=['GET'])
def scanIssue(projectId):
    return web_utils.scanIssue(projectId)


if __name__=='__main__':
    if "web" == sys.argv[1]:
        app.config['JSON_AS_ASCII'] = False
        app.run(host='0.0.0.0',debug=True,port=8000)
    else: # local svg file mode
        project = sys.argv[1]
        md_utils.generateBadges(project, "")
