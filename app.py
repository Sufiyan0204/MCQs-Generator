from flask import Flask,request,render_template,send_file
import os
import pdfplumber
import docx
import csv
from werkzeug.utils import secure_filename
import google.generativeai as genai
from fpdf import FPDF



os.environ["GOOGLE_API_KEY"]="AIzaSyDZrGXWHo81KY0wgu8SJSHsT_XH4xQoGzs"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model=genai.GenerativeModel('models/gemini-1.5-pro')


app=Flask(__name__)


app.config['UPLOAD_FOLDER']='uploads/'
app.config['RESULTS_FOLDER']='results/'
app.config['ALLOWED_EXTENSIONS']={'pdf','txt','docx'}


#custom function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_file(file_path):
    ext=file_path.rsplit('.',1)[1].lower()
    if ext=='pdf':
        with pdfplumber.open(file_path) as pdf:
            text=''.join([page.extract_text() for page in pdf.pages])
        return text
    elif ext=='docx':
        doc=docx.Document(file_path)
        text=''.join([para.text for para in doc.paragraphs])
        return text
    elif ext=='txt':
        with open(file_path,'r') as file:
            return file.read()
    return None

def Questions_mcqs_Generator(input_text,number_of_questions):
    prompt=f"""Generate {number_of_questions} number of multiple-choice questions (MCQs) from the given text {input_text}. Each question should have:
            - A clear and concise question statement.
            - Four labeled answer options (A, B, C, D).
            - The correct answer explicitly mentioned.
            Format the output as:
            
            #1. Question: [Question text]
            A) [Option 1]
            B) [Option 2]
            C) [Option 3]
            D) [Option 4]
            Correct Answer: [A/B/C/D]"""
    response=model.generate_content(prompt).text.strip()
    return response

def save_mcqs_to_file(mcqs, filename):
    results_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    with open(results_path, 'w') as f:
        f.write(mcqs)
    return results_path

def create_pdf(mcqs, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for mcq in mcqs.split("#"):
        if mcq.strip():
            pdf.multi_cell(0, 10, mcq.strip())
            pdf.ln(5)  # Add a line break

    pdf_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    pdf.output(pdf_path)
    return pdf_path

#routes
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/generate",methods=['POST'])
def generate_mcqs():
    if 'file' not in request.files:
        return 'no file part'
    file=request.files['file']
    
    if file and allowed_file(file.filename):
        filename=secure_filename(file.filename)
        file_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
        file.save(file_path)

        text=extract_text_from_file(file_path)
        #print(text)
        if text:
            number_of_questions=int(request.form['number_of_questions'])
            mcqs=Questions_mcqs_Generator(text,number_of_questions)
            # Save the generated MCQs to a file
            txt_filename = f"generated_mcqs_{filename.rsplit('.', 1)[0]}.txt"
            pdf_filename = f"generated_mcqs_{filename.rsplit('.', 1)[0]}.pdf"
            save_mcqs_to_file(mcqs, txt_filename)
            create_pdf(mcqs, pdf_filename)

            # Display and allow downloading
            return render_template('results.html', mcqs=mcqs, txt_filename=txt_filename, pdf_filename=pdf_filename)
            #print("\n\n",mcqs)
        return "Invalid file format"


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__=='__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['RESULTS_FOLDER']):
        os.makedirs(app.config['RESULTS_FOLDER'])
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000)

