import datetime
import jira
import db_utils


def login():
    client = jira.JIRA(server="https://jira.daocloud.io", basic_auth=('eazybirobot', 'Gai9gai@h\ie*h5'))
    return client


def search_jql(jira_client, jql):
    issues_in_proj = jira_client.search_issues(jql, maxResults=-1)
    return issues_in_proj


def get_date():
    current_date = datetime.date.today()
    first_day_of_month = datetime.date(current_date.year, current_date.month, 1)
    next_month = first_day_of_month.replace(day=28) + datetime.timedelta(days=4)
    last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
    return first_day_of_month, last_day_of_month, first_day_of_month.strftime("%Y%m")


def initial_table():
    mysqldb = db_utils.mysqldb()
    print('>>>>> show database:', mysqldb.selectData("show databases;"))
    mysqldb.createTable("jiraStatistics", db_utils.jiraStatisticsTableSql)
    print('>>>>> show the created tables:', mysqldb.selectData("show tables;"))


def update_mysql(projectID, reporter, defects, enhancements, month):
    mysqldb = db_utils.mysqldb()
    sql = 'REPLACE INTO {0}(projectID, reporter, defects, enhancements, byMonth) ' \
          'VALUES(\'{1}\', \'{2}\', \'{3}\', \'{4}\', \'{5}\');'
    insert_sql = sql.format("jiraStatistics", projectID, reporter, defects, enhancements, month)
    # print(insert_sql)
    mysqldb.insertTable(insert_sql)


def count_issues():
    jira_client = login()
    projectID = "DEC"
    issue_ops = ["in", "not in"]
    reporters = ["xinjun.jiang", "jinye.shi", "lihan.zhou", "liqing.wu", "wen.rui"]
    first_day_of_month, last_day_of_month, month = get_date()
    jql = "project = {0} AND issuetype {1} (故障) AND issuetype not in (子任务,测试)AND created >= {2} " \
          "AND created <= {3} AND reporter in ({4})"
    for reporter in reporters:
        defects = issues = 0
        for issue_op in issue_ops:
            query = jql.format(projectID, issue_op, first_day_of_month, last_day_of_month, reporter)
            # print(query)
            issues = search_jql(jira_client, query)
            # print(len(issues))
            if issue_op == "in":
                defects = len(issues)
            elif issue_op == "not in":
                issues = len(issues)
        update_mysql(projectID, reporter, defects, issues, month)


if __name__ == '__main__':
    # optional if table not existed
    # initial_table()
    count_issues()
