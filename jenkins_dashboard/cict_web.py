import sqlite3, time, datetime, logging, sys, os, re, html
import threading, subprocess, queue  # Example: You might use this for Git commands

try:
    from flask import Flask, request, render_template, redirect, url_for, flash, send_file
except ImportError:
    subprocess.run("python -m pip install flask==3.1.0", shell=True, check=True)
    from flask import Flask,jsonify, request, render_template, redirect, url_for, flash, send_file
try:
    import pandas as pd
except ImportError:
    subprocess.run("python -m pip install pandas==2.2.3", shell=True, check=True)
    import pandas as pd
from io import BytesIO
try:
    import openpyxl
except ImportError:
    subprocess.run("python -m pip install openpyxl==3.1.5", shell=True, check=True)
    import openpyxl
try:
    import schedule
except ImportError:
    subprocess.run("python -m pip install schedule==1.2.2", shell=True, check=True)
    import schedule

sys.path.append(os.path.join(os.path.dirname(__file__) + '\..\core'))
from config_info import ConfigInfo
from logging_config import logger
from sql_command  import sql_command
from jenkins_info import JenkinsJob

conf_info = ConfigInfo(dashboard_conf="Jenkins_Dashboard_Config")
PORT = int(conf_info.get_port())
DB_PATH = './jenkins_dashboard/database/database.db'
cict_webhook_update_q = queue.Queue()

class CICTWebApp:
    def __init__(self, database_path, port=5000):
        """
        Initialize the CICTWebApp object.

        :param database_path: Path to the SQLite database file.
        :param port: Port number for the Flask web application.
        """
        self.database_path = database_path
        self.app = Flask(__name__)
        self.app.secret_key = 'your_secret_key'  # Needed for flash messages
        self.port = port
        self.setup_routes()
        self.variant = "nothing"
        self.config=ConfigInfo(dashboard_conf="Jenkins_Dashboard_Config")

    def get_db_connection(self):
        """
        Establish a connection to the SQLite database.

        :return: SQLite database connection object.
        """
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def convert_datetime(self):
        """
        Convert date input from the request to datetime objects.

        :return: Tuple containing start and end datetime objects.
        """
        # get the date from the form
        date_from = str(request.form.get('date_from'))
        date_to = str(request.form.get('date_to'))
        # if the date is not provided, set the default date to 7 days ago
        if date_from == "None":
            date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        if date_to == "None":
            date_to = datetime.datetime.now().strftime('%Y-%m-%d')

        try:
            # Append time component to date input '2025.02.25 20:39:02'
            date_from = datetime.datetime.strptime(date_from + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            date_to = datetime.datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('home'))
        return date_from, date_to
    
    def setup_routes(self):
        """
        Set up the Flask routes for the web application.
        """
        @self.app.route('/')
        def home():
            """
            Render the home page.

            :return: Rendered home page template.
            """
            return render_template('index.html', config=self.config.json_data['config'])

        @self.app.route('/query', methods=['POST'])
        def run_query():
            """
            Run an SQL query and display the results.

            :return: Rendered template with query results or error message.
            """
            query = request.form.get('sql')
            self.variant = request.form.get('selected_variant')
            self.config.switch_project_type(self.variant)
            build_link = f"{self.config.get_jenkins_group_job_url()}/{self.config.get_job_names()}"
            DEFAULT_QUERY = f'SELECT * FROM {self.config.get_table()} WHERE created_at BETWEEN ? AND ? ORDER BY build_id DESC'
            empty = False
            # Check if the query is empty
            if query == '':
                empty = True
            # if the query is empty, run the default query with the date range
            if empty:
                date_from, date_to = self.convert_datetime()
                query = DEFAULT_QUERY
                params = (date_from, date_to)

            try:
                # connect to the database and execute the query
                conn = self.get_db_connection()
                cursor = conn.cursor()
                if empty:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    # conn.commit()
                rows = cursor.fetchall()
                conn.close()

                results = [dict(row) for row in rows]
                return render_template('index.html', results=results, query='', config=self.config.json_data['config'], buildlink= build_link, variant= self.variant)

            except Exception as e:
                return render_template('index.html', error=str(e), query=query, config=self.config.json_data['config'])
        
        @self.app.route('/update', methods=['POST'])
        def jenkins_update_trigger():
            data = request.json
            logger.info(f"Received Jenkins webhook update {data}")

            if data['job_label'] in ['check','merge','ReadyForMerge']:
                cict_webhook_update_q.put(data)

            return render_template('index.html')

    def run(self):
        """
        Run the Flask web application.
        """
        self.app.run(debug=True, host='0.0.0.0', port=self.port)

