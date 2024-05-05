from flask import Flask, render_template, request, jsonify
import csv
import random
import os
import base64
from PIL import Image
import google.generativeai as genai
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['STATIC_FOLDER'] = 'static'
WORDLIST_FILE = 'wordlist.csv'

def getword():
    with open(WORDLIST_FILE, 'r') as file:
        words_line = file.readline().strip()
        words = words_line.split(',')
        return random.choice(words).strip()


# Function to check if the uploaded file is allowed
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_word', methods=['POST'])
def get_word():
    random_word = getword()
    return jsonify({'word': random_word})

@app.route('/get_message', methods=['POST'])
def get_message():
    text = request.form['message']
    char_count = len(text)
    return jsonify({'char_count': char_count})

@app.route('/get_hint', methods=['POST'])
def get_hint():
    # Check if the request contains JSON data (from canvas)
    if request.is_json:
        data = request.get_json()
        answer = data.get('answer')
        image_data_url = data.get('image_data_url')
        if image_data_url:
            # Strip the data URL prefix
            image_data = base64.b64decode(image_data_url.split(',')[1])
            imagefile = BytesIO(image_data)
            image = Image.open(imagefile)
            # Save the image data to a file
            filename = os.path.join(app.config['UPLOAD_FOLDER'], 'canvas_image.png')
            response = get_gemini_response(f'The drawer is trying to draw "{answer}". Give a brief tip on how to improve this drawing', image)

            return jsonify({'message': response})
    

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if request.is_json:
        data = request.get_json()
        image_data_url = data.get('image_data_url')
        if image_data_url:
            # Strip the data URL prefix
            image_data = base64.b64decode(image_data_url.split(',')[1])
            imagefile = BytesIO(image_data)
            image = Image.open(imagefile)
            # Save the image data to a file
            filename = os.path.join(app.config['UPLOAD_FOLDER'], 'canvas_image.png')
            response = get_gemini_response("guess what is being drawn. max: 3 word answer", image)
            return jsonify({'message': response})

    # Otherwise, handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # If the file is allowed, save it to the images folder
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'message': 'File successfully uploaded'})

    # If the file extension is not allowed
    return jsonify({'error': 'File type not allowed'})

@app.route('/guess', methods=['POST'])
def confirm_guess():
    answer = request.get_json().get('answer')
    guess = request.get_json().get('guess')
    message=get_ai_response(answer,guess)
    return jsonify({'value': message})

def get_gemini_response(input_text, image):
    try: 
        model = genai.GenerativeModel('gemini-pro-vision')
        if input_text != "":
            response = model.generate_content([input_text, image])
        else:
            response = model.generate_content(image)
        return response.text
    except Exception as e:
        return "i cant guess it"

def get_ai_response(answer,guess):
    prompt = f'The guesser is trying to guess what is in an image. The answer is \'{answer}\'. The guesser has guessed \'{guess}\'. Are they correct? Respond \'true\' or \'false\''
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
