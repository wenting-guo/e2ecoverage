import sys
import os
import datetime
from github import Github
from scripts import db_utils
from scripts import md_utils
from pymysql import NULL

sys.path.append('.')
sys.path.append('./scripts')
current_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(current_path)
prjJsFile = parent_path + '/case/projects.json'
cfgFile = parent_path + '/case/casepath.ini'


class GetGithubIssue:

    def __init__(self, github_project_names):
        self.github = Github(login_or_token="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")
        self.repo = self.github.get_repo(github_project_names)

    def get_expect_labels(self, expect_label_string):
        """
        get expect labels
        TODO: To be improved
        :return: labels list
        """
        labels = self.repo.get_labels()
        tmp_list = []
        for label in labels:
            if expect_label_string in label.name:
                tmp_list.append(label.name)
        return tmp_list

    def get_issue_average_fix_time(self, labels_list: list):
        """
        Get the average repair time of an issue
        TODO: To be improved
        :return: issue average fix time
        """
        now_time = datetime.datetime.now()
        bugs = 0
        open_bugs_created_total_time = datetime.timedelta()
        close_bugs_closed_total_time = datetime.timedelta()
        for label in labels_list:
            open_issues = self.repo.get_issues(state='open', labels=[label])
            bugs += open_issues.totalCount
            for iss in open_issues:
                created_at_time = iss.created_at + datetime.timedelta(hours=8)
                open_bugs_created_total_time += (now_time - created_at_time)

            close_issues = self.repo.get_issues(state='closed', labels=[label])
            for close_issue in close_issues:
                closed_time = close_issue.closed_at + datetime.timedelta(hours=8)
                created_time = close_issue.created_at + datetime.timedelta(hours=8)
                if (now_time - closed_time).days <= 30:
                    bugs += 1
                    close_bugs_closed_total_time = (closed_time - created_time) + close_bugs_closed_total_time
        if bugs != 0:
            average_fix_issue_time_per_month = (open_bugs_created_total_time + close_bugs_closed_total_time) / bugs
        else:
            average_fix_issue_time_per_month = datetime.timedelta(days=0)
        return average_fix_issue_time_per_month

    def get_uncategorized_issue_maximum_waiting_time(self):
        """
        Get uncategorized issue maximum waiting time
        TODO: To be improved
        :return: uncategorized issue maximum waiting time
        """
        now_time = datetime.datetime.now()
        uncategorized_issue = self.repo.get_issues(state='open', labels=[NULL])
        maximum_waiting_time_list = []
        if uncategorized_issue.totalCount == 0:
            earliest_time = datetime.timedelta(days=0)
            return earliest_time
        else:
            for issue in uncategorized_issue:
                created_at_time = issue.created_at + datetime.timedelta(hours=8)
                maximum_waiting_time_list.append((now_time - created_at_time).days)
        maximum_waiting_time_list_sort = sorted(maximum_waiting_time_list, reverse=True)
        return maximum_waiting_time_list_sort[0]

    def get_issue_average_comment_time(self, labels_list: list):
        """
        get issue average comment time
        :return:
        """
        now_time = datetime.datetime.now()
        open_issue_comment_total_time = datetime.timedelta()
        closed_issue_comment_total_time = datetime.timedelta()
        issues = 0
        for label in labels_list:
            # TODO: If the issue has more than one label, it will be counted more than once
            open_issues = self.repo.get_issues(state='open', labels=[label])
            issues += open_issues.totalCount
            for open_issue in open_issues:
                if open_issue.comments == 0:
                    created_at_time = open_issue.created_at + datetime.timedelta(hours=8)
                    open_issue_comment_total_time += (now_time - created_at_time)
                else:
                    comments = open_issue.get_comments()
                    first_comment_created_at_time = comments[0].created_at + datetime.timedelta(hours=8)
                    closed_issue_comment_total_time += (now_time - first_comment_created_at_time)

            # TODO: If the issue has more than one label, it will be counted more than once
            close_issues = self.repo.get_issues(state='closed', labels=[label])
            for close_issue in close_issues:
                create_time = close_issue.created_at
                # closed_time = close_issue.closed_at
                if (now_time - create_time + datetime.timedelta(hours=8)).days <= 30:
                    issues += 1
                    if close_issue.comments == 0:
                        closed_issue_comment_total_time += (now_time - create_time)
                    else:
                        comments = close_issue.get_comments()
                        first_comment_time = comments[0].created_at
                        closed_issue_comment_total_time += first_comment_time - create_time
        if issues != 0:
            average_comment_time = (open_issue_comment_total_time + closed_issue_comment_total_time) / issues
        else:
            average_comment_time = datetime.timedelta(days=0)
        return average_comment_time