def update_database():
    logger.info(f'Starting database update in thread: {threading.current_thread().name}')
    for jenkins_instance in conf_info.json_data['config']:
        conf_info.switch_project_type(jenkins_instance['type'])
        CI_BUILD_JOB = conf_info.get_job_names()
        JENKINS_GROUP_JOB_URL = conf_info.get_jenkins_group_job_url()
        DB_TABLE = conf_info.get_table()
        CT_JOB_REGEX = conf_info.get_ct_jobs_regex()
        logger.info(f'Jenkins url: {JENKINS_GROUP_JOB_URL}')
        logger.info(f'Job name(s): {CI_BUILD_JOB}')
        logger.info(f'Database table: {DB_TABLE}')
        create_table(DB_TABLE)
        sql_cmd = sql_command(DB_PATH)
        ci_overview_jk= JenkinsJob(db_path=DB_PATH,jk_gr_jb_url=JENKINS_GROUP_JOB_URL,job_name=CI_BUILD_JOB, ct_tb= DB_TABLE)
        first_ci_build_no= ci_overview_jk.get_first_build()
        no_ci_jobs = ci_overview_jk.get_last_build()
        logger.info(f'Latest ci build number from Jenkins: {no_ci_jobs}')

        max_db_ci_build_no = sql_cmd.execute_query_fetchone(f'SELECT MAX(build_id) FROM {DB_TABLE}')[0]
        if max_db_ci_build_no is None:
            max_db_ci_build_no=0
        logger.info(f'Max build number in database: {max_db_ci_build_no}')

        if max_db_ci_build_no == no_ci_jobs:
            # if the database is up to date, skip the update
            last_ci_build = max_db_ci_build_no + 1 # Do not add into table the latest DB build
            logger.info(f'Database is up to date')
        elif max_db_ci_build_no >= first_ci_build_no:
            last_ci_build = max_db_ci_build_no + 1 # Do not add into table the latest DB build
        else:
            last_ci_build = first_ci_build_no
            logger.info(f'First build detected is {first_ci_build_no}')

        for ci in range(last_ci_build, no_ci_jobs+1):
            if ci_overview_jk.check_build_exists(ci) and not ci_overview_jk.is_build_replay(ci):
                # print(f"ci build {ci}")
                logger.info(f'Processing build number: {ci}')
                match = ci_overview_jk.get_variable_from_urlcontent(r'(https:\/\/github[\w\-.\/]+\/[^\/]+\/pull\/\d+)',str(ci))
                # print(match)
                if len(match) == 0:
                    PR_no='none'
                else:
                    PR_no=match[0]
                ct_job_set = ci_overview_jk.get_triggered_ct_jobs(fr'(https://jenkins[-.\w\d\/]+{CT_JOB_REGEX})', ci)
                # print(ct_job_set)
                cict_dict=ci_overview_jk.create_empty_dict_from_db_tb()
                cict_dict['build_id'] = ci
                cict_dict['pull_request_number'] = PR_no
                cict_dict['created_at'] = ci_overview_jk.get_datetime_variable(str(ci))
                if (len(ct_job_set) != 0):
                    # in each BVT job link
                    logger.info(f'triggered ct jobs: {ct_job_set}')
                    for job in ct_job_set:
                        # print(f"ct job is {job}")
                        match = re.search(r'/job/([^/]+)/(\d+)/$', job)
                        ct_jkjob = JenkinsJob(db_path=DB_PATH,jk_gr_jb_url=JENKINS_GROUP_JOB_URL,job_name=match.group(1), ct_tb= DB_TABLE)
                        cict_dict=ct_jkjob.get_ct_build_info(cict_dict, match.group(2))
                        build_result = ci_overview_jk.get_build_result(ci)
                        if (build_result != cict_dict['result']):
                            # when CT jobs succeed but CI build does not succeed
                            if (build_result == 'FAILURE'):
                                cict_dict['result'] = "POSTBUILD FAIL"
                                upload_artifacts_err = ci_overview_jk.get_variable_from_consoleText(r"rm: cannot remove '[\d\w]+': Device or resource busy", ci)
                                if (len(upload_artifacts_err) != 0):
                                    cict_dict['error_type'] = "upload-artifacts"
                                    cict_dict['error_logs'] = str(upload_artifacts_err[0])
                                else:
                                    cict_dict['error_type'] = "None"
                                    cict_dict['error_logs'] = "unable to identify error"
                            else:
                                cict_dict = handle_unstable_aborted_build(build_result, cict_dict, ci_overview_jk)
                        sql_cmd.insert_dictionary_to_table(cict_dict, DB_TABLE)
                        logger.info(f'all data of jenkin build job {cict_dict}')
                else:
                    build_result= ci_overview_jk.get_build_result(ci)
                    if (build_result == 'FAILURE'):
                        cict_dict['result'] == 'FAILURE'
                        cict_dict['error_type'], cict_dict['error_logs'] = ci_overview_jk.get_ci_error(ci)
                    else:
                        cict_dict = handle_unstable_aborted_build(build_result, cict_dict, ci_overview_jk)
                    sql_cmd.insert_dictionary_to_table(cict_dict, DB_TABLE)
                    logger.info(f'all data of jenkin build job {cict_dict}')
        sql_cmd.close_database()
        logger.info('Database update completed')

