import os
import shutil
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import subprocess

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diunggah'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        output_path = app.config['OUTPUT_FOLDER']

        # Perintah Demucs
        demucs_command = [
            'python3', '-m', 'demucs',
            '--out', output_path,
            filepath
        ]

        try:
            result = subprocess.run(demucs_command, check=True, capture_output=True, text=True)
            print("Output Demucs:", result.stdout)
        except subprocess.CalledProcessError as e:
            print("Error Demucs:", e.stderr)
            return jsonify({'error': 'Gagal memproses file audio.', 'details': e.stderr}), 500
        except FileNotFoundError:
            print("Perintah Demucs tidak ditemukan.")
            return jsonify({'error': 'Perintah Demucs tidak ditemukan. Pastikan demucs terinstal.'}), 500

        # Cari file output
        filename_without_ext = os.path.splitext(filename)[0]
        # Jalur output demucs default adalah <output_path>/htdemucs/<filename_without_ext>/
        processed_folder = os.path.join(output_path, 'htdemucs', filename_without_ext)

        stems = []
        if os.path.exists(processed_folder):
            for stem_file in sorted(os.listdir(processed_folder)):
                if stem_file.endswith('.wav'):
                    stems.append({
                        'name': os.path.splitext(stem_file)[0].capitalize(),
                        'path': f'/output/htdemucs/{filename_without_ext}/{stem_file}'
                    })
        else:
            return jsonify({'error': 'Tidak dapat menemukan file yang diproses. Demucs mungkin gagal secara diam-diam.'}), 500

        return jsonify({'stems': stems})

    return jsonify({'error': 'Tipe file tidak diizinkan'}), 400

# Rute baru untuk menyajikan file dari subdirektori dinamis demucs
@app.route('/output/htdemucs/<path:folder>/<path:filename>')
def serve_demucs_output_file(folder, filename):
    directory = os.path.join(app.config['OUTPUT_FOLDER'], 'htdemucs', folder)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
