import os , sys
sys.path.append(os.path.join(os.path.dirname(__file__)+'\..\core'))
from config_info import ConfigInfo
from info_from_url import InfoFromUrl
import re

conf_info = ConfigInfo(dashboard_conf="CICT_Dashboard_Config")

if __name__ == '__main__':
    while True:
        print("\n====================================================================================")
        input_url = str(input('Please input the jenkins URL of the job you want to extract the logs from:\n'))

        if (len(re.findall(r'https://jenkins.*\/([\d]+)', input_url))==0):
            print("ERROR! Please input a valid jenkins URL with build number!")
        else:
            print("Generating...")
            build_number = re.findall(r'https://jenkins.*\/([\d]+)', input_url)[0]
            if not os.path.exists(f"{build_number}_logs"):
                os.makedirs(f"{build_number}_logs")
                urlcontentobj = InfoFromUrl(f'{input_url}', '')
                print(urlcontentobj.url_content, file=open(f'{build_number}_logs/urlcontent.txt', 'w', encoding=('utf-8')))

                apixmlobj = InfoFromUrl(f'{input_url}/api/xml', '')
                print(apixmlobj.url_content, file=open(f'{build_number}_logs/apixml.txt', 'w', encoding='utf-8'))

                consolelogobj = InfoFromUrl(f'{input_url}/consoleText', '')
                print(consolelogobj.url_content, file=open(f'{build_number}_logs/log.txt', 'w', encoding='utf-8'))

                print(f"\nLogs generation Successful, please copy \"{build_number}_logs\" folder to the correct location")
            else:
                print(f"\nLogs generation failed! \"{build_number}_logs\" already exists!")