def handle_unstable_aborted_build(result, dict, ci_jenkins):
    if (result == 'UNSTABLE'):
        dict['result'] = "UNSTABLE"
        jira_err = ci_jenkins.get_variable_from_apixml(r"warning.summary(.*)</text>",dict['build_id'])
        if (len(jira_err) != 0):
            dict['error_type'] = "JiraVerification"
            error_log= html.unescape(str(jira_err[0]))
            formatted_err_log = re.sub('\'|\"', '', re.sub(r'\[[\d]{4}-[\d]{2}-[\d]{2}T[\d]{2}:[\d]{2}:[\d]{2}.[\d]{3}Z\]', '', re.sub(r'\r\n?|\n', '<br/>', error_log).replace('\t',' ')))
            dict['error_logs'] = formatted_err_log
        else:
            dict['error_type'] = "None"
            dict['error_logs'] = "unable to identify error"
    elif (result == 'ABORTED'):
        dict['result'] = 'ABORTED'
        dict['error_logs'] = 'ABORTED'
    else:
        dict['result'] = result
        
    return dict

def delete_table(table):
    sql_cmd = sql_command(DB_PATH)
    sql_cmd.execute_query(f"DROP TABLE IF EXISTS {table}")
    sql_cmd.close_database()

def create_table(table):
    sql_cmd = sql_command(DB_PATH)
    ct_db_command = f'''CREATE TABLE IF NOT EXISTS {table} (
                            pull_request_number TEXT,
                            build_id  INTEGER,
                            test_build_number INTEGER,
                            variant TEXT,
                            result TEXT,
                            error_type TEXT,
                            error_logs TEXT,
                            created_at TEXT,
                            test_link TEXT,
                            artifactory_link TEXT
                        )'''
    sql_cmd.execute_query(ct_db_command)
    # sql_cmd.verify_database(table)
    sql_cmd.close_database()

