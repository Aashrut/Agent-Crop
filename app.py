import os
import shutil
import time
import numpy as np
import pandas as pd
from keras.preprocessing.image import ImageDataGenerator
from keras.models import load_model
from PIL import Image
import gdown
from flask import Flask, render_template, request, redirect, flash, send_from_directory, url_for

from werkzeug.utils import secure_filename

disease_map = {0: 'Apple: Apple Scab',
        1: 'Apple: Black Rot',
        2: 'Apple: Cedar Rust',
        3: 'Apple: Healthy',
        4: 'Blueberry: Healthy',
        5: 'Cherry: Powdery Mildew',
        6: 'Cherry: Healthy',
        7: 'Corn (Maize): Grey Leaf Spot',
        8: 'Corn (Maize): Common Rust of Maize',
        9: 'Corn (Maize): Northern Leaf Blight',
        10: 'Corn (Maize): Healthy',
        11: 'Grape: Black Rot',
        12: 'Grape: Black Measles (Esca)',
        13: 'Grape: Leaf Blight (Isariopsis Leaf Spot)',
        14: 'Grape: Healthy',
        15: 'Orange: Huanglongbing (Citrus Greening)',
        16: 'Peach: Bacterial spot',
        17: 'Peach: Healthy',
        18: 'Bell Pepper: Bacterial Spot',
        19: 'Bell Pepper: Healthy',
        20: 'Potato: Early Blight',
        21: 'Potato: Late Blight',
        22: 'Potato: Healthy',
        23: 'Raspberry: Healthy',
        24: 'Rice: Brown Spot',
        25: 'Rice: Hispa',
        26: 'Rice: Leaf Blast',
        27: 'Rice: Healthy',
        28: 'Soybean: Healthy',
        29: 'Squash: Powdery Mildew',
        30: 'Strawberry: Leaf Scorch',
        31: 'Strawberry: Healthy',
        32: 'Tomato: Bacterial Spot',
        33: 'Tomato: Early Blight',
        34: 'Tomato: Late Blight',
        35: 'Tomato: Leaf Mold',
        36: 'Tomato: Septoria Leaf Spot',
        37: 'Tomato: Spider Mites (Two-spotted Spider Mite)',
        38: 'Tomato: Target Spot',
        39: 'Tomato: Yellow Leaf Curl Virus',
        40: 'Tomato: Mosaic Virus',
        41: 'Tomato: Healthy'}

if not os.path.exists('AgentCropKeras.h5'):
    url='https://drive.google.com/uc?id=1RptBAVHhoGcHydWHkRFpflj3WG8BMDJo'
    output = 'AgentCropKeras.h5'
    gdown.download(url, output, quiet=False)

model = load_model('AgentCropKeras.h5')
if not os.path.exists('./static/test'):
        os.makedirs('./static/test')

def predict(test_dir):
    test_img = [f for f in os.listdir(os.path.join(test_dir)) if not f.startswith(".")]
    test_df = pd.DataFrame({'Image': test_img})
    
    test_gen = ImageDataGenerator(rescale=1./255)

    test_generator = test_gen.flow_from_dataframe(
        test_df, 
        test_dir, 
        x_col = 'Image',
        y_col = None,
        class_mode = None,
        target_size = (150, 150),
        batch_size = 20,
        shuffle = False
    )
    predict = model.predict(test_generator, steps = np.ceil(test_generator.samples/20))
    test_df['Label'] = np.argmax(predict, axis = -1) # axis = -1 --> To compute the max element index within list of lists
    test_df['Label'] = test_df['Label'].replace(disease_map)

    prediction_dict = {}
    for value in test_df.to_dict('index').values():
        prediction_dict[value['Image']] = value['Label']
    return prediction_dict


# Create an app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # maximum upload size is 50 MB
app.secret_key = "agentcrop"
ALLOWED_EXTENSIONS = {'png', 'jpeg', 'jpg'}
folder_num = 0
folders_list = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean():
    global folders_list
    try:
        for folder in folders_list:
            if (time.time() - os.stat(folder).st_ctime) / 3600 > 1:
                shutil.rmtree(folder)
                folders_list.remove(folder)
    except:
        flash("Something Went Wrong! Coudn't delete data!")

@app.route('/', methods=['GET', 'POST'])

def get_disease():
    global folder_num
    global folders_list
    clean()
    if request.method == 'POST':
        if folder_num >= 1000000:
            folder_num = 0
        # check if the post request has the file part
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        # Create a new folder for every new file uploaded,
        # so that concurrency can be mainatained
        files = request.files.getlist('files[]')
        app.config['UPLOAD_FOLDER'] = "./static/test"
        app.config['UPLOAD_FOLDER'] = app.config['UPLOAD_FOLDER'] + '/predict_' + str(folder_num).rjust(6, "0")
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            folders_list.append(app.config['UPLOAD_FOLDER'])
            folder_num += 1
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash("Invalid file type! Only PNG, JPEG/JPG files are supported.")
                return redirect('/')
        try:
            if len(os.listdir(app.config['UPLOAD_FOLDER'])) > 0:
                diseases = predict(app.config['UPLOAD_FOLDER'])
                return render_template('show_prediction.html',
                folder = app.config['UPLOAD_FOLDER'],
                predictions = diseases)
        except:
            flash("Something Went Wrong! Try Refreshing the Page!")
            return redirect('/')
        
    return render_template('index.html')

@app.route('/favicon.ico')

def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static'), 'Agent-Crop-Icon.png')