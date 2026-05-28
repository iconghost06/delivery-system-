// Global client gallery variables
let currentFilter = 'all';

// Toggle favorite status asynchronously
function toggleFavorite(button, photoId) {
    const formData = new FormData();
    formData.append('photo_id', photoId);

    fetch(`/api/gallery/${GALLERY_HASH}/favorite`, {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        const item = document.querySelector(`.gallery-item[data-photo-id="${photoId}"]`);
        
        if (data.status === 'added') {
            button.classList.add('favorited');
            item.setAttribute('data-is-fav', 'true');
        } else {
            button.classList.remove('favorited');
            item.setAttribute('data-is-fav', 'false');
            
            // If we are currently viewing only favorites, hide this item immediately
            if (currentFilter === 'favs') {
                item.style.display = 'none';
            }
        }
        
        updateCounts();
    })
    .catch(err => console.error('Error toggling favorite:', err));
}

// Update selections counts in the UI
function updateCounts() {
    const favoriteItems = document.querySelectorAll('.gallery-item[data-is-fav="true"]');
    const favCount = favoriteItems.length;
    
    // Update header tabs and summary floating bar
    document.getElementById('fav-count-header').innerText = favCount;
    document.getElementById('fav-count-floating').innerText = favCount;
    
    // Toggle displays for floating bars and download buttons
    const summaryBar = document.getElementById('summary-bar');
    const downloadFavsBtn = document.getElementById('btn-download-favs');
    
    if (favCount > 0) {
        summaryBar.style.display = 'flex';
        if (downloadFavsBtn) downloadFavsBtn.style.display = 'inline-block';
    } else {
        summaryBar.style.display = 'none';
        if (downloadFavsBtn) downloadFavsBtn.style.display = 'none';
    }
}

// Filter grid items
function setFilter(filter) {
    currentFilter = filter;
    
    document.getElementById('tab-all').classList.toggle('active', filter === 'all');
    document.getElementById('tab-favs').classList.toggle('active', filter === 'favs');
    
    const items = document.querySelectorAll('.gallery-item');
    items.forEach(item => {
        if (filter === 'all') {
            item.style.display = 'block';
        } else {
            const isFav = item.getAttribute('data-is-fav') === 'true';
            item.style.display = isFav ? 'block' : 'none';
        }
    });
}

// Lightbox Modal functions
function openLightbox(photoId, src, name) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const caption = document.getElementById('lightbox-caption');
    
    img.src = src;
    caption.innerText = name;
    lightbox.style.display = 'flex';
}

function closeLightbox(event) {
    if (!event || event.target === document.getElementById('lightbox') || event.target.tagName === 'SPAN') {
        document.getElementById('lightbox').style.display = 'none';
    }
}

// Comments side drawer functions
function openCommentDrawer(photoId, src, name) {
    const drawer = document.getElementById('comments-drawer');
    document.getElementById('drawer-preview-img').src = src;
    document.getElementById('drawer-preview-filename').innerText = name;
    document.getElementById('comment-photo-id').value = photoId;
    
    renderDrawerComments(photoId);
    drawer.classList.add('open');
}

function closeCommentDrawer() {
    document.getElementById('comments-drawer').classList.remove('open');
}

// Render comments list in drawer
function renderDrawerComments(photoId) {
    const list = document.getElementById('drawer-comments-list');
    list.innerHTML = '';
    
    const comments = initialComments[photoId] || [];
    
    if (comments.length === 0) {
        list.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; font-style: italic;">No layout notes yet.</p>';
        return;
    }
    
    comments.forEach(c => {
        const item = document.createElement('div');
        item.className = 'comment-item';
        item.innerHTML = `
            <div class="comment-meta">
                <span class="comment-author">${c.author}</span>
                <span>${c.timestamp}</span>
            </div>
            <div class="comment-text" style="font-size: 0.9rem; color: var(--text-secondary);">${c.text}</div>
        `;
        list.appendChild(item);
    });
}

// Submit new comment/layout note
function submitComment(event) {
    event.preventDefault();
    
    const photoId = document.getElementById('comment-photo-id').value;
    const author = document.getElementById('comment-author').value;
    const text = document.getElementById('comment-text').value;
    
    const formData = new FormData();
    formData.append('photo_id', photoId);
    formData.append('author', author);
    formData.append('text', text);
    
    fetch(`/api/gallery/${GALLERY_HASH}/comment`, {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            // Add comment to locally held array
            if (!initialComments[photoId]) {
                initialComments[photoId] = [];
            }
            
            initialComments[photoId].push({
                id: data.comment_id,
                author: data.author,
                text: data.text,
                timestamp: data.timestamp
            });
            
            // Re-render comments list
            renderDrawerComments(photoId);
            
            // Reset text area
            document.getElementById('comment-text').value = '';
            
            // Show badge on photo card
            const badge = document.getElementById(`cmt-badge-${photoId}`);
            if (badge) {
                badge.innerText = `${initialComments[photoId].length} Comments`;
                badge.style.display = 'inline-block';
            }
        }
    })
    .catch(err => console.error('Error submitting comment:', err));
}

// Copy selected photo filenames to clipboard
function copySelectionList() {
    const favoriteItems = document.querySelectorAll('.gallery-item[data-is-fav="true"] img');
    const filenames = Array.from(favoriteItems).map(img => {
        // Extract name from src path
        const parts = img.src.split('/');
        return parts[parts.length - 1];
    });
    
    const text = filenames.join('\n');
    navigator.clipboard.writeText(text)
    .then(() => {
        alert('Selected filenames copied to clipboard! You can send this list directly to your album designer.');
    })
    .catch(err => console.error('Failed to copy text:', err));
}

// Finalize selections
function finalizeSelection() {
    const count = document.querySelectorAll('.gallery-item[data-is-fav="true"]').length;
    alert(`Congratulations! You have finalized ${count} photos for your physical album. The Aura Photography studio has been notified and will proceed with layout design.`);
}
