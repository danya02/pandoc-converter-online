from flask import Flask, render_template, request, redirect, url_for, flash
from flask_hcaptcha import hCaptcha
from dotenv import load_dotenv
import os
load_dotenv('conf.env')


app = Flask(__name__)
app.config['HCAPTCHA_ENABLED'] = True
app.config['HCAPTCHA_SITE_KEY'] = os.getenv('HCAPTCHA_SITE_KEY')
app.config['HCAPTCHA_SECRET_KEY'] = os.getenv('HCAPTCHA_SECRET_KEY')
app.secret_key = os.getenv('FLASK_SECRET_KEY')
hcaptcha = hCaptcha(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if not hcaptcha.verify():
        flash('Invalid captcha')
        return redirect(url_for('index'))
    return 'Submitted!'

if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
