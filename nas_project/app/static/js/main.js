// Storage Usage Warning
class StorageMonitor {
    constructor() {
        this.progressBar = document.querySelector('.storage-progress');
        this.checkStorage();
    }

    checkStorage() {
        if (this.progressBar) {
            const usage = parseInt(this.progressBar.getAttribute('aria-valuenow'));
            if (usage >= 90) {
                this.showStorageWarning('critical');
            } else if (usage >= 75) {
                this.showStorageWarning('warning');
            }
        }
    }

    showStorageWarning(level) {
        const message = level === 'critical' ? 
            'Storage space is critically low!' : 
            'Storage space is running low.';
            
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${level === 'critical' ? 'danger' : 'warning'} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                    <button class="btn btn-sm btn-light ms-2" 
                            data-bs-toggle="modal" 
                            data-bs-target="#storageRequestModal">
                        Request More
                    </button>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.querySelector('.toast-container') || 
            (() => {
                const cont = document.createElement('div');
                cont.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(cont);
                return cont;
            })();
            
        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// File Search and Filter
class FileManager {
    constructor() {
        this.searchInput = document.querySelector('#fileSearch');
        this.categoryFilter = document.querySelector('#categoryFilter');
        this.fileTable = document.querySelector('#filesTable tbody');
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.filterFiles());
        }
        if (this.categoryFilter) {
            this.categoryFilter.addEventListener('change', () => this.filterFiles());
        }
    }

    filterFiles() {
        if (!this.fileTable) return;
        
        const searchTerm = this.searchInput.value.toLowerCase();
        const category = this.categoryFilter.value.toLowerCase();
        const rows = this.fileTable.getElementsByTagName('tr');

        Array.from(rows).forEach(row => {
            if (row.cells.length < 2) return; // Skip if not enough cells (might be empty state row)
            
            const fileName = row.cells[0].textContent.toLowerCase();
            const fileCategory = row.cells[1].textContent.toLowerCase();
            const matchesSearch = fileName.includes(searchTerm);
            const matchesCategory = !category || fileCategory.includes(category);
            row.style.display = matchesSearch && matchesCategory ? '' : 'none';
        });
    }
}

// Drag and Drop functionality 
class DragDropHandler {
    constructor() {
        this.uploadZone = document.querySelector('.upload-zone');
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (!this.uploadZone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, this.preventDefaults);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, () => {
                this.uploadZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, () => {
                this.uploadZone.classList.remove('dragover');
            });
        });

        this.uploadZone.addEventListener('drop', (e) => {
            this.preventDefaults(e);
            const files = e.dataTransfer.files;
            
            if (files.length > 0) {
                // Trigger file upload modal
                const uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
                if (uploadModal) {
                    uploadModal.show();
                    // Let the user know they need to select the file in the modal
                    alert("Please select the file using the file input in the upload dialog.");
                }
            }
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
}

// Global utilities
// Direct modal setup without additional wrapper function
function setupDeleteModal() {
    // Get the delete modal element
    const deleteModal = document.getElementById('deleteModal');
    if (!deleteModal) return;
    
    // When the modal is shown, set up the delete file ID
    deleteModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        if (!button) return;
        
        const fileId = button.getAttribute('data-file-id');
        const filename = button.getAttribute('data-filename');
        
        // Update the modal content
        const fileNameElement = document.getElementById('deleteFileName');
        if (fileNameElement) {
            fileNameElement.textContent = filename || 'this file';
        }
        
        // Set up the confirm button
        const confirmDeleteBtn = document.getElementById('confirmDelete');
        if (confirmDeleteBtn) {
            // Remove any existing event listeners
            const newBtn = confirmDeleteBtn.cloneNode(true);
            confirmDeleteBtn.parentNode.replaceChild(newBtn, confirmDeleteBtn);
            
            // Add fresh event listener
            newBtn.addEventListener('click', function() {
                // Disable the button and show loading state
                newBtn.disabled = true;
                newBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';
                
                deleteFile(fileId, deleteModal);
            });
        }
    });
}

function deleteFile(fileId, modalElement) {
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
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Delete response data:", data);
        
        // Hide modal if present
        if (modalElement) {
            const bsModal = bootstrap.Modal.getInstance(modalElement);
            if (bsModal) {
                bsModal.hide();
            } else {
                // If the Bootstrap instance isn't found, try to hide it manually
                $(modalElement).modal('hide'); // Using jQuery if available
            }
        }
        
        // Show success message
        showNotification('success', 'File deleted successfully');
        
        // Reload page after a short delay
        setTimeout(() => {
            window.location.reload();
        }, 500);
    })
    .catch(error => {
        // Reset any delete button
        const confirmBtn = document.getElementById('confirmDelete');
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Delete';
        }
        
        console.error('Error during delete:', error);
        showNotification('error', error.message || 'Delete failed. Please try again.');
    });
}

// Notification function for general purpose messages
function showNotification(type, message) {
    const toastContainer = document.querySelector('.toast-container') || 
        (() => {
            const cont = document.createElement('div');
            cont.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(cont);
            return cont;
        })();
        
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Handle tag-related UI interactions
function setupTagInteractions() {
    // Tag Modal Handler
    const tagModal = document.getElementById('tagModal');
    if (tagModal) {
        tagModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const fileId = button.getAttribute('data-file-id');
            const filename = button.getAttribute('data-filename');
            
            const fileNameElement = document.getElementById('tagFileName');
            const fileIdInput = document.getElementById('tagFileId');
            
            if (fileNameElement) fileNameElement.textContent = filename;
            if (fileIdInput) fileIdInput.value = fileId;
            
            // Clear all checkboxes first
            document.querySelectorAll('.tag-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
            
            // Get current tags for the file
            fetch(`/files/get-tags/${fileId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.tags) {
                        data.tags.forEach(tagId => {
                            const checkbox = document.getElementById(`tag_modal_${tagId}`);
                            if (checkbox) checkbox.checked = true;
                        });
                    }
                })
                .catch(error => console.error('Error fetching tags:', error));
        });
        
        // Save tags button
        const saveTagsBtn = document.getElementById('saveTagsBtn');
        if (saveTagsBtn) {
            saveTagsBtn.addEventListener('click', function() {
                const fileId = document.getElementById('tagFileId').value;
                const form = document.getElementById('tagForm');
                
                if (form && fileId) {
                    const formData = new FormData(form);
                    
                    fetch(`/files/tag/${fileId}`, {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        const modal = bootstrap.Modal.getInstance(tagModal);
                        if (modal) modal.hide();
                        
                        if (data.message) {
                            showNotification('success', 'Tags updated successfully');
                            // Reload page to reflect changes
                            setTimeout(() => window.location.reload(), 500);
                        } else {
                            throw new Error(data.error || 'Failed to update tags');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showNotification('error', error.message || 'Error updating tags');
                    });
                }
            });
        }
    }
}

// Initialize all components
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded - initializing components");
    
    // Initialize our custom components
    new StorageMonitor();
    new FileManager();
    new DragDropHandler();
    
    // Set up tag interactions
    setupTagInteractions();
    
    // Set up delete modal handling
    setupDeleteModal();
    
    // Initialize Bootstrap components
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => new bootstrap.Popover(popover));
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {
                // Alert might have been already closed or removed
                console.log("Could not auto-close alert:", e);
            }
        }, 5000);
    });
});

// Format file size utility function
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}