// Main JavaScript for Flask Task Scheduler

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            const closeButton = message.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Fix for delete modal issues - use a single modal
    const deleteButtons = document.querySelectorAll('.delete-btn');
    const deleteModal = document.getElementById('deleteTaskModal');

    if (deleteButtons.length > 0 && deleteModal) {
        const deleteForm = document.getElementById('deleteTaskForm');
        const deleteTaskTitle = document.getElementById('deleteTaskTitle');
        const bsDeleteModal = new bootstrap.Modal(deleteModal);

        deleteButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Get task data from data attributes
                const taskId = this.getAttribute('data-task-id');
                const taskTitle = this.getAttribute('data-task-title');

                // Update the modal with task details
                deleteTaskTitle.textContent = taskTitle;
                deleteForm.action = `/tasks/${taskId}/delete`;

                // Show the modal
                bsDeleteModal.show();
            });
        });
    }

    // Enhance form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Handle estimated hours input to ensure it's in 0.5 increments
    const hoursInput = document.getElementById('estimated_hours');
    if (hoursInput) {
        hoursInput.addEventListener('change', function() {
            const value = parseFloat(this.value);
            if (!isNaN(value)) {
                // Round to nearest 0.5
                this.value = Math.round(value * 2) / 2;
                // Ensure minimum of 0.5
                if (this.value < 0.5) {
                    this.value = 0.5;
                }
            }
        });
    }

    // Show motivational quotes randomly
    const quotes = [
        "The secret of getting ahead is getting started. – Mark Twain",
        "Don't wish it were easier, wish you were better. – Jim Rohn",
        "Education is the most powerful weapon which you can use to change the world. – Nelson Mandela",
        "The beautiful thing about learning is that no one can take it away from you. – B.B. King",
        "The more that you read, the more things you will know. The more that you learn, the more places you'll go. – Dr. Seuss",
        "The expert in anything was once a beginner. – Helen Hayes",
        "Learn from yesterday, live for today, hope for tomorrow. – Albert Einstein"
    ];

    const quoteContainer = document.getElementById('motivational-quote');
    if (quoteContainer) {
        const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
        quoteContainer.textContent = randomQuote;
    }

    // Add confirmation for task completion
    const completeButtons = document.querySelectorAll('.task-complete-btn');
    completeButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm('Mark this task as complete? This will update the task status.')) {
                event.preventDefault();
            }
        });
    });

    // Date validation for log form
    const logDateInput = document.getElementById('log_date');
    if (logDateInput) {
        // Get today's date in YYYY-MM-DD format
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const todayFormatted = `${yyyy}-${mm}-${dd}`;

        // Prevent future dates
        logDateInput.setAttribute('max', todayFormatted);

        logDateInput.addEventListener('change', function() {
            if (this.value > todayFormatted) {
                alert('Cannot log hours for future dates!');
                this.value = todayFormatted;
            }
        });
    }

    // Toggle task description expansion
    const taskDescriptionToggles = document.querySelectorAll('.task-description-toggle');
    taskDescriptionToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const descriptionElement = document.getElementById(this.dataset.target);
            if (descriptionElement) {
                descriptionElement.classList.toggle('d-none');

                // Toggle the icon
                const icon = this.querySelector('i');
                if (icon) {
                    if (icon.classList.contains('fa-chevron-down')) {
                        icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                    } else {
                        icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                    }
                }
            }
        });
    });
});