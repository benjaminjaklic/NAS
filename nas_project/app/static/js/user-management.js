let userIdToDelete = null;
let deleteUserModal = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the modal
    deleteUserModal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
    
    // Add event listeners
    document.getElementById('confirmDeleteUser')?.addEventListener('click', handleUserDeletion);
    document.getElementById('deleteUserModal')?.addEventListener('hidden.bs.modal', handleModalHidden);
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

function deleteUser(userId, event) {
    event.preventDefault();
    const button = event.target.closest('button');
    const username = button.dataset.username;
    
    userIdToDelete = userId;
    document.getElementById('deleteUsername').textContent = username;
    
    deleteUserModal.show();
}

async function handleUserDeletion() {
    const confirmButton = document.getElementById('confirmDeleteUser');
    const spinner = '<span class="spinner-border spinner-border-sm me-2"></span>';
    
    try {
        // Disable the button and show loading state
        confirmButton.disabled = true;
        confirmButton.innerHTML = spinner + 'Deleting...';
        
        console.log('Attempting to delete user:', userIdToDelete);
        
        const response = await fetch(`/admin/users/delete/${userIdToDelete}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        console.log('Response:', response);
        const data = await response.json();
        console.log('Data:', data);
        
        if (response.ok) {
            // Hide modal
            deleteUserModal.hide();
            
            // Show success notification
            showNotification('success', data.message);
            
            // Remove the user's row from the table with animation
            const userRow = document.querySelector(`button[onclick="deleteUser(${userIdToDelete}, event)"]`)
                .closest('tr');
            userRow.style.transition = 'opacity 0.5s';
            userRow.style.opacity = '0';
            setTimeout(() => userRow.remove(), 500);
        } else {
            // Show error in modal
            showModalError(data.error || 'Error deleting user');
        }
    } catch (error) {
        console.error('Error:', error);
        showModalError('Error deleting user. Please try again.');
    } finally {
        // Reset button state
        confirmButton.disabled = false;
        confirmButton.innerHTML = '<i class="fas fa-trash me-1"></i>Delete User';
    }
}

function handleModalHidden() {
    // Clear any error messages when modal is hidden
    clearModalError();
    
    // Reset the button state just in case
    const confirmButton = document.getElementById('confirmDeleteUser');
    confirmButton.disabled = false;
    confirmButton.innerHTML = '<i class="fas fa-trash me-1"></i>Delete User';
}

function showModalError(message) {
    clearModalError();
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger mt-3 mb-0';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
    document.querySelector('.modal-body').appendChild(errorDiv);
}

function clearModalError() {
    const errorDiv = document.querySelector('#deleteUserModal .alert-danger');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function showNotification(type, message) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the card body
    const cardBody = document.querySelector('.card-body');
    cardBody.insertBefore(notification, cardBody.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = bootstrap.Alert.getOrCreateInstance(notification);
        alert.close();
    }, 5000);
}