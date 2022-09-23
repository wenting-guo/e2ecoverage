# -*- coding: utf-8 -*- 
import os
import sys

sys.path.append('.')
sys.path.append('./scripts')
import scripts.web_utils as web_utils
import scripts.getgithub as getgithub

if __name__ == '__main__':
    # for gitlab projects
    ndxProjectIDs = web_utils.getNDXProjectInfo()
    web_utils.getNDXPrjIssues(ndxProjectIDs)
    web_utils.generateIssueStatistic()

    # for github projects
    getgithub.getGithubIssues()
    getgithub.generateGithubIssueStatistic()
