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
    
    cursor.style.left = `${currentX}px`;
    cursor.style.top = `${currentY}px`;
    
    requestAnimationFrame(animateCursor);
}
requestAnimationFrame(animateCursor);

// Show / Hide cursor when mouse leaves or enters the viewport
document.addEventListener('mouseleave', () => {
    cursor.style.opacity = '0';
});
document.addEventListener('mouseenter', () => {
    cursor.style.opacity = '1';
});

// Cursor State Controller
window.setCursorState = function(state) {
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


// 3. Liquid Gooey Navbar Background Indicator
const navBar = document.getElementById('navBar');
const navBlob = document.getElementById('navBlob');
const navLinks = document.querySelectorAll('.nav-link');

let currentLeft = 0;
let currentWidth = 0;

navLinks.forEach(link => {
    link.addEventListener('mouseenter', () => {
        const rect = link.getBoundingClientRect();
        const navRect = navBar.getBoundingClientRect();
        const newLeft = rect.left - navRect.left;
        const newWidth = rect.width;
        
        if (currentWidth > 0) {
            const deltaX = newLeft - currentLeft;
            const absDeltaX = Math.abs(deltaX);
            
            if (absDeltaX > 15) {
                // Calculate dynamic stretch magnitude based on hover distance
                const stretch = Math.min(absDeltaX * 0.35, 75);
                navBlob.style.width = `${currentWidth + stretch}px`;
                
                // Offset left offset so it expands forward/backward organically
                if (deltaX < 0) {
                    navBlob.style.left = `${newLeft}px`;
                } else {
                    navBlob.style.left = `${currentLeft}px`;
                }
                
                // Snap to final dimensions on target finish
                setTimeout(() => {
                    navBlob.style.left = `${newLeft}px`;
                    navBlob.style.width = `${newWidth}px`;
                }, 120);
            } else {
                navBlob.style.left = `${newLeft}px`;
                navBlob.style.width = `${newWidth}px`;
            }
        } else {
            navBlob.style.left = `${newLeft}px`;
            navBlob.style.width = `${newWidth}px`;
        }
        
        currentLeft = newLeft;
        currentWidth = newWidth;
        navBlob.style.opacity = '1';
    });
});

// Hide blob when user stops hovering nav links
navBar.addEventListener('mouseleave', () => {
    navBlob.style.opacity = '0';
    currentLeft = 0;
    currentWidth = 0;
});


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
window.toggleShutterMenu = function() {
    const container = document.getElementById('shutterMenuContainer');
    container.classList.toggle('active');
};

// Close Shutter Menu if clicked outside
document.addEventListener('click', (e) => {
    const container = document.getElementById('shutterMenuContainer');
    if (container && !container.contains(e.target)) {
        container.classList.remove('active');
    }
});


// 6. Asymmetric Editorial Grid Hover Tilt & Lift
const gridItems = document.querySelectorAll('.grid-item');
gridItems.forEach(item => {
    item.addEventListener('mousemove', (e) => {
        const rect = item.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        // Find percentage offset from center
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        // Max tilt of 8 degrees in X and Y planes
        const rotateY = ((mouseX - centerX) / centerX) * 8;
        const rotateX = ((centerY - mouseY) / centerY) * 8;
        
        item.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
        
        // Push the inner descriptive overlay in matching perspective direction
        const overlay = item.querySelector('.item-overlay');
        if (overlay) {
            overlay.style.transform = `translate3d(${rotateY * 1.5}px, ${-rotateX * 1.5}px, 20px)`;
        }
    });
    
    item.addEventListener('mouseleave', () => {
        // Reset transformation elements smoothly
        item.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
        
        const overlay = item.querySelector('.item-overlay');
        if (overlay) {
            overlay.style.transform = 'translate3d(0, 0, 0)';
        }
    });
});
