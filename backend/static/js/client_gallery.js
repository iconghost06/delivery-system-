// Global client gallery variables
let currentFilter = 'all';
let activeRole = localStorage.getItem('proofer_role') || 'Client';
let replyParentId = null;
let pendingDownloadType = null;

// Initialize layout on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set selector value
    const select = document.getElementById('proofer-role-select');
    if (select) select.value = activeRole;
    
    const nameInput = document.getElementById('comment-author');
    if (nameInput) nameInput.value = activeRole;
    
    initializeGalleryState();
});

// Update proofer role
function changeProoferRole(role) {
    activeRole = role;
    localStorage.setItem('proofer_role', role);
    
    const nameInput = document.getElementById('comment-author');
    if (nameInput) nameInput.value = role;
    
    initializeGalleryState();
}

// Set up likes and badges based on the active proofer role
function initializeGalleryState() {
    const items = document.querySelectorAll('.gallery-item');
    items.forEach(item => {
        const photoId = item.getAttribute('data-photo-id');
        const favsList = initialFavorites[photoId] || [];
        
        const isFav = favsList.includes(activeRole);
        item.setAttribute('data-is-fav', isFav ? 'true' : 'false');
        
        const favBtn = document.getElementById(`fav-btn-${photoId}`);
        if (favBtn) {
            if (isFav) {
                favBtn.classList.add('favorited');
            } else {
                favBtn.classList.remove('favorited');
            }
        }
        
        renderFavBadges(photoId);
    });
    
    updateCounts();
}

// Render initials badges for all roles who liked the photo
function renderFavBadges(photoId) {
    const container = document.getElementById(`fav-badges-${photoId}`);
    if (!container) return;
    container.innerHTML = '';
    
    const favsList = initialFavorites[photoId] || [];
    favsList.forEach(author => {
        const badge = document.createElement('span');
        badge.className = `fav-author-badge ${author.toLowerCase()}`;
        badge.innerText = author.substring(0, 1);
        badge.title = `${author}'s Selection`;
        container.appendChild(badge);
    });
}

// Toggle favorite status asynchronously
function toggleFavorite(button, photoId) {
    const formData = new FormData();
    formData.append('photo_id', photoId)
    formData.append('author', activeRole);

    fetch(`/api/gallery/${GALLERY_HASH}/favorite`, {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        const item = document.querySelector(`.gallery-item[data-photo-id="${photoId}"]`);
        if (!initialFavorites[photoId]) {
            initialFavorites[photoId] = [];
        }
        
        if (data.status === 'added') {
            button.classList.add('favorited');
            item.setAttribute('data-is-fav', 'true');
            if (!initialFavorites[photoId].includes(activeRole)) {
                initialFavorites[photoId].push(activeRole);
            }
        } else {
            button.classList.remove('favorited');
            item.setAttribute('data-is-fav', 'false');
            initialFavorites[photoId] = initialFavorites[photoId].filter(x => x !== activeRole);
            
            if (currentFilter === 'favs') {
                item.style.display = 'none';
            }
        }
        
        renderFavBadges(photoId);
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

// Secure ZIP downloads trigger
function requestDownload(type) {
    if (GALLERY_HAS_PIN) {
        pendingDownloadType = type;
        document.getElementById('pin-modal').style.display = 'flex';
        document.getElementById('download-pin-input').focus();
    } else {
        window.location.href = `/gallery/${GALLERY_HASH}/download?download_type=${type}`;
    }
}

function closePinModal() {
    document.getElementById('pin-modal').style.display = 'none';
    document.getElementById('download-pin-input').value = '';
    pendingDownloadType = null;
}

function submitPin() {
    const pin = document.getElementById('download-pin-input').value.trim();
    if (!pin) {
        alert('Please enter your secure download PIN.');
        return;
    }
    window.location.href = `/gallery/${GALLERY_HASH}/download?download_type=${pendingDownloadType}&pin=${encodeURIComponent(pin)}`;
    closePinModal();
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
    
    cancelCommentReply(); // Reset reply state on open
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
        list.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; font-style: italic; font-family: var(--font-mono);">No layout notes yet.</p>';
        return;
    }
    
    // Group comments into roots and replies
    const roots = [];
    const childrenByParent = {};
    
    comments.forEach(c => {
        if (c.parent_id === null || c.parent_id === undefined) {
            roots.push(c);
        } else {
            if (!childrenByParent[c.parent_id]) {
                childrenByParent[c.parent_id] = [];
            }
            childrenByParent[c.parent_id].push(c);
        }
    });
    
    // Recursive element builder
    function buildCommentEl(c, isReply = false) {
        const wrapper = document.createElement('div');
        wrapper.className = 'comment-wrapper';
        
        const item = document.createElement('div');
        item.className = 'comment-item';
        
        let timeStr = c.timestamp;
        if (timeStr && timeStr.includes('.')) {
            timeStr = timeStr.split('.')[0];
        }
        if (timeStr && timeStr.includes(' ')) {
            const pts = timeStr.split(' ');
            timeStr = `${pts[0]} ${pts[1].substring(0, 5)}`;
        }
        
        item.innerHTML = `
            <div class="comment-meta">
                <span class="comment-author">${c.author}</span>
                <span>${timeStr}</span>
            </div>
            <div class="comment-text" style="color: var(--text-secondary);">${c.text}</div>
            ${!isReply ? `
            <button type="button" class="comment-reply-trigger" onclick="initiateCommentReply('${c.id}', '${c.author}')">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="9 17 4 12 9 7"></polyline>
                    <path d="M20 18v-2a4 4 0 0 0-4-4H4"></path>
                </svg>
                Reply
            </button>
            ` : ''}
        `;
        wrapper.appendChild(item);
        
        const replies = childrenByParent[c.id] || [];
        if (replies.length > 0) {
            const repliesList = document.createElement('div');
            repliesList.className = 'replies-list';
            replies.forEach(r => {
                repliesList.appendChild(buildCommentEl(r, true));
            });
            wrapper.appendChild(repliesList);
        }
        
        return wrapper;
    }
    
    roots.forEach(root => {
        list.appendChild(buildCommentEl(root, false));
    });
}

// Threaded Reply Trigger
function initiateCommentReply(commentId, author) {
    replyParentId = commentId;
    const banner = document.getElementById('reply-banner');
    const targetAuthor = document.getElementById('reply-target-author');
    if (targetAuthor) targetAuthor.innerText = author;
    if (banner) banner.style.display = 'flex';
    document.getElementById('comment-text').focus();
}

function cancelCommentReply() {
    replyParentId = null;
    const banner = document.getElementById('reply-banner');
    if (banner) banner.style.display = 'none';
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
    if (replyParentId) {
        formData.append('parent_id', replyParentId);
    }
    
    fetch(`/api/gallery/${GALLERY_HASH}/comment`, {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            if (!initialComments[photoId]) {
                initialComments[photoId] = [];
            }
            
            initialComments[photoId].push({
                id: data.comment_id,
                author: data.author,
                text: data.text,
                parent_id: data.parent_id,
                timestamp: data.timestamp
            });
            
            cancelCommentReply();
            renderDrawerComments(photoId);
            
            document.getElementById('comment-text').value = '';
            
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
