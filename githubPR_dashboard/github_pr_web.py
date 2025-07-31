import sqlite3,os, sys, threading, schedule, time, datetime, re, queue, requests
from flask import Flask, render_template, jsonify, request
from github import Github
from github import Auth
sys.path.append(os.path.join(os.path.dirname(__file__)+'\..\core'))
from github_instance import GithubInstance
from config_info import ConfigInfo
from logging_config import logger
from info_from_url import InfoFromUrl
from sql_command import sql_command

DATABASE_FILE = os.path.join(os.path.dirname(__file__)+'\database\github_pulls.db')
conf=ConfigInfo(dashboard_conf='Github_Dashboard_Config')
PORT = int(conf.get_port())
ACTIVE_PERIOD = int(conf.get_pull_requests_active_period())
GH_TK = os.environ.get('GITHUB_TOKEN')

webhook_update_q = queue.Queue()

class PRDatabase:                                                  #Class PRDatabase
    def __init__(self, db_path):                                    #Constructor for Class
        self.db_path = db_path
		
    def get_connection(self):                                         # Connecting with the Database
        return sqlite3.connect(self.db_path)

    def check_review_status(self, pr_id, sub_pr_table):                               # Function to check PR review status button
        conn = self.get_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM {sub_pr_table} 
            WHERE (review_status != 'APPROVED' OR review_status IS NULL) 
            AND mpr_num = ?
        """
        cursor.execute(query, (pr_id,))
        result = cursor.fetchall()
        conn.close()
        return bool(result)

    def check_merge_conflict(self, pr_id, meta_pr_table, sub_pr_table):                             # Function to check PR merge conflict button
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor2 = conn.cursor()

        query1 = f"SELECT * FROM {meta_pr_table} WHERE merge_conflict = 1 AND mpr_num = ?"
        query2 = f"SELECT * FROM {sub_pr_table} WHERE merge_conflict = 1 AND mpr_num = ?"

        cursor.execute(query1, (pr_id,))
        cursor2.execute(query2, (pr_id,))

        result1 = cursor.fetchone()
        result2 = cursor2.fetchone()

        conn.close()
        return (result1 is not None or result2 is not None)

    def check_pr_status(self, pr_id,meta_pr_table, sub_pr_table):                               # Function to check PR status button(Draft/Open)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor2 = conn.cursor()

        query1 = f"SELECT * FROM {meta_pr_table} WHERE mpr_status = 'draft' AND mpr_num = ?"
        query2 = f"SELECT * FROM {sub_pr_table} WHERE spr_status = 'draft' AND mpr_num = ?"

        cursor.execute(query1, (pr_id,))
        cursor2.execute(query2, (pr_id,))

        result1 = cursor.fetchone()
        result2 = cursor2.fetchone()

        conn.close()
        return (result1 is not None or result2 is not None)

    def get_data(self, table=None):                                        # Function to retrieve and display data from Database on server
        date_to = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_from = (datetime.datetime.now() - datetime.timedelta(days=ACTIVE_PERIOD)).strftime('%Y-%m-%d %H:%M:%S')

        conn = self.get_connection()
        cursor = conn.cursor()
        
        if table:
            cursor.execute(f"SELECT * FROM {table} WHERE last_updated BETWEEN ? AND ? ORDER BY mpr_num DESC", (date_from, date_to))
            rows = cursor.fetchall()

        conn.close()

        data = []
        for row in rows:
            data.append({
                "PR No.": row[0],
                "PR Link": row[1],
                "Review Status": row[2],
                "Merge Conflicts": row[3],
                "PR Status": row[4],
                "Owner": row[5]
            })
        return data
     
    def add_comment_to_pr(self,github_url, repo_name, pr_number, comment_body, auth):      # Function to comment on PR using Github API
     try:
        # Initializing the GitHub object using the personal access token
        g = Github(auth=auth, base_url=f"{github_url}/api/v3")
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(comment_body)
        print(f"Comment added to PR #{pr_number} in {repo_name} successfully.")

     except Exception as e:
        print(f"Error adding comment: {e}")	

    def run_sql_query(self, query):                                     # Function to run SQL query on server
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            raw_result = [dict(zip(columns, row)) for row in rows]

            key_map = {
                "mpr_num": "PR No.",
                "meta_link": "PR Link",
                "review_status": "Review Status",
                "merge_conflict": "Merge Conflicts",
                "mpr_status": "PR Status",
                "owner": "Owner"
            }

            result = []
            for row in raw_result:
                mapped_row = {key_map.get(k, k): v for k, v in row.items()}
                result.append(mapped_row)

            return result
        except Exception as e:
            raise Exception(str(e))
        finally:
            conn.close()


class GithubPRWebApp:
    def __init__(self, github_token=GH_TK, database_path = DATABASE_FILE, port=5000):
        self.database_path = database_path
        self.port = port
        self.auth = Auth.Token(github_token)
        self.app = Flask(__name__)
        self.pr_db = PRDatabase(self.database_path)
        self.setup_routes()
        self.config=ConfigInfo(dashboard_conf="Github_Dashboard_Config")
        self.cict_config=ConfigInfo(dashboard_conf="Jenkins_Dashboard_Config")

    def setup_routes(self):
        @self.app.route('/')
        def index():                                                   #Routing to index.html
            return render_template('index.html', config=self.config.json_data['config'])

        @self.app.route('/get-permissions')
        def get_permissions():                                        # Check Permission function to enable/disable buttons using action-labels
            row_id = int(request.args.get('id', 0))
            meta_pr_tb = self.config.get_meta_pr_db_table()
            sub_pr_tb = self.config.get_sub_pr_db_table()
            return jsonify({
                "checkReview": self.pr_db.check_review_status(row_id, sub_pr_tb),
                "checkConflict": self.pr_db.check_merge_conflict(row_id, meta_pr_tb, sub_pr_tb),
                "checkStatus": self.pr_db.check_pr_status(row_id, meta_pr_tb, sub_pr_tb)
            })

        @self.app.route('/get_data')
        def get_data():
            variant = str(request.args.get('variant', None))
            self.config.switch_project_type(variant)
            meta_pr_table = self.config.get_meta_pr_db_table()
            return jsonify(self.pr_db.get_data(table=meta_pr_table))

        @self.app.route('/run_query', methods=['POST'])
        def run_query():                                           # Routing to run sql query function
            query = request.json.get('query')
            table = re.findall(r'[fF][rR][oO][mM]\s([\d.\w_\-]+)',query)
            if (len(table)!=0):
                table = table[0]
                for item in self.config.json_data['config']:
                    if table in (item['meta_pr_database_table'], item['sub_pr_database_table']):
                        self.config.switch_project_type(item['type'])
            try:
                result = self.pr_db.run_sql_query(query)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 400

        @self.app.route('/button_action', methods=['POST'])
        def action_button():                                     # Python function for action button when enabled button is clicked to respond
            data = request.json                                  # and comment on corresponding PR
            pr_no = data.get("pr_no")
            action = data.get("action")
            owner = data.get("user")

            auth = Auth.Token(GH_TK)
            github_server = self.config.get_github_server()
            org = self.config.get_github_organization()
            repository = self.config.get_github_meta_repo()
            repo_name = f"{org}/{repository}"
            review_comment = f"Hello @{owner}, Please get all your sub-repos reviewed!"                          # Comments based on PR actions
            conflict_comment = f"Hello @{owner}, Please solve your merge conflict in Meta-repo!"
            status_comment = f"Hello @{owner}, Please change your Sub-repo/Meta-repo status from Draft to Open!"

            try:
                if action == "Review Status":
                    self.pr_db.add_comment_to_pr(github_server, repo_name, pr_no, review_comment, auth=auth)
                elif action == "Merge Conflict":
                    self.pr_db.add_comment_to_pr(github_server, repo_name, pr_no, conflict_comment, auth=auth)
                elif action == "PR Status":
                    self.pr_db.add_comment_to_pr(github_server, repo_name, pr_no, status_comment, auth=auth)

            except Exception as e:
                print(f"[ERROR] Exception while commenting: {e}")
                return jsonify({"message": f"Failed to comment on PR: {e}"}), 500

            return jsonify({"message": f"{action} action completed for PR #{pr_no}."})

        @self.app.route('/update', methods=['POST'])
        def github_webhook_trigger():
            data = request.json
            call = False
            action = 'update'
            if data.get('pull_request', False):
                if data.get('review', False):
                    if data['action'] == 'submitted':
                        logger.info(f'Detected review activity on {data["pull_request"]["html_url"]}')
                        call = True
                        action = 'update'
                else:
                    if data['action'] == 'closed':
                        logger.info(f'Detected PR closed activity on {data["pull_request"]["html_url"]}')
                        action = 'delete'
                        call = True
                    elif data['action'] == 'reopened':
                        logger.info(f'Detected PR reopened activity on {data["pull_request"]["html_url"]}')
                        action = 'update'
                        call = True
                    elif data['action'] == 'opened':
                        logger.info(f'Detected PR opened activity on {data["pull_request"]["html_url"]}')
                        action = 'update'
                        call = True
                    elif data['action'] == 'synchronize':
                        logger.info(f'Detected commits on {data["pull_request"]["html_url"]}')
                        action = 'update'
                        call = True
                    elif data['action'] == 'ready_for_review':
                        logger.info(f'Detected PR draft to open on {data["pull_request"]["html_url"]}')
                        action = 'update'
                        call = True
                    elif data['action'] == 'review_requested':
                        logger.info(f'Detected review request on {data["pull_request"]["html_url"]}')
                        action = 'update'
                        call = True
                    elif data['action'] == 'unlabeled':
                        if data['label']['name'] in conf.get_labels_list():
                            logger.info(f'Detected jenkins job completion on {data["pull_request"]["html_url"]}')
                            try:
                                response = requests.post(f"{self.cict_config.get_ip_address()}:{self.cict_config.get_port()}/update", headers = {"Content-Type": "application/json"}, json={"job_label":f"{data['label']['name']}"})
                                logger.info(response)
                            except Exception as e:
                                logger.error(f"Error while sending HTTP request to Jenkins web server: {e}")
                if call:
                    task = {'url':data["pull_request"]["html_url"], 'action': action}
                    webhook_update_q.put(task)
            elif data.get('issue', False):
                logger.info(f'Detected comment activity on {data["issue"]["pull_request"]["html_url"]}')
                action = 'update'
                task = {'url': data["issue"]["pull_request"]["html_url"], 'action': action}
                webhook_update_q.put(task)
            return '', 204
    
    def run(self):
        self.app.run(debug=True, host='0.0.0.0', port=self.port)

def print_keys(d, parent_key=''):
    """
    This function can be used for debugging to print the keys of the github payload
    """
    for k, v in d.items():
        full_key = f"{parent_key}.{k}" if parent_key else k
        logger.info(full_key)
        if isinstance(v, dict):
            print_keys(v, full_key)

def get_last_updated_datetime(pull_request):
    commits = list(pull_request.get_commits())
    datetimelist = []
    if commits:
        datetimelist.append(commits[-1].commit.author.date)
    review_comments = list(pull_request.get_comments())
    if review_comments:
        datetimelist.append(review_comments[-1].created_at)
    issue_comments = list(pull_request.get_issue_comments())
    if issue_comments:
        datetimelist.append(issue_comments[-1].created_at)
    reviews = list(pull_request.get_reviews())
    if reviews:
        datetimelist.append(reviews[-1].submitted_at)
    return max(datetimelist).strftime("%Y-%m-%d %H:%M:%S")

def get_pr_review_merge_status(pull_request):
    if pull_request.draft == True:
        pr_status = 'draft'
    else:
        pr_status = 'open'
    if pull_request.mergeable: 
        merge_conflict = 0
    else: 
        merge_conflict = 1
    review_status = 'None'
    reviews = list(pull_request.get_reviews())
    if reviews:
        for review in reviews:
            review_status = review.state
            if review.state not in ['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED', 'PENDING', 'DISMISSED', 'NONE']:
                review_status = 'None'
    return pr_status, merge_conflict, review_status

def get_all_open_pr(github, target_branch, org_repository, meta_pr_table, pr_set=None):
    prs=[]
    # Specify the repository you want to access (owner/repo)
    # Get all open pull requests (optional: you can filter by state: 'open', 'closed', 'all')
    if pr_set is not None:
        pull_requests = []
        for pr_num in pr_set:
            pull_requests.append(github.get_single_pull_request(org_repository, pr_num))
    else:
        pull_requests = github.get_all_pull_requests(org_repository,target_branch,'open')  # Replace with your actual repo name (e.g., "octocat/Hello-World")

    sqlcmd= sql_command(DATABASE_FILE)
    for mpr in pull_requests:
        if mpr.state == 'open':
            data_dict=sqlcmd.create_dictionary_from_table(meta_pr_table)
            data_dict['last_updated'] = get_last_updated_datetime(mpr)
            data_dict['mpr_num'] = mpr.number
            data_dict['meta_link'] = mpr.html_url
            data_dict["owner"] = mpr.user.login
            data_dict['mpr_status'], data_dict['merge_conflict'], data_dict['review_status'] = get_pr_review_merge_status(mpr)
            logger.info(f"PR data dict {data_dict}") 
            prs.append(data_dict.copy())
        else:
            logger.info(f"pull request {mpr.number} was recently closed/merged.")
    sqlcmd.close_database()
    return prs

def get_sub_pr(url, table):
    # url of git hub
    logger.info(url)
    ret = {}
    # access to url and get info
    try:
        url_obj = InfoFromUrl(url, '')
    except:
        print(f"Error: Url:{url} is not valid. Please check")
        return ret
    # print(url_obj.url_content,  file=open('log.txt', 'w', encoding='utf-8'))

    # extract info from url
    sub_repos = url_obj.extract_info_from_url(r"SubRepos:\n\n([\w\n\/.#-]+[\d]+)")
    if len(sub_repos) == 0:
        ret["sub_repos"] = []
    else:
        ret["sub_repos"]=sub_repos[0].split("\n")
        # delete the last empty in sub_repos 
        if ret["sub_repos"][len(ret["sub_repos"])-1] == "":
            ret["sub_repos"].pop()
    usr = url_obj.extract_info_from_url(r"by (.*) · Pull Request")
    logger.info(f"sub repos are: {ret['sub_repos']}")
    # logger.info(f"user is {usr[0]}")
    return ret

def get_sub_pr_info(github, sub_pr, data_dict, meta_pr=0):
    match=re.findall("(.*)/(.*)#(.*)",sub_pr)
    org = match[0][0]
    repo_name = match[0][1]
    sub_pr_num = int(match[0][2])
    mpr_num = meta_pr
    spr = github.get_single_pull_request(f"{org}/{repo_name}",sub_pr_num) 
    data_dict['mpr_num'] = mpr_num
    data_dict['sub_pr_num'] = spr.number
    data_dict['sub_link'] = spr.html_url
    data_dict["owner"] = spr.user.login
    data_dict['spr_status'], data_dict['merge_conflict'], data_dict['review_status'] = get_pr_review_merge_status(spr)
    logger.info(f"sub-repo PR data dict: {data_dict}") 
    return data_dict

def check_pr_exist(sql, meta_pr_num, sub_link,table):
    if meta_pr_num != 0:
        row = sql.execute_query_fetchone(f"SELECT * FROM {table} WHERE mpr_num = {meta_pr_num}")
    elif sub_link != '':
        row = sql.execute_query_fetchone(f"SELECT * FROM {table} WHERE sub_link = '{sub_link}'")
    else:
        raise Exception(f"Invalid pull request number: {meta_pr_num}")
    
    # Check if the data was found
    if row:
        logger.info("Data found in database:")
        logger.info(row) 
        return True, row
    else:
        logger.info(f"No data found for {meta_pr_num} {sub_link}.")
        return False, None

def execute_update_command_meta(dict,table,sql):
    try:
        sql.execute_update_command(dict, table, 'mpr_num')
    except Exception as e:
        logger.error(f"{e}: ERROR: Updating meta_pullrequest table")

def execute_update_command_sub(dict,table,sql):
    try:
        merge_conflict = dict.get('merge_conflict')
        review_status = dict.get('review_status')
        sub_pr_num = dict.get('sub_pr_num')
        spr_status = dict.get('spr_status')
        mpr_num = dict.get('mpr_num')
        values = (merge_conflict,review_status,spr_status,sub_pr_num,mpr_num)  # Get the values from the dictionary
        logger.info(f"Updating sub_pullrequest table {table} with: {values}")
        sql_statement = f'''UPDATE {table} 
                       SET merge_conflict = {merge_conflict},review_status= "{review_status}",spr_status = "{spr_status}"
                       WHERE sub_pr_num = {sub_pr_num} AND mpr_num = {mpr_num}'''
        sql.execute_query(sql_statement)
    except Exception as e:
        logger.error(f"{e}: Error: While updating sub_pullrequest table")

def get_configuration(prj_type):
    conf.switch_project_type(prj_type)
    github_server = conf.get_github_server()
    organization = conf.get_github_organization()
    repository = conf.get_github_meta_repo()
    target_branch = conf.get_github_target_branch()
    meta_database_table = conf.get_meta_pr_db_table()
    sub_database_table = conf.get_sub_pr_db_table()

    return github_server, organization, repository, target_branch, meta_database_table, sub_database_table

def update_database_from_scratch():
    logger.info(f'Starting database update in thread: {threading.current_thread().name}')
    try:
        if os.path.exists(DATABASE_FILE):
            logger.info(f"Database {DATABASE_FILE} already exists.")
        else:
            logger.info(f"Database {DATABASE_FILE} does not exist, it will be created.")
        for project in conf.json_data['config']:
            logger.info(f"Starting database update for {project['type']}")
            gh_server, org, meta_repo, target_branch, meta_pr_tb, sub_pr_tb = get_configuration(project['type'])
            logger.info(f"Github server:{gh_server}")
            logger.info(f"Github organization: {org}")
            logger.info(f"Github repository and branch: {meta_repo}, {target_branch}")
            logger.info(f"Meta and Sub pull request tables: {meta_pr_tb} and {sub_pr_tb}")
            sql_cmd = sql_command(DATABASE_FILE)
            sql_cmd.execute_query(f'''CREATE TABLE IF NOT EXISTS {meta_pr_tb} (
                            mpr_num INTEGER PRIMARY KEY,
                            meta_link VARCHAR,
                            review_status VARCHAR,
                            merge_conflict BOOLEAN,
                            mpr_status VARCHAR,
                            owner VARCHAR,
                            last_updated TEXT
                        )''')
            sql_cmd.execute_query(f'''CREATE TABLE IF NOT EXISTS {sub_pr_tb} (
                            mpr_num INTEGER,
                            sub_pr_num INTEGER,
                            sub_link VARCHAR PRIMARY KEY,
                            review_status VARCHAR,
                            merge_conflict BOOLEAN,
                            spr_status VARCHAR,
                            owner VARCHAR
                        )''')
            github_mpr_num_tuple = update_specific_database(sql_cmd, gh_server, org, meta_repo, target_branch, meta_pr_tb, sub_pr_tb)
            sql_cmd.close_database()
            clean_database(github_mpr_num_tuple, meta_pr_tb, sub_pr_tb)
            logger.info(f"database updated and cleaned for {project['type']}\n")

    except Exception as e:
        logger.error(f"{e}")

def update_specific_database(sql, github_server, organization, repo, branch, meta_pr_db_tb, sub_pr_db_tb, pr_set=None):
    try:
        gh = GithubInstance(token=GH_TK, base_url=f"{github_server}/api/v3")
        mpr_num_tuple= ()
        for pr_dict in get_all_open_pr(gh, branch, f'{organization}/{repo}', meta_pr_db_tb, pr_set):
            mpr_num_tuple += (pr_dict['mpr_num'],)
            found, db_tuple= check_pr_exist(sql, pr_dict['mpr_num'],'',meta_pr_db_tb)
            if not found:
                sql.insert_dictionary_to_table(pr_dict,meta_pr_db_tb)
                logger.info(f'insert into table: {pr_dict}')
            else:
                if (tuple(pr_dict.values()) != db_tuple):
                    execute_update_command_meta(pr_dict,meta_pr_db_tb,sql)
                    logger.info(f'update meta_pullrequest table with: {pr_dict}\n')
                else:
                    logger.info(f"nothing to update")

            # get sub-repos 's pull reuest from the meta repo's pull request
            url = github_server +"/"+ organization +"/"+ repo  +"/pull/"+ str(pr_dict["mpr_num"]) 
            ret = get_sub_pr(url, sub_pr_db_tb)
            sub_prs = ret['sub_repos']
            for sub_pr in sub_prs:
                empty_sub_pr_dict = sql.create_dictionary_from_table(sub_pr_db_tb)
                data_dict = get_sub_pr_info(gh, sub_pr, empty_sub_pr_dict, meta_pr=pr_dict["mpr_num"])
                found , db_spr_tuple = check_pr_exist(sql,0,data_dict['sub_link'],sub_pr_db_tb)
                if not found:
                    sql.insert_dictionary_to_table(data_dict,sub_pr_db_tb)
                    logger.info(f'insert into table: {data_dict}')
                else:
                    if (tuple(data_dict.values()) != db_spr_tuple):
                        execute_update_command_sub(data_dict,sub_pr_db_tb,sql)
                        logger.info(f'update sub_pullrequest table with: {data_dict}\n')
                    else:
                        logger.info(f"nothing to update")

    except Exception as e:
        logger.error(f"{e}")
    finally:
        return mpr_num_tuple
    
def clean_database(github_pr_tuple, meta_pr_table, sub_pr_table):
    logger.info("Starting database cleanup")
    sql_cmd = sql_command(DATABASE_FILE)
    num_github_pr = len(github_pr_tuple)
    num_db_pr = sql_cmd.get_number_of_entries(meta_pr_table)
    if num_db_pr > num_github_pr:
        logger.info(f"Some PRs are merged, cleaning up database")
        sql_cmd.execute_query(f"DELETE FROM {meta_pr_table} WHERE mpr_num NOT IN {github_pr_tuple}")
        sql_cmd.execute_query(f"DELETE FROM {sub_pr_table} WHERE mpr_num NOT IN {github_pr_tuple}")
    logger.info("Database cleanup done")
    sql_cmd.close_database()

def task_schedule():
    try:
        logger.info("Task Scheduled to run every hour. Press Ctrl+C to stop the scheduled task")
        schedule.every().hour.do(update_active_PRs_statusses)
        while True:
            schedule.run_pending()
            time.sleep(3)
    except KeyboardInterrupt:
        print("keyboard interrupt! Stopping the scheduled task")

def github_hook_update(url, action):
    match = re.match(r"(http[s]*://github.*)/(.*)/(.*)/(.*)/(.*)", url)
    detected_github_url = match.group(1)
    github_obj = GithubInstance(token=GH_TK, base_url=f"{detected_github_url}/api/v3")
    detected_org = match.group(2)
    detected_repo = match.group(3)
    detected_pr_num = int(match.group(5))
    pr_obj = github_obj.get_single_pull_request(f"{detected_org}/{detected_repo}", detected_pr_num)
    detected_target_branch = pr_obj.base.ref
    found_config = False
    for project in conf.json_data['config']:
        conf.switch_project_type(project['type'])
        if detected_github_url == conf.get_github_server() and detected_org == conf.get_github_organization() \
        and detected_repo == conf.get_github_meta_repo() and detected_target_branch == conf.get_github_target_branch():
            found_config = True
            meta_pr_tb = project['meta_pr_database_table']
            sub_pr_tb = project['sub_pr_database_table']
            break
    if found_config:
        sql_cmd = sql_command(DATABASE_FILE)
        # logger.info("config found!")
        if action == 'delete':
            logger.info(f"Removing from database...")
            sql_cmd.execute_query(f"DELETE FROM {meta_pr_tb} WHERE mpr_num ={detected_pr_num}")
            sql_cmd.execute_query(f"DELETE FROM {sub_pr_tb} WHERE mpr_num = {detected_pr_num}")
            logger.info("Database cleanup done.")
        elif action == 'update':
            logger.info(f"update {detected_pr_num}")
            update_specific_database(sql_cmd, detected_github_url, detected_org, detected_repo, detected_target_branch, meta_pr_tb, sub_pr_tb, set([detected_pr_num]))
            logger.info(f"update {detected_pr_num} and sub repos done")


def handle_webhook():
    while True:
        if not webhook_update_q.empty():
            logger.info(f"current queue length is {webhook_update_q.qsize()}")
            task = webhook_update_q.get()
            github_hook_update(task['url'], task['action'])
        time.sleep(1)

def update_active_PRs_statusses():
    for project in conf.json_data['config']:
        conf.switch_project_type(project['type'])
        gh_server, org, meta_repo, target_branch, meta_pr_tb, sub_pr_tb = get_configuration(project['type'])
        logger.info(f"{project['type']}: Updating PR statusses")
        sql_cmd = sql_command(DATABASE_FILE)
        github_inst = GithubInstance(token=GH_TK, base_url=f"{gh_server}/api/v3")
        date_to = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_from = (datetime.datetime.now() - datetime.timedelta(days=ACTIVE_PERIOD)).strftime('%Y-%m-%d %H:%M:%S')
        sql_cmd = sql_command(DATABASE_FILE)
        results =sql_cmd.execute_query_fetchall(f"SELECT * FROM {meta_pr_tb} WHERE last_updated BETWEEN '{date_from}' AND '{date_to}' ORDER BY mpr_num DESC")
        for row in results:
            db_row_tuple = (row[0], row[4], row[3], row[2], row[6])
            logger.info(f"Updating pull request {row[0]}")
            pr = github_inst.get_single_pull_request(f'{org}/{meta_repo}', row[0])
            data_dict = {}
            data_dict['mpr_num'] = int(row[0])
            data_dict['mpr_status'], data_dict['merge_conflict'], data_dict['review_status'] = get_pr_review_merge_status(pr)
            data_dict['last_updated'] = get_last_updated_datetime(pr)
            if (tuple(data_dict.values())!= db_row_tuple):
                sql_cmd.execute_update_command(data_dict, meta_pr_tb, 'mpr_num')
                logger.info(f"updating {db_row_tuple} -> {tuple(data_dict.values())}")

            ret = get_sub_pr(f'{gh_server}/{org}/{meta_repo}/pull/{str(row[0])}', sub_pr_tb)
            for sub_pr in ret['sub_repos']:
                spr = github_inst.get_single_pull_request(str(sub_pr).split('#')[0], int(str(sub_pr).split('#')[1]))
                sub_pr_row =sql_cmd.execute_query_fetchone(f"SELECT * FROM {sub_pr_tb} WHERE sub_pr_num = {int(str(sub_pr).split('#')[1])}")
                db_sub_pr_row_tuple = (sub_pr_row[1], sub_pr_row[5], sub_pr_row[4], sub_pr_row[3])
                sub_pr_data_dict = {}
                sub_pr_data_dict['sub_pr_num'] = int(str(sub_pr).split('#')[1])
                sub_pr_data_dict['spr_status'], sub_pr_data_dict['merge_conflict'], sub_pr_data_dict['review_status'] = get_pr_review_merge_status(spr)
                if (tuple(sub_pr_data_dict.values()) != db_sub_pr_row_tuple):
                    sql_cmd.execute_update_command(sub_pr_data_dict, sub_pr_tb, 'sub_pr_num')
                    logger.info(f"updating {db_sub_pr_row_tuple} -> {tuple(sub_pr_data_dict.values())}")
            logger.info(f"Update done for PR {row[0]}")

        open_pr_tuple = tuple(open_pr.number for open_pr in github_inst.get_all_pull_requests(f'{org}/{meta_repo}',target_branch,'open'))
        clean_database(open_pr_tuple, meta_pr_tb, sub_pr_tb)

if __name__ == '__main__':
    logger.info('Starting Github PR dashboard application')
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true': #Flask triggers 2 processes, resulting double update. Checking this env variable ensure only the main process executes the update
        update_database_from_scratch()

        # Ensure logging configuration is set up before starting the thread
        thread1 = threading.Thread(target=task_schedule)
        thread1.daemon = True
        thread1.start()

        thread2 = threading.Thread(target=handle_webhook)
        thread2.daemon=True
        thread2.start()


    # Run the Flask app in the main thread
    app = GithubPRWebApp(database_path=DATABASE_FILE, port=PORT)
    app.run()
    logger.info('Flask app started')
    logger.info(f'Please access localhost:{PORT}')

 

