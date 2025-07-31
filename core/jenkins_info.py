import re
from info_from_url import InfoFromUrl
from sql_command import sql_command
import json
import xmltodict
import lxml.etree as ET
import html

from logging_config import logger
JENKINS_GROUP_JOB_URL = ""
JOB_NAME = ""
DB_PATH = ""

from jenkins_dashboard.error_config.error_config import CI_ERROR_PATTERN_MAP

class JenkinsJob:
    def __init__(self, jk_gr_jb_url = JENKINS_GROUP_JOB_URL, job_name = JOB_NAME, db_path = DB_PATH,ct_tb = '',test_mode = False):
        
        self.db_path = db_path
        self.job_name = job_name
        self.jenkins_group_job_url = jk_gr_jb_url
        self.test_mode = test_mode
        self.jenkins_job_url = f'{jk_gr_jb_url}/{job_name}'
        if self.test_mode:
            self.url_suffix = '/urlcontent.txt'
            self.apixml_suffix = '/apixml.txt'
            self.consoleText_suffix = 'log.txt'
        else:
            self.url_suffix = ''
            self.apixml_suffix = '/api/xml'
            self.consoleText_suffix = 'consoleText'

        self.info_ct_pipeline = InfoFromUrl(self.jenkins_job_url + self.url_suffix, '')
        self.info_api_xml= InfoFromUrl(self.jenkins_job_url + self.apixml_suffix, '')
        self.ct_tb=ct_tb

        logger.info(f'jenkin url: {self.jenkins_group_job_url}')
        logger.info(f'jenkin job url: {self.jenkins_job_url}')
    
    def create_empty_dict_from_db_tb(self):
        sql_cmd = sql_command(self.db_path)
        empty_dict = sql_cmd.create_dictionary_from_table(self.ct_tb)
        sql_cmd.close_database()
        return empty_dict
    
    def get_url_content(self, build_num=None):
        if build_num:
            info_build_url=InfoFromUrl(f'{self.jenkins_job_url}/{build_num}/{self.url_suffix}', '')

            return info_build_url.url_content
        else:
            return self.info_ct_pipeline.url_content
        
    def get_apixml_content(self, build_num=None):
        if build_num:
            info_build_apixml=InfoFromUrl(f'{self.jenkins_job_url}/{build_num}{self.apixml_suffix}', '')
            return info_build_apixml.url_content
        else:
            return self.api_xml.url_content
    def get_json_content(self, build_num=None):
        return (json.loads(json.dumps(xmltodict.parse(self.get_apixml_content(build_num)))))
    
    def get_variable_from_urlcontent(self, pattern, build_num=None):
        if build_num:
            info_build_url=InfoFromUrl(f'{self.jenkins_job_url}/{build_num}/{self.url_suffix}', '')

            return info_build_url.extract_info_from_url(pattern)
        else:
            return self.info_ct_pipeline.extract_info_from_url(pattern)
        
    def get_variable_from_apixml(self, pattern, build_num=None):
        if build_num:
            info_build_apixml=InfoFromUrl(f'{self.jenkins_job_url}/{build_num}/{self.apixml_suffix}', '')
            return info_build_apixml.extract_info_from_url(pattern)
        else:
            return self.info_api_xml.extract_info_from_url(pattern)
    
    def get_variable_from_consoleText(self, pattern, build_num):

        url = f'{self.jenkins_group_job_url}/{self.job_name}/{build_num}/{self.consoleText_suffix}'
        job_info = InfoFromUrl(url, '')

        return job_info.extract_info_from_url(pattern)
    
    def is_build_replay(self, build_num):
        if (len(self.get_variable_from_apixml(r'<shortDescription>Replayed\s#[\d,]+<\/shortDescription>', build_num)) !=0):
            return True
        else:
            return False
        
    def get_last_build(self):
        return int(self.get_variable_from_apixml(pattern=r'<lastCompletedBuild.*?>.*?<number>(\d+)</number>.*?</lastCompletedBuild>')[0])
    
    def get_first_build(self):
        return int(self.get_variable_from_apixml(pattern=r'<firstBuild.*?>.*?<number>(\d+)</number>.*?</firstBuild>')[0])
    
    def check_build_exists(self, build_num):
        return self.get_variable_from_apixml(pattern=r'<number>'+ str(build_num) +r'</number>')

    def get_build_result(self, build_num):
        job_result = self.get_variable_from_apixml(r'<result>(.*)</result>', str(build_num))
        if len(job_result) == 0:
            return "running"
        else:
            return job_result
        
    def get_triggered_ct_jobs(self, pattern, build_num):
        ct_job_list = self.get_variable_from_urlcontent(pattern, str(build_num))
        if (len(ct_job_list) == 0 ):
            ct_job_list = self.get_variable_from_consoleText(pattern, str(build_num))

        return set(ct_job_list)
    
    def get_failed_consolelog_obj(self, build_num):
        """
        Specific to within the 'parallel' gate, identify which particular task is failing

        :param build_num: an xml tree object that contains raw data of console urls and result
        :return: obj of class InfoFromUrl
        """

        json_content = self.get_json_content(build_num)
        obj=""
        nodeid = ""
        if not self.test_mode:
            for x in (json_content['workflowRun']['action']):
                if x is not None and "text" in x:
                    if "<b>failure</b>" in x['text']:
                        # decoded_html = re.search(r'taskStatus.*<br />', html.unescape(str(x['text']))).group(0)
                        decoded_html = str(x['text'])
                        xml_string = f"<root>{decoded_html}</root>"
                        parser = ET.XMLParser(recover=True)
                        tree = ET.ElementTree(ET.fromstring(xml_string, parser=parser))

            start=False
            links_list=[]
            results_list=[]
            for element in tree.getroot().iter():
                if element.text is not None:
                    # print(element.text)
                    if 'https://jenkins' in element.text:
                        if not start:
                            start=True
                        links_list.append(element.text)
                    elif 'failure' in element.text and start is True:
                        start=False
                        results_list.append(0)
                    elif 'success' in element.text and start is True:
                        start=False
                        results_list.append(1)
                    elif 'aborted' in element.text and start is True:
                        start=False
                        results_list.append(2)
            link_result_map= {}
            for i, link in enumerate(links_list):
                link_result_map[str(link)]= results_list[i]

            for consolelink, result in link_result_map.items():
                if not result:
                    # console log of task that failed
                    nodeid=str(re.findall(r'selected-node=([\d]+)',consolelink)[0])

            if nodeid != "":
                consoleUrl= f"{self.jenkins_job_url}/{build_num}/pipeline-console/log?nodeId={nodeid}"
                obj=InfoFromUrl(consoleUrl, '')
        else:
            obj = InfoFromUrl(f'{self.jenkins_job_url}/{build_num}/{self.consoleText_suffix}', '')

        return obj

    def get_ci_error(self, build_num):
        """
        For CI builds that do not trigger any CT jobs (BVT), check for all the possible errors
        according to the CI_ERROR_PATTERN_MAP and extract out the detailed error logs. If more
        new errors are detected and new Regex needed, please add to the CI_ERROR_PATTERN_MAP

        :param build_num: CI job number
        :return: detected error type, error logs
        """

        detected_error_type = 'None'
        detected_error_log = "None"
        outergate_errfound = False
        for error_type in CI_ERROR_PATTERN_MAP.keys():
            detected_string = self.get_variable_from_urlcontent(CI_ERROR_PATTERN_MAP[error_type]['pattern'], build_num)
            if ((len(detected_string) != 0) and not outergate_errfound):
                # print(f"detected error: {error_type} string :{detected_string}")
                detected_log = detected_string[0]
                detected_error_type = error_type
                outergate_errfound= True
        
                if detected_error_type == 'parallel':
                    parallelgate_errfound= False
                    for gate in CI_ERROR_PATTERN_MAP['parallel']['gate_errors'].keys():
                        gate_detected_string = self.get_variable_from_urlcontent(CI_ERROR_PATTERN_MAP['parallel']['gate_errors'][gate]['pattern'], build_num)
                        if (len(gate_detected_string)!=0):
                            # print(f"in parallel, detected error: {gate}")
                            gate_error = gate
                            gate_error_log = gate_detected_string[0]
                            detected_error_type += f":{gate}"
                            parallelgate_errfound = True
                            # get consolelog link for the specific failed task
                            urlobj = self.get_failed_consolelog_obj(build_num)
                            if 'errors' in CI_ERROR_PATTERN_MAP['parallel']['gate_errors'][gate_error]: #specific error
                                errlist=[]
                                parallel_build_errfound = False
                                for err, pattern_dict in CI_ERROR_PATTERN_MAP['parallel']['gate_errors'][gate_error]['errors'].items():
                                    if urlobj:
                                        if (len(urlobj.extract_info_from_url(pattern_dict['pattern']))!=0):
                                            # print(f"err in parallel detected {err}")
                                            errlist.append(err)
                                            parallel_build_errfound =True
                                            if pattern_dict['first_match']:
                                                detected_error_log = urlobj.extract_info_from_url(pattern_dict['pattern'])[0]
                                            else:
                                                matches = urlobj.extract_info_from_url(pattern_dict['pattern'])
                                                detected_error_log = str(err).upper() +':\n'+''.join(line for line in matches)
                                        else:
                                            if not parallel_build_errfound:
                                                detected_error_log = f'unable to identify error in {detected_error_type}'
                                if (len(errlist) !=0):
                                    detected_error_type += f":{errlist[-1]}"
                            else:
                                #generic handler for gate errors without 'errors' key
                                detected_error_log = str(gate_error_log)
                        else:
                            if not parallelgate_errfound:
                                detected_error_log = f'unable to identify error in {detected_error_type}'
                else:
                    # errors not within parallel
                    detected_error_log = str(detected_log)
            else:
                if not outergate_errfound:
                    detected_error_log = f'unable to identify error'

        # Remove any HTML formatting, remove timestamp strings, remove any quotes and replace any \n, \r with <br/>
        detected_error_log = html.unescape(detected_error_log)
        detected_error_log = re.sub('\'|\"', '', re.sub(r'\[[\d]{4}-[\d]{2}-[\d]{2}T[\d]{2}:[\d]{2}:[\d]{2}.[\d]{3}Z\]', '', re.sub(r'\r\n?|\n', '<br/>', str(detected_error_log)).replace('\t',' ')))
        return detected_error_type, detected_error_log

 
    def get_datetime_variable(self, build_no):
        datetime = self.get_variable_from_consoleText(build_num=build_no, pattern=r'imeStamp.*?(\d{4}.\d{2}.\d{2} \d{2}:\d{2}:\d{2})')
        if len(datetime) == 0:
            return 'None'
        else:
            return (datetime[0].replace('.', '-'))

    def get_ct_build_info(self, dict, test_build_number):
        """
        Retrieves information about a BVT job from a Jenkins server.
        """
        test_build_number = str(test_build_number)
        # Regular expressions to extract the information from the URL
        RE_PATTERN_ARTIFACTORY = r'url\s*:(.*?/bvt)'
        RE_PATTERN_TESTCASES = r"\[\d*\] = name  : '(.*?)'"
        RE_PATTERN_RESULTS = r"status: '(.*?)'"
        RE_PATTERN_ERRORS = r'(.*?) The process cannot access the file because it is being used by another process'

        # get the CT information from the Jenkins server
        url = f'{self.jenkins_job_url}/{test_build_number}/{self.consoleText_suffix}'

        info_ct_build = InfoFromUrl(url, '')
        # assign the values to the dictionary
        dict['test_build_number'] = test_build_number
        dict['variant'] = self.job_name
        dict['test_link'] = f'{self.jenkins_group_job_url}/{self.job_name}/{test_build_number}/'
        dict['result'] = self.get_build_result(test_build_number)

        if (dict['result'] == 'FAILURE'):
            dict['error_type'] = 'BVT pipeline'
            error_str = self.get_variable_from_urlcontent(r'<pre>(.*?)</pre>',test_build_number)
            if "Not all bvt tests succedded" in str(error_str):
                # duplicate the result of the CT in url content
                num = int(len(info_ct_build.extract_info_from_url(pattern=RE_PATTERN_RESULTS))/2) # 
                index = 0
                # TODO: Find all failed test cases. For now, only the first failed test case is considered.
                for r in info_ct_build.extract_info_from_url(pattern=RE_PATTERN_RESULTS):
                    if index == num or 'failure' in r:
                        break
                    index = index + 1
                # print(info_ct_build.extract_info_from_url(pattern=RE_PATTERN_TESTCASES)[index])
                dict['error_logs'] = info_ct_build.extract_info_from_url(pattern=RE_PATTERN_TESTCASES)[index]
                
            else:
                if len(error_str) > 0:
                    dict['error_logs'] = error_str[0]
                else:
                    dict['error_logs'] = 'None'
        else:
            dict['error_type'] = 'None'
            dict['error_logs'] = 'None'
        
        if (len(info_ct_build.extract_info_from_url(pattern=RE_PATTERN_ARTIFACTORY))!=0):
            dict['artifactory_link']= info_ct_build.extract_info_from_url(pattern=RE_PATTERN_ARTIFACTORY)[0]
        else:
            dict['artifactory_link'] = 'None'

        # print(dict)
        return dict

if __name__ == '__main__':
    jk_job = JenkinsJob()
    jk_job.get_ct_build(120)
    # jk_job.get_ct_build(jk_job.last_ct_build)
    # jk_job.get_ct_build(176)

