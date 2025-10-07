document.addEventListener('DOMContentLoaded', function() {
    // Initialize file upload form
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            uploadFile();
        });
    }

    // Initialize delete modal
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        let fileIdToDelete = null;

        deleteModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            fileIdToDelete = button.getAttribute('data-file-id');
            const filename = button.getAttribute('data-filename');
            const fileNameElement = document.getElementById('deleteFileName');
            if (fileNameElement) {
                fileNameElement.textContent = filename;
            }
        });

        const confirmDeleteButton = document.getElementById('confirmDelete');
        if (confirmDeleteButton) {
            confirmDeleteButton.addEventListener('click', function() {
                if (fileIdToDelete) {
                    deleteFile(fileIdToDelete);
                }
            });
        }
    }
});

function uploadFile() {
    const fileInput = document.querySelector('#uploadForm input[type="file"]');
    const categorySelect = document.querySelector('#uploadForm select[name="category"]');
    const progressBar = document.querySelector('.upload-progress-bar');
    const progressText = document.querySelector('.upload-progress-text');
    const uploadModal = document.getElementById('uploadModal');
    const uploadButton = document.querySelector('.upload-btn');
    const form = document.getElementById('uploadForm');

    if (!fileInput || !fileInput.files.length) {
        alert('Please select a file first.');
        return;
    }

    // Disable form elements during upload
    if (uploadButton) uploadButton.disabled = true;
    if (fileInput) fileInput.disabled = true;
    if (categorySelect) categorySelect.disabled = true;
    if (uploadButton) uploadButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';

    const formData = new FormData(form);
    const file = fileInput.files[0];
    console.log(`Starting upload of ${file.name} (${formatFileSize(file.size)})`);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/files/upload', true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    // Add event listeners for progress updates
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable && progressBar && progressText) {
            const percent = (e.loaded / e.total) * 100;
            progressBar.style.width = percent + '%';
            progressText.textContent = Math.round(percent) + '%';
            
            // Log progress to console for debugging
            console.log(`Upload progress: ${Math.round(percent)}% (${formatFileSize(e.loaded)} of ${formatFileSize(e.total)})`);
            
            // Update upload speed and time estimate if these elements exist
            const speedSpan = document.querySelector('.upload-speed');
            const timeSpan = document.querySelector('.upload-time');
            const sizeSpan = document.querySelector('.upload-size');
            
            if (speedSpan && timeSpan && sizeSpan) {
                // Calculate upload speed
                const currentTime = new Date().getTime();
                const elapsedTime = (currentTime - uploadStartTime) / 1000; // in seconds
                const speed = e.loaded / elapsedTime; // bytes per second
                
                // Update displayed info
                speedSpan.textContent = `${formatFileSize(speed)}/s`;
                sizeSpan.textContent = `${formatFileSize(e.loaded)} / ${formatFileSize(e.total)}`;
                
                // Calculate time remaining
                const remaining = e.total - e.loaded;
                const timeRemaining = remaining / speed; // seconds
                timeSpan.textContent = `Time remaining: ${formatTime(timeRemaining)}`;
            }
        }
    };

    // Track upload start time
    const uploadStartTime = new Date().getTime();

    xhr.upload.onloadstart = function() {
        console.log("Upload started");
    };

    xhr.upload.onloadend = function() {
        console.log("Upload finished");
    };

    xhr.onload = function() {
        console.log(`Server response status: ${xhr.status}`);
        console.log(`Server response text: ${xhr.responseText}`);
        
        if (xhr.status === 200) {
            try {
                // Parse the JSON response
                const response = JSON.parse(xhr.responseText);
                console.log("JSON response:", response);

                // Update UI for success
                if (progressBar) {
                    progressBar.classList.remove('bg-danger');
                    progressBar.classList.add('bg-success');
                    progressBar.style.width = '100%';
                }
                if (progressText) {
                    progressText.textContent = '100%';
                }
                
                // Close modal and reset after delay
                setTimeout(function() {
                    const bsModal = bootstrap.Modal.getInstance(uploadModal);
                    if (bsModal) bsModal.hide();
                    
                    // Reset form and progress
                    if (form) form.reset();
                    if (progressBar) {
                        progressBar.style.width = '0%';
                        progressBar.classList.remove('bg-success');
                    }
                    if (progressText) progressText.textContent = '0%';
                    
                    // Re-enable form elements
                    if (uploadButton) {
                        uploadButton.disabled = false;
                        uploadButton.innerHTML = 'Upload';
                    }
                    if (fileInput) fileInput.disabled = false;
                    if (categorySelect) categorySelect.disabled = false;
                    
                    // Refresh page to show new file
                    window.location.reload();
                }, 1000);
            } catch (e) {
                console.error("Error parsing JSON response:", e);
                window.location.reload(); // Fallback to reloading the page
            }
        } else {
            // Error case
            if (progressBar) progressBar.classList.add('bg-danger');
            let errorMsg = 'Upload failed';
            try {
                const response = JSON.parse(xhr.responseText);
                errorMsg = response.error || errorMsg;
            } catch (e) {
                errorMsg = xhr.responseText || errorMsg;
            }
            alert(errorMsg);
            
            // Re-enable form elements
            if (uploadButton) {
                uploadButton.disabled = false;
                uploadButton.innerHTML = 'Upload';
            }
            if (fileInput) fileInput.disabled = false;
            if (categorySelect) categorySelect.disabled = false;
        }
    };

    xhr.onerror = function() {
        console.log("XHR error occurred");
        if (progressBar) progressBar.classList.add('bg-danger');
        alert('Network error occurred. Please try again.');
        
        // Re-enable form elements
        if (uploadButton) {
            uploadButton.disabled = false;
            uploadButton.innerHTML = 'Upload';
        }
        if (fileInput) fileInput.disabled = false;
        if (categorySelect) categorySelect.disabled = false;
    };

    xhr.ontimeout = function() {
        console.log("XHR request timed out");
        if (progressBar) progressBar.classList.add('bg-danger');
        alert('Request timed out. Please try again.');
        
        // Re-enable form elements
        if (uploadButton) {
            uploadButton.disabled = false;
            uploadButton.innerHTML = 'Upload';
        }
        if (fileInput) fileInput.disabled = false;
        if (categorySelect) categorySelect.disabled = false;
    };

    // Set a longer timeout for large files (5 minutes)
    xhr.timeout = 300000;

    // Start upload
    try {
        xhr.send(formData);
        console.log("XHR request sent");
    } catch (error) {
        console.error("Error sending XHR request:", error);
        alert('Error starting upload: ' + error.message);
        
        // Re-enable form elements
        if (uploadButton) {
            uploadButton.disabled = false;
            uploadButton.innerHTML = 'Upload';
        }
        if (fileInput) fileInput.disabled = false;
        if (categorySelect) categorySelect.disabled = false;
    }
}

function deleteFile(fileId) {
    console.log("Deleting file with ID:", fileId);
    fetch(`/files/delete/${fileId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        console.log("Delete response status:", response.status);
        return response.json();
    })
    .then(data => {
        console.log("Delete response data:", data);
        const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
        if (deleteModal) deleteModal.hide();
        
        if (data.message) {
            // Success case
            window.location.reload();
        } else {
            throw new Error(data.error || 'Delete failed');
        }
    })
    .catch(error => {
        console.error('Error during delete:', error);
        alert(error.message || 'Delete failed. Please try again.');
    });
}

// Format file size for display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format time in seconds to hh:mm:ss
function formatTime(seconds) {
    seconds = Math.ceil(seconds);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    const parts = [];
    if (h > 0) parts.push(`${h}h`);
    if (m > 0 || h > 0) parts.push(`${m}m`);
    parts.push(`${s}s`);
    
    return parts.join(' ');
}