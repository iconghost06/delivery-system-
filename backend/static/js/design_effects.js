// 1. Custom Interactive Cursor Follower with Elastic Physics
const cursor = document.getElementById('customCursor');
let targetX = 0, targetY = 0;
let currentX = 0, currentY = 0;
const cursorInertia = 0.12; // Speed multiplier for elastic lag

// Track Mouse Movement
document.addEventListener('mousemove', (e) => {
    targetX = e.clientX;
    targetY = e.clientY;
});

// Animate Cursor position using RequestAnimationFrame
function animateCursor() {
    currentX += (targetX - currentX) * cursorInertia;
    currentY += (targetY - currentY) * cursorInertia;
    
    if (cursor) {
        cursor.style.left = `${currentX}px`;
        cursor.style.top = `${currentY}px`;
    }
    
    requestAnimationFrame(animateCursor);
}
requestAnimationFrame(animateCursor);

// Show / Hide cursor when mouse leaves or enters the viewport
document.addEventListener('mouseleave', () => {
    if (cursor) cursor.style.opacity = '0';
});
document.addEventListener('mouseenter', () => {
    if (cursor) cursor.style.opacity = '1';
});

// Cursor State Controller
window.setCursorState = function(state) {
    if (!cursor) return;
    cursor.className = 'cursor-dot'; // Reset classes
    cursor.textContent = ''; // Reset text content
    
    if (state === 'hover') {
        cursor.classList.add('hover');
    } else if (state === 'view') {
        cursor.classList.add('view');
        cursor.textContent = 'view';
    } else if (state === 'drag') {
        cursor.classList.add('drag');
        cursor.textContent = '← drag →';
    }
};

// Automatically track hover states on interactive elements globally
document.addEventListener('mouseover', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        setCursorState('normal');
        return;
    }
    const interactive = e.target.closest('a, button, [role="button"], .shutter-btn, .action-icon, .portfolio-cell, .gallery-item img');
    if (interactive) {
        if (interactive.classList.contains('portfolio-cell') || (interactive.tagName === 'IMG' && interactive.closest('.portfolio-cell, .gallery-item'))) {
            setCursorState('view');
        } else {
            setCursorState('hover');
        }
    } else {
        setCursorState('normal');
    }
});


// 2. Magnetic Nav Links Effect
const magneticLinks = document.querySelectorAll('.magnetic-link');
magneticLinks.forEach(link => {
    link.addEventListener('mousemove', (e) => {
        const rect = link.getBoundingClientRect();
        const relX = e.clientX - (rect.left + rect.width / 2);
        const relY = e.clientY - (rect.top + rect.height / 2);
        
        // Pull the text 35% towards the cursor coordinate within the link boundary
        link.style.transform = `translate(${relX * 0.35}px, ${relY * 0.35}px)`;
    });
    
    link.addEventListener('mouseleave', () => {
        // Snap back to base position smoothly
        link.style.transform = 'translate(0, 0)';
    });
});


// 3. Brutalist Navbar Background Indicator
const navBar = document.querySelector('nav');
const navBlob = document.getElementById('navBlob');
const navLinks = document.querySelectorAll('.nav-link');

if (navBar && navBlob) {
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', () => {
            const rect = link.getBoundingClientRect();
            const navRect = navBar.getBoundingClientRect();
            const newLeft = rect.left - navRect.left;
            const newWidth = rect.width;
            
            navBlob.style.left = `${newLeft}px`;
            navBlob.style.width = `${newWidth}px`;
            navBlob.style.opacity = '1';
        });
    });

    // Hide blob when user stops hovering nav links
    navBar.addEventListener('mouseleave', () => {
        navBlob.style.opacity = '0';
    });
}


// 4. Logo Camera Lens Previews
window.showLensPreview = function(imageId, element) {
    const lensPics = document.querySelectorAll('.lens-pic');
    lensPics.forEach(pic => pic.classList.remove('active'));
    
    const targetPic = document.getElementById(imageId);
    if (targetPic) {
        targetPic.classList.add('active');
    }
};


// 5. Aperture Client Login Menu Toggle
const shutterBtn = document.querySelector('.shutter-btn');
const shutterContainer = document.getElementById('shutterMenuContainer');

if (shutterBtn && shutterContainer) {
    shutterBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        shutterContainer.classList.toggle('active');
    });
}

// Close Shutter Menu if clicked outside
document.addEventListener('click', (e) => {
    const container = document.getElementById('shutterMenuContainer');
    if (container && !container.contains(e.target)) {
        container.classList.remove('active');
    }
});

// 6. IntersectionObserver Scroll Entrance Reveal Fallback (Firefox, older Safari)
if (!CSS.supports('(animation-timeline: view()) and (animation-range: entry)')) {
    const revealOnScrollElements = document.querySelectorAll('.reveal-on-scroll');
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
            }
        });
    }, { threshold: 0.1 });

    revealOnScrollElements.forEach(el => {
        revealObserver.observe(el);
        
        // Check if element is already in viewport on load
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
            el.classList.add('revealed');
        }
    });
}

// 7. Split Text Animation Initializer & Observer
const splitTextElements = document.querySelectorAll('[data-split-text]');
splitTextElements.forEach(el => {
    const htmlContent = el.innerHTML.trim();
    const lines = htmlContent.split(/<br\s*\/?>/i);
    el.innerHTML = '';
    
    lines.forEach((line, lineIdx) => {
        const lineDiv = document.createElement('div');
        lineDiv.style.overflow = 'hidden';
        lineDiv.style.display = 'block';
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = line;
        const text = tempDiv.textContent || tempDiv.innerText || '';
        
        [...text].forEach((char, charIdx) => {
            const span = document.createElement('span');
            span.textContent = char === ' ' ? '\u00A0' : char;
            span.style.transitionDelay = `${(lineIdx * 10 + charIdx) * 0.02}s`;
            lineDiv.appendChild(span);
        });
        
        el.appendChild(lineDiv);
        if (lineIdx < lines.length - 1) {
            el.appendChild(document.createElement('br'));
        }
    });

    const splitObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-split');
                splitObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.05 });

    splitObserver.observe(el);
});

