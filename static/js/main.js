// Close flash messages
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Close button for flash messages
    document.querySelectorAll('.close-flash').forEach(function(button) {
        button.addEventListener('click', function() {
            const message = this.parentElement;
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                message.remove();
            }, 300);
        });
    });

    // Auto-resize textarea
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });

    // Confirm delete with custom message
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this journal entry? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Toggle visibility via AJAX
    const visibilityToggles = document.querySelectorAll('.toggle-visibility');
    visibilityToggles.forEach(function(toggle) {
        toggle.addEventListener('click', async function(e) {
            e.preventDefault();
            const journalId = this.dataset.journalId;
            
            try {
                const response = await fetch(`/api/journal/${journalId}/toggle-visibility`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const badge = this.querySelector('.visibility-badge');
                    if (data.is_public) {
                        badge.textContent = '🌍 Public';
                        badge.classList.remove('private');
                        badge.classList.add('public');
                    } else {
                        badge.textContent = '🔒 Private';
                        badge.classList.remove('public');
                        badge.classList.add('private');
                    }
                }
            } catch (error) {
                console.error('Error toggling visibility:', error);
            }
        });
    });

    // Word count for textarea
    const contentTextarea = document.getElementById('content');
    if (contentTextarea) {
        const wordCountDisplay = document.createElement('div');
        wordCountDisplay.className = 'word-count';
        wordCountDisplay.style.cssText = 'text-align: right; color: var(--text-muted); font-size: 0.85rem; margin-top: 0.5rem;';
        contentTextarea.parentElement.appendChild(wordCountDisplay);

        function updateWordCount() {
            const text = contentTextarea.value.trim();
            const words = text ? text.split(/\s+/).length : 0;
            const chars = text.length;
            wordCountDisplay.textContent = `${words} words · ${chars} characters`;
        }

        contentTextarea.addEventListener('input', updateWordCount);
        updateWordCount();
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to save (when in form)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            const form = document.querySelector('.journal-form');
            if (form) {
                e.preventDefault();
                form.submit();
            }
        }

        // Escape to go back
        if (e.key === 'Escape') {
            const backBtn = document.querySelector('a.btn-secondary[href*="dashboard"], a.btn-secondary[href*="public"]');
            if (backBtn && !document.activeElement.matches('input, textarea')) {
                window.location.href = backBtn.href;
            }
        }
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Dark mode is default, but you can add a toggle if needed
function toggleTheme() {
    document.body.classList.toggle('light-mode');
    localStorage.setItem('theme', document.body.classList.contains('light-mode') ? 'light' : 'dark');
}

// Check for saved theme preference
if (localStorage.getItem('theme') === 'light') {
    document.body.classList.add('light-mode');
}