def debug(url):
    match = re.findall(r'(https://.*\/job)/(.*)/([\d]+)', url)
    if (len(match[0]) != 3):
        print("ERROR please input a valid jenkins job url")
    else:
        jenkins_group_job = match[0][0]
        jenkins_job = match[0][1]
        ci = match[0][2]
    ci_overview_jk= JenkinsJob(db_path=DB_PATH,jk_gr_jb_url=jenkins_group_job,job_name=jenkins_job)
    if ci_overview_jk.check_build_exists(str(ci)) and not ci_overview_jk.is_build_replay(ci):
        print(f"build is {ci}")
        match = ci_overview_jk.get_variable_from_urlcontent(r'(https:\/\/github[\w\-.\/]+\/[^\/]+\/pull\/\d+)',str(ci))
        # print(match)
        if len(match) == 0:
            PR_no='none'
        else:
            PR_no=match[0]
        ct_job_set = ci_overview_jk.get_triggered_ct_jobs(fr'({jenkins_group_job}/RBT[.\w]*/[0-9]+/)', ci)
        print(ct_job_set)
        cict_dict=ci_overview_jk.create_empty_dict_from_db_tb()
        # print(f"empty dict : {cict_dict}")
        cict_dict['build_id'] = ci
        cict_dict['pull_request_number'] = PR_no
        cict_dict['created_at'] = ci_overview_jk.get_datetime_variable(str(ci))
        if (len(ct_job_set) != 0):
            # in each BVT job link
            for job in ct_job_set:
                print(f"ct job is {job}")
                match = re.search(r'/job/([^/]+)/(\d+)/$', job)
                ct_jkjob = JenkinsJob(db_path=DB_PATH,jk_gr_jb_url=jenkins_group_job,job_name=match.group(1))
                cict_dict=ct_jkjob.get_ct_build_info(cict_dict, match.group(2))
                build_result = ci_overview_jk.get_build_result(ci)
                if (build_result != cict_dict['result']):
                    # when CT jobs succeed but CI build does not succeed
                    if (build_result == 'FAILURE'):
                        cict_dict['result'] = "POSTBUILD FAIL"
                        upload_artifacts_err = ci_overview_jk.get_variable_from_consoleText(r"rm: cannot remove '[\d\w]+': Device or resource busy", ci)
                        if (len(upload_artifacts_err) != 0):
                            cict_dict['error_type'] = "upload-artifacts"
                            cict_dict['error_logs'] = str(upload_artifacts_err[0])
                        else:
                            cict_dict['error_type'] = "None"
                            cict_dict['error_logs'] = "unable to identify error"
                    else:
                        cict_dict = handle_unstable_aborted_build(build_result, cict_dict, ci_overview_jk)
                logger.info(f'all data of jenkin build job {cict_dict}')
        else:
            build_result= ci_overview_jk.get_build_result(ci)
            if (build_result == 'FAILURE'):
                cict_dict['result'] == 'FAILURE'
                cict_dict['error_type'], cict_dict['error_logs'] = ci_overview_jk.get_ci_error(ci)
            else:
                cict_dict = handle_unstable_aborted_build(build_result, cict_dict, ci_overview_jk)
            logger.info(f'all data of jenkin build job {cict_dict}')
        logger.info('Database update completed')

def run_scheduled_tasks():
    # Schedule the update_ct_database function to run every hour
    schedule.every().hour.do(update_database)
    while True:
        schedule.run_pending()
        time.sleep(1)

def handle_webhook():
    while True:
        if not cict_webhook_update_q.empty():
            logger.info(f"Completion of Jenkins job detected")
            logger.info(f"Webhook queue length is {cict_webhook_update_q.qsize()}, updating database...")
            cict_webhook_update_q.get()
            update_database()
            time.sleep(1)

if __name__ == '__main__':
    logger.info('Starting application')

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true': #Flask triggers 2 processes, resulting double update. Checking this env variable ensure only the main process executes the update
        update_database()

    # Ensure logging configuration is set up before starting the thread
    hourly_update_thread = threading.Thread(target=run_scheduled_tasks)
    hourly_update_thread.daemon = True
    hourly_update_thread.start()

    handle_hooks_thread = threading.Thread(target=handle_webhook)
    handle_hooks_thread.daemon = True
    handle_hooks_thread.start()

    # Run the Flask app in the main thread
    app = CICTWebApp(DB_PATH, port=PORT)
    app.run()
    logger.info('Flask app started')
    logger.info(f'Please access localhost:{PORT}')
    logger.info(f'Please access <host pc name>:{PORT}')