def run_main():
    """
    Get the time of each statistic and generate badges
    TODO: To be improved
    :return:
    """
    mysqldb = db_utils.mysqldb()
    github_project_names = mysqldb.selectData('select projectName from githubProjects;')

    for project_names in github_project_names:
        print('>>>>>>>>>>>>>>', project_names[0], '<<<<<<<<<<<<<<<')

        # init
        ggi = GetGithubIssue(project_names[0])

        # Truncate the second half of the name and use it as the folder name.
        badges_storage_directory = project_names[0].split("/")[1]

        # Check if a directory exists under the badges directory, if not then create
        expect_path = parent_path + "/badges/" + badges_storage_directory
        if not os.path.exists(expect_path):
            os.mkdir(expect_path)

        # label Differentiation exists, treating different ones
        if "spiderpool" in project_names[0]:
            # Get only issue's, no pr's
            labels_list = ggi.get_expect_labels("issue/bug")
        else:
            labels_list = ggi.get_expect_labels('bug')
        # Average bug fix time
        issue_average_fix_time = ggi.get_issue_average_fix_time(labels_list)
        print("issue average fix time {}".format(issue_average_fix_time))

        svg_label_colours = {'30d': 'teal', '60d': 'green', '90d': 'yellow', '91d': 'red'}
        fix_time_svg_file = expect_path + '/average_fix_time_perMonth.svg'
        md_utils.make_Badge_string("Bug Average Fix Time",
                                   str(issue_average_fix_time.days) + 'd',
                                   svg_label_colours,
                                   fix_time_svg_file)

        # Maximum waiting time for unclassified issues
        uncategorized_issue_time = ggi.get_uncategorized_issue_maximum_waiting_time()
        print("uncategorized issue time {}".format(uncategorized_issue_time))
        earliest_issue_thresholds = {'7d': 'green', '30d': 'yellow', '31d': 'red'}
        earliest_issue_svg_file = expect_path + '/earliest_issue.svg'
        md_utils.make_Badge_string("Uncategorized Issue Time",
                                   str(uncategorized_issue_time.days) + 'd',
                                   earliest_issue_thresholds, earliest_issue_svg_file)

        # Statistics issue comment Average time
        if "spiderpool" in project_names[0]:
            labels_list = ["issue/bug", "issue/ci-fail"]
        average_comment_time = ggi.get_issue_average_comment_time(labels_list)
        print("average comment time {}".format(average_comment_time))
        average_comment_time_thresholds = {'1d': 'teal', '7d': 'green', '30d': 'yellow', '31d': 'red'}
        average_comment_time_svg_file = expect_path + '/average_replyTime.svg'
        md_utils.make_Badge_string("Average Comment Time",
                                   str(average_comment_time.days) + 'd',
                                   average_comment_time_thresholds,
                                   average_comment_time_svg_file)

        print(">>>>>>>>>> badges Storage directory: {} ".format(expect_path) + '<<<<<<<<<<')


if __name__ == '__main__':
    # GetGithubIssue("spidernet-io/spiderpool").get_issue_average_comment_time(["issue/bug"])
    run_main()
