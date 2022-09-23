# -*- coding: utf-8 -*- 

import pymysql

# 创建issueDetail表
# create table 创建issueDetail表(
    #     id int not null, #issue的全局id
    #     iid int not null, #issue在项目里的id
    #     projectID int not null,
    #     projectName char(100) not null,
    #     state char(20) not null,
    #     created_at char(200) not null,
    #     author_id int not null, # 此处保存员工id
    #     author_username char(20) not null, # 此处保存员工username
    #     labels char(200) DEFAULT None
    # );
# insert new issue之前先判断是否存在同样iid/projectName/author_id/labels;如果labels不一样则：
# 1. 某个issue原来有kind/bug label但是被取消了换了别的label此时则删除此issue数据
# 2. 某个issue原来有kind/bug label之外又新增了别的label此时则update
issueTableSql = 'create table issueDetail (id int not null, iid int not null, projectID int not null, projectName char(100) not null, \
                state char(20) not null, created_at char(200) not null, author_id int not null,\
                author_username char(20) not null, labels char(200) DEFAULT null, PRIMARY KEY(iid, projectID, author_id)) default charset=utf8;'

# 考虑到github的issue数据跟gitlab不同，所以github的issue单独建表
# author_username: 本公司内域名,可以为空（有的issue是社区人员提的）
# github_username: github username
githubIssueTableSql = 'create table githubIssueDetail (number int not null, projectName char(100) not null, \
                state char(20) not null, created_at char(200) not null, github_username char(50) not null,\
                author_username char(20), labels char(200) DEFAULT null, PRIMARY KEY(number, projectName, github_username)) default charset=utf8;'

#创建bugStatistics表
# create table bugStatistics(
#     projectID int  not null, # project id
#     projectName char(50) not null, # project name
#     author int not null # 备用
#     authorName char(20) not null # 此处保存员工name；通过id查询员工表获取username
#     allIssues int DEFAULT 0,
#     byMonth char(20) not null # 存储当前这条数据是哪个月份获取到的，比如202205
#     PRIMARY KEY(projectID, author, byMonth)  # projectID, author, authorName这3个字段是主键，不能重复
# )
bugStatisticsTableSql = 'create table bugStatistics (projectID int not null, projectName char(50) not null, author int not null, \
                        authorName char(20) not null, allIssues int DEFAULT 0, byMonth char(20) not null, \
                        PRIMARY KEY(projectID, author, byMonth)) default charset=utf8;'

githubBugStatisticsTableSql = 'create table githubBugStatistics (projectName char(50) not null, author_username char(20), \
                        github_username char(50) not null, allIssues int DEFAULT 0, byMonth char(20) not null, \
                        PRIMARY KEY(projectName, github_username, byMonth)) default charset=utf8;'

# Create jiraStatistics table
# create table jiraStatistics(
#     projectID char(20)  not null, # project id
#     reporter char(30) not null # 此处保存员工name；通过id查询员工表获取username
#     defects int DEFAULT 0,
#     enhancements int DEFAULT 0,
#     byMonth char(20) not null # 存储当前这条数据是哪个月份获取到的，比如202205
#     PRIMARY KEY(projectID, author, byMonth)  # projectID, reporter, authorName这3个字段是主键，不能重复
# )
jiraStatisticsTableSql = 'create table jiraStatistics (projectID char(20) not null, reporter char(30) not null, \
                        defects int DEFAULT 0, enhancements int DEFAULT 0, byMonth char(20) not null, \
                        PRIMARY KEY(projectID, reporter, byMonth)) default charset=utf8;'

# 针对github projects创建project表,用于保存需要同步issue的project name
# create table githubProjects(
#     projectName char(50) not null # project name； such as: clusterpedia-io/clusterpedia
# )
githubProjectsSql = 'create table githubProjects(projectName char(50) not null) default charset=utf8;'
# insert into githubProjects (projectName) values('hwameistor/local-storage'), ('hwameistor/local-disk-manager'), ('spidernet-io/spiderpool'),
#                                               ('clusterpedia-io/clusterpedia'), ('merbridge/merbridge'), ('klts-io/kubernetes-lts');

# github member mapping
# create table githubMember(
#     author_username char(20) not null, # github username
#     github_username char(50) not null #与之对应的公司内部域名
# )

class mysqldb:
    def __init__(self):
        self.mysqldb = pymysql.connect(
            host ="10.6.127.6",
            port = 3306,
            user = "root",
            password = "root",
            database =  "issueTest",
        )
        self.mycursor = self.mysqldb.cursor()

    def createDB(self, dbName):
        sql = "create database {0}".format(dbName)
        try:
            self.mycursor.execute(sql)
        except Exception as e:
             print("create db {0} fail: {1}".format(dbName, e))
    
    def closeDB(self):
        self.mycursor.close()
        self.mysqldb.close()

    def createTable(self, tableName, sqlCmd):
        try:
            self.mycursor.execute("DROP TABLE IF EXISTS {0}".format(tableName))
            print(sqlCmd)
            self.mycursor.execute(sqlCmd)
            print("create table {0} success".format(tableName))
        except Exception as e:
            print("create table {0} fail: {1}".format(tableName, e))

    def insertTable(self, sql):
        try:
            self.mycursor.execute(sql)
            self.mysqldb.commit()
        except Exception as e:
            print("{0} fail: {1}".format(sql, e))
            self.mysqldb.rollback()

    def selectData(self, selectSql):
        try:
            self.mycursor.execute(selectSql)
            # 获取结果集1
            # for i in range(self.mycursor.rowcount):
            #     result = self.mycursor.fetchone()
            #     print(result)
            # 获取结果集2
            rows = self.mycursor.fetchall()
            return rows
        except Exception as e:
            print("select sql {0} fail: {1}".format(selectSql, e))

    def deleteData(self, deleteSql):
        try:
            self.mycursor.execute(deleteSql)
            self.mysqldb.commit()
        except Exception as e:
            print("{0} fail: {1}".format(deleteSql, e))
            self.mysqldb.rollback()


def initialDB():
    mysqldbObj = mysqldb()
    print('>>>>> show the initial database:', mysqldbObj.selectData("show databases;"))
    ### 初始化database/tables
    # 1. create DB
    print('>>>>> create new database:')
    mysqldbObj.createDB("issueTest")
    print('>>>>> show the created database:', mysqldbObj.selectData("show databases;"))
    # 2. create table: 
    mysqldbObj.createTable("issueDetail", issueTableSql)
    mysqldbObj.createTable("bugStatistics", bugStatisticsTableSql)
    mysqldb.createTable("jiraStatistics", jiraStatisticsTableSql)
    # 3. 由web_utils.insertBugStatistics()完成拉取截止202205月份的issue统计数据（包括所有历史issue)
    mysqldbObj.closeDB()


#for test
if __name__=='__main__':
    initialDB()





