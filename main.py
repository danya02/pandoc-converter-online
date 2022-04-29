from re import template
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_hcaptcha import hCaptcha
from dotenv import load_dotenv
import os
import uuid
import zipfile
import subprocess
load_dotenv('conf.env')


app = Flask(__name__)
app.config['HCAPTCHA_ENABLED'] = True
app.config['HCAPTCHA_SITE_KEY'] = os.getenv('HCAPTCHA_SITE_KEY')
app.config['HCAPTCHA_SECRET_KEY'] = os.getenv('HCAPTCHA_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = '/uploads'
app.config['TEMPLATE_FOLDER'] = '/render_templates'
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024    # 10 Mb limit
hcaptcha = hCaptcha(app)

def get_template_list():
    return os.listdir(app.config['TEMPLATE_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html', templates=get_template_list())

@app.route('/upload', methods=['POST'])
def upload_to_convert():
    """
    Accept a ZIP file upload.
    Check the captcha, then store the file in a temporary directory
    and redirect to the unzipping page.
    """
    if not hcaptcha.verify():
        flash('Invalid captcha')
        return redirect(url_for('index'))

    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))

    template = request.form.get('template')
    if template not in get_template_list():
        flash('Invalid compilation template')
        return redirect(url_for('index'))


    # Save the file to disk
    file = request.files['file']
    name = str(uuid.uuid4())
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], name + '.zip'))
    return redirect(url_for('unzip', name=name, template=template))


@app.route('/unzip/<name>/<template>')
def unzip(name, template):
    """
    Unzip the uploaded file.
    When unzipping is successful, redirect to the conversion page.
    """
    
    try:
        with zipfile.ZipFile(os.path.join(app.config['UPLOAD_FOLDER'], name + '.zip')) as zip_file:
            # Make folder for the unzipped files
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], name))
            # Extract the files
            zip_file.extractall(os.path.join(app.config['UPLOAD_FOLDER'], name))
    except FileNotFoundError:
        flash('No such file')
        return redirect(url_for('index'))
    except zipfile.BadZipFile:
        flash('Invalid ZIP file')
        return redirect(url_for('index'))

    return redirect(url_for('convert', name=name, template=template))

@app.route('/convert/<name>/<template>')
def convert(name, template):
    """
    Put the render template into the unzipped folder and begin the conversion.
    """

    directory = os.path.join(app.config['UPLOAD_FOLDER'], name)
    os.chdir(directory)

    # Remove the user's Makefile if it exists
    try:
        os.remove('Makefile')
    except FileNotFoundError:
        pass

    template = template.replace('/', '')

    # Copy files from the template folder to the user's folder
    # without overwriting the existing files
    template_root = os.path.join(app.config['TEMPLATE_FOLDER'], template)
    if not os.path.exists(template_root):
        flash('Invalid compilation template')
        return redirect(url_for('index'))
    
    for directory, subdirectories, files in os.walk(template_root):
        # For every file:
        for file in files:
            print(file)
            # Get the absolute path to the file
            file_path = os.path.join(directory, file)

            # Get path to this file in the template directory
            relative_path = os.path.relpath(file_path, template_root)

            # If the path doesn't exist in the user directory, copy it
            # (to the current directory, because we are in the user directory)
            if not os.path.exists(relative_path):
                # Make the directory if it doesn't exist
                if os.path.dirname(relative_path):
                    os.makedirs(os.path.dirname(relative_path), exist_ok=True)
                # then copy the file
                shutil.copy(file_path, relative_path)

    # Run the makefile, capturing the output
    handle = subprocess.Popen(['make'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    try:
        handle.wait(timeout=60)
    except subprocess.TimeoutExpired:
        handle.kill()
        flash('Compilation timed out')
        return redirect(url_for('index'))

    stdout = handle.stdout.read().decode('utf-8')
    stderr = handle.stderr.read().decode('utf-8')
    exit_code = handle.returncode

    # Now that the compilation is done, zip up the folder
    os.chdir('..')
    shutil.make_archive(name+'-output', 'zip', name)

    # Delete the unzipped folder
    #shutil.rmtree(name)

    # Render the result page
    return render_template('convert_result.html', name=name, stdout=stdout, stderr=stderr, exit_code=exit_code)

@app.route('/download/<name>')
def download_output(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], name + '-output.zip')

if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
