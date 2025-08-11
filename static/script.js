document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const submitButton = uploadForm.querySelector('button');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');
    const stemsContainer = document.getElementById('stems-container');
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');

    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (!fileInput.files.length) {
            alert('Silakan pilih file audio terlebih dahulu.');
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        // Reset UI
        hideError();
        resultsDiv.classList.add('hidden');
        stemsContainer.innerHTML = '';
        statusDiv.classList.remove('hidden');
        submitButton.disabled = true;
        submitButton.textContent = 'Memproses...';

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.details || data.error || 'Terjadi kesalahan yang tidak diketahui.');
            }

            if (data.error) {
                throw new Error(data.error);
            }

            statusDiv.classList.add('hidden');
            displayResults(data.stems);

        } catch (err) {
            showError(`Gagal: ${err.message}`);
            statusDiv.classList.add('hidden');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Pisahkan Audio';
        }
    });

    function displayResults(stems) {
        if (!stems || stems.length === 0) {
            showError('Tidak ada stem audio yang dihasilkan. File mungkin kosong atau formatnya tidak didukung.');
            return;
        }

        stems.forEach(stem => {
            const stemDiv = document.createElement('div');
            stemDiv.className = 'stem';

            const title = document.createElement('h3');
            title.textContent = stem.name;

            const audio = document.createElement('audio');
            audio.controls = true;
            audio.src = stem.path;

            stemDiv.appendChild(title);
            stemDiv.appendChild(audio);
            stemsContainer.appendChild(stemDiv);
        });

        resultsDiv.classList.remove('hidden');
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    function hideError() {
        errorDiv.classList.add('hidden');
    }
});
