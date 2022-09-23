# python-gitlab
import gitlab


class getgitlab:
    # 初始化
    def __init__(self):
        # 服务器地址
        self.url = 'https://gitlab.daocloud.cn/'
        # 前面生成的Access Token
        self.accessToken = 'VC-_rYvd5pqvRdBk496u'

    # 登录
    def login(self):
        gl = gitlab.Gitlab(self.url, self.accessToken)
        return gl

    # 获得项目：projectID的格式随意，反正我就写了个数字进去
    def getProject(self, projectID):
        gl = self.login()
        projects = gl.projects.get(projectID)
        return projects

    def checkMasterBranch(self, projectID):
        projects = self.getProject(projectID)
        # 判断主分支为master还是main
        # masterbranch = "master"
        # if len(projects.branches.list(search=masterbranch)) == 0 :
        #     masterbranch = "main"
        return projects.default_branch

    # 获得project下单个文件
    def gitDownload(self, projectID, gitfilepath, localpath, masterbranch):
        projects = self.getProject(projectID)
        # 获得文件
        f = projects.files.get(file_path=gitfilepath, ref=masterbranch)
        # 第一次decode获得bytes格式的内容
        content = f.decode()
        # 第二次decode获得str
        # content = content.decode()
        # 存到本地
        with open(localpath, 'wb') as code:
            code.write(content)


# # 测试
# git = getgitlab()
# git.getContent(796, "docs/test/cluster_testcase.md", "/Users/xujiewei/dev/e2ecoverage/case/kpanda/cluster.md")
# for i in git.getProject(796).branches:
#     print(i)

# print(git.getProject(796).branches.list(page=0, per_page=200,as_list=True))
# print(len(git.getProject(796).branches.list(search='master')))
# print(git.getProject(796).branches.get('master1'))


