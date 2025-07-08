from thread_worker import *
from time import sleep
from flask import Flask, jsonify
import flask
from fileproc import *
from app_config import *
import threading
import uuid

app = Flask('AIProcessingApi')

# API endpoint to get thread status
@app.route('/api/process_output/<thread_id>', methods=['GET'])
def process_output(thread_id):
    status = get_thread_status(thread_id)
    output = get_thread_output(thread_id)
    file = Path(LOCAL_PATH_OUT + output)
    if(not output=="" and file.exists() and file.is_file()):
        return flask.send_file(str(file), as_attachment=True, download_name=output)
    else:
        if(not output=="" and status==Stage4): set_thread_status(thread_id, Stage0, OPFILE_NOT_FOUND_REPROCESS)
    return process_status(thread_id)
    
# API endpoint to get thread status
@app.route('/api/process_status/<thread_id>', methods=['GET'])
def process_status(thread_id):
    status = get_thread_status(thread_id)
    output = get_thread_output(thread_id)
    print(f"{get_thread_dtls(thread_id)}")
    msg = get_thread_dtls(thread_id)[MSG]
    return jsonify({'thread_id': thread_id, 'status': status, 'output': output, 'msg': msg})

@app.route('/api/process_file', methods=['POST'])
def process_file():
    if 'comp_files' not in flask.request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = flask.request.files['comp_files']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file.content_length is not None and file.content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 2MB limit'}), 400
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 2MB limit'}), 400
    
    file_content = file.read()

    # In extract_financial_data, after starting the thread:
    thread_id = str(uuid.uuid4())
    set_thread_status(thread_id, Stage1)
    set_thread_output(thread_id,"")
    thread = threading.Thread(target=worker, args=(thread_id, thread_id+"_"+file.filename, file_content))
    thread.start()
    return jsonify({'thread_id': thread_id, 'status': Stage1, 'output': ""})


if __name__ == '__main__':
    app.run(debug=False, threaded=True, host="0.0.0.0")
    #in production use gunicorn controller:app --bind 0.0.0.0:5000 --workers 4



