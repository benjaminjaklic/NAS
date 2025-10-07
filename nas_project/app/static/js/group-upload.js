class GroupFileUploader {
    constructor(groupId) {
        this.groupId = groupId;
        this.uploadZone = document.querySelector('.group-upload-zone');
        this.progressBar = document.querySelector('.upload-progress');
        this.uploadQueue = [];
        this.maxConcurrentUploads = 3;
        this.activeUploads = 0;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.uploadZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                this.uploadZone.addEventListener(eventName, this.preventDefaults);
            });

            this.uploadZone.addEventListener('drop', this.handleDrop.bind(this));
            this.uploadZone.addEventListener('dragenter', this.highlight.bind(this));
            this.uploadZone.addEventListener('dragleave', this.unhighlight.bind(this));
        }

        // File input change handler
        const fileInput = document.querySelector('#groupFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFiles(e.target.files);
            });
        }
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight() {
        this.uploadZone.classList.add('dragover');
    }

    unhighlight() {
        this.uploadZone.classList.remove('dragover');
    }

    handleDrop(e) {
        const files = e.dataTransfer.files;
        this.handleFiles(files);
    }

    handleFiles(files) {
        Array.from(files).forEach(file => {
            this.uploadQueue.push(file);
        });
        this.processQueue();
    }

    async processQueue() {
        while (this.uploadQueue.length > 0 && this.activeUploads < this.maxConcurrentUploads) {
            const file = this.uploadQueue.shift();
            this.activeUploads++;
            await this.uploadFile(file);
            this.activeUploads--;
        }

        if (this.uploadQueue.length === 0 && this.activeUploads === 0) {
            this.onAllUploadsComplete();
        }
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('group_id', this.groupId);

        // Create progress element
        const progressItem = this.createProgressItem(file.name);
        
        try {
            const response = await fetch('/groups/upload', {
                method: 'POST',
                body: formData,
                onUploadProgress: (progressEvent) => {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    this.updateProgress(progressItem, percentCompleted);
                }
            });

            if (response.ok) {
                this.updateProgress(progressItem, 100, 'success');
                this.showNotification(`${file.name} uploaded successfully`, 'success');
            } else {
                this.updateProgress(progressItem, 0, 'error');
                this.showNotification(`Failed to upload ${file.name}`, 'error');
            }
        } catch (error) {
            this.updateProgress(progressItem, 0, 'error');
            this.showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
        }
    }

    createProgressItem(fileName) {
        const progressContainer = document.querySelector('.upload-progress-container');
        const item = document.createElement('div');
        item.className = 'upload-progress-item mb-2';
        item.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">
                    <small>${fileName}</small>
                    <div class="progress" style="height: 5px;">
                        <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                    </div>
                </div>
                <button type="button" class="btn-close ms-2" style="scale: 0.8;"></button>
            </div>
        `;
        progressContainer.appendChild(item);
        return item;
    }

    updateProgress(progressItem, percent, status = '') {
        const progressBar = progressItem.querySelector('.progress-bar');
        progressBar.style.width = `${percent}%`;
        
        if (status === 'success') {
            progressBar.classList.add('bg-success');
            setTimeout(() => progressItem.remove(), 2000);
        } else if (status === 'error') {
            progressBar.classList.add('bg-danger');
        }
    }

    showNotification(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
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

    onAllUploadsComplete() {
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}