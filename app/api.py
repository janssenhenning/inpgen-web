import os
import uuid
import shutil

#Workaround for path
import sys
from pathlib import Path
sys.path.insert(0,os.fspath(Path(__file__).parent))

from celery.app.task import Task
import celery.states as states
from flask import Flask, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from worker import celery

from flask_cors import CORS

app = Flask(__name__)

CORS(app)
TASKS = {}

UPLOAD_FOLDER = '/app/uploads'
QUEUE_FOLDER = '/queue/uploads'
if not Path(UPLOAD_FOLDER).exists():
    Path(UPLOAD_FOLDER).mkdir()
ALLOWED_EXTENSIONS = {'cif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def create_input_from_cif():

    task_id = str(uuid.uuid4())
    folder = Path(app.config['UPLOAD_FOLDER']) / task_id

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir()
            file.save(os.path.join(folder, filename))
            task = celery.send_task('tasks.create_input', args=[os.fspath(Path(QUEUE_FOLDER) / task_id), filename], kwargs={})

            response = f"<a href='{url_for('get_task', task_id=task.id, external=True)}'>check status of {task.id} </a>"
            return response

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/<string:task_id>', methods=['GET'])
def get_task(task_id):
    
    res = celery.AsyncResult(task_id)
    if res.state == states.PENDING:
        return res.state
    else:
        return jsonify(res.result)

if __name__ == '__main__':
    app.run(debug=True)
            

