from pathlib import Path
from fileproc import *
from json_mapper import *

# Constants
Stage0='Error'
Stage1='Initiated'
Stage2='SaveFileContent'
Stage3='ExtractDataMap'
Stage4='GenerateXLS'
Stage5='Complete'

STAGE = 'status'
INPUT = 'input'
OUTPUT = 'output'
MSG = 'msg'

OPFILE_NOT_FOUND_REPROCESS="Output file not found, please reprocess the file"

# Dictionary to store thread statuses
threads = {}

def get_thread_dtls(thread_id, create_if_missing=False):
    if(create_if_missing and threads.get(thread_id) == None):
        threads[thread_id] = {STAGE: Stage0, INPUT: "", OUTPUT: "", MSG: ""}
    return threads.get(thread_id, {STAGE: Stage0, INPUT: "", OUTPUT: "", MSG: "No record found"})

def set_thread_status(thread_id, status, msg=""):
    get_thread_dtls(thread_id, True)[STAGE] = status
    get_thread_dtls(thread_id)[MSG] = msg
    log(f"Thread {thread_id} at {status}")


def get_thread_status(thread_id):
    return get_thread_dtls(thread_id).get(STAGE, Stage0)

def set_thread_output(thread_id, outfile):
    get_thread_dtls(thread_id)[OUTPUT] = Path(outfile).name

def get_thread_output(thread_id):
    return get_thread_dtls(thread_id).get(OUTPUT, "")

def init():
    Path(LOCAL_PATH_INP).mkdir(parents=True, exist_ok=True)
    Path(LOCAL_PATH_OUT).mkdir(parents=True, exist_ok=True)

def save_file_content(filename, file_content) -> str:
    temp_path = LOCAL_PATH_INP + filename
    write_to_fileb(temp_path, file_content)
    print(f"File saved to {temp_path}")
    return temp_path

def worker(thread_id, filename, content):
    init()
    try:
        get_thread_dtls(thread_id)[INPUT] = filename
        set_thread_status(thread_id, Stage2)
        file_path = save_file_content(filename, content)
        set_thread_status(thread_id, Stage3)
        map_file = extract_data_map(file_path, LOCAL_PATH_OUT, True)
        set_thread_status(thread_id, Stage4)
        xl_output=LOCAL_PATH_OUT+filename+"_tmpl.xlsx"
        json_to_xlsx(map_file, XL_TEMPLATE, xl_output)
        set_thread_output(thread_id, xl_output)
        set_thread_status(thread_id, Stage5)
        print(f"Processing {filename} ... Completed.")
    except Exception as e:
        set_thread_status(thread_id, Stage0, f"Error processing file")
        set_thread_output(thread_id, "")
        log(get_thread_dtls(thread_id)[MSG]+":"+str(e))

def test(thread_id, filename):
    with open(LOCAL_PATH_INP+thread_id+"_"+filename, "rb") as ifile:
        contents=ifile.read()
    worker(thread_id, thread_id+"_"+filename, contents)
    log(f"{thread_id} - {threads[thread_id]}")
