// Admin dashboard Javascript operations
const uploadZone = document.getElementById('upload-zone');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const statusText = document.getElementById('upload-status');

if (uploadZone) {
    // Add dragover, dragenter, dragleave, drop event listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, e => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--primary)';
            uploadZone.style.backgroundColor = 'var(--bg-card-hover)';
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, e => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--border-color)';
            uploadZone.style.backgroundColor = 'transparent';
        }, false);
    });

    uploadZone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });
}

function handleFileSelect(event) {
    const files = event.target.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length === 0) return;
    
    // Show progress bar
    progressContainer.style.display = 'block';
    statusText.style.display = 'block';
    statusText.innerText = `Preparing upload for ${files.length} photos...`;
    progressBar.style.width = '0%';

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/admin/galleries/${GALLERY_ID}/upload`, true);

    // Track upload progress
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = percentComplete + '%';
            statusText.innerText = `Uploading photos: ${percentComplete}% completed`;
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            if (data.status === 'success') {
                statusText.innerText = 'Upload completed successfully! Reloading gallery...';
                progressBar.style.width = '100%';
                
                // Reload page after short delay to show uploaded photos
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                statusText.innerText = 'Error: ' + (data.error || 'Unknown error occurred.');
                progressBar.style.backgroundColor = 'var(--accent)';
            }
        } else {
            statusText.innerText = 'Failed to upload files. Server error occurred.';
            progressBar.style.backgroundColor = 'var(--accent)';
        }
    };

    xhr.onerror = function() {
        statusText.innerText = 'Error connection timed out or blocked.';
        progressBar.style.backgroundColor = 'var(--accent)';
    };

    xhr.send(formData);
}

// Selection Export Modal operations
function exportSelections() {
    const listArea = document.getElementById('export-list');
    listArea.value = selectedFilenames.join('\n');
    toggleExportModal(true);
}

function toggleExportModal(show) {
    document.getElementById('export-modal').style.display = show ? 'flex' : 'none';
}

function copyExportText() {
    const listArea = document.getElementById('export-list');
    listArea.select();
    navigator.clipboard.writeText(listArea.value)
    .then(() => {
        alert('Selections copied to clipboard!');
        toggleExportModal(false);
    })
    .catch(err => console.error('Failed to copy selections:', err));
}
