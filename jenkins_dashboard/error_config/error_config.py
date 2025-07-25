import json

"""
    Dictionary that contains all the possible errors in Jenkins job. The script uses this dict to extract error type and logs. 
    The structure follows the different gates of the pipeline. This is the entry point to add new error.

    In the sub-dictionary "parallel", it will contain most errors and future potential errors. Hence the handling is different.
    If there are more than 1 type of errors, "errors" gate is required to contain all possible known errors. In each error, there will be
    two keys, "pattern" and "first_match":

        "pattern": REGEX string to detect and extract from the console log of the task that failed
        "first_match" True if only first instance of the matches are required, False will take all the matches
    
    For sub-dictionaries other than "parallel", there is no need to check the consolelog, just checking the job's Jenkins Summary page
    will be sufficient
"""

CI_ERROR_PATTERN_MAP = {
    "error 1": {
        "pattern" : r'regex pattern 1'
    },
    "error 2": {
        "pattern" : r'regex pattern 1'
    },
    "error 3": {
        "pattern" : r'regex pattern 1'
    },
    "parallel": {
        "pattern": r'regex pattern describing parallel stage fail',
        "gate_errors" : {
            "stage 1 in parallel": {
                "pattern": r'regex pattern in stage 1'
            },
            "stage 2" : {
                "pattern":r'regex pattern in stage 2',
                "errors":{
                    "error 1":{
                        "pattern" : r"regex pattern",
                        "first_match" : True
                    },
                    "error 2": {
                        "pattern": r'regex pattern',
                        "first_match": True
                    }
                }
            },
            "stage 4" : {
                "pattern": r'regex pattern',
            }
        }
    }
}

def visualize_dict(d):
    print(json.dumps(d, indent=4, sort_keys=True))

# Example usage:
# visualize_dict(CI_ERROR_PATTERN_MAP)