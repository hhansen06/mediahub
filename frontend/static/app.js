// API Configuration
// Always use localhost:8004 for development
let API_BASE_URL = window.location.origin;
if (window.location.hostname === 'localhost' && !window.location.port) {
    // If no port is specified, use 8004
    API_BASE_URL = 'http://localhost:8004';
}

// Toast Notification System
function showToast(message, type = 'info', duration = 4000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');
    const toastId = `toast-${Date.now()}`;
    toast.id = toastId;
    toast.style.cssText = `
        padding: 16px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        min-width: 300px;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
        font-size: 14px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 12px;
    `;

    // Set type-specific styles
    const typeStyles = {
        success: {
            bg: '#d4edda',
            border: '#c3e6cb',
            color: '#155724',
            icon: '✓'
        },
        error: {
            bg: '#f8d7da',
            border: '#f5c6cb',
            color: '#721c24',
            icon: '✕'
        },
        warning: {
            bg: '#fff3cd',
            border: '#ffeaa7',
            color: '#856404',
            icon: '⚠'
        },
        info: {
            bg: '#d1ecf1',
            border: '#bee5eb',
            color: '#0c5460',
            icon: 'ℹ'
        }
    };

    const style = typeStyles[type] || typeStyles.info;
    toast.style.backgroundColor = style.bg;
    toast.style.borderLeft = `4px solid ${style.border}`;
    toast.style.color = style.color;

    toast.innerHTML = `<span style="font-size: 18px; font-weight: bold;">${style.icon}</span><span>${message}</span>`;

    toastContainer.appendChild(toast);

    // Auto remove toast
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}

// Add CSS animations for toasts if not already present
if (!document.getElementById('toastStyles')) {
    const style = document.createElement('style');
    style.id = 'toastStyles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Auth State
let authToken = localStorage.getItem('authToken');
let refreshToken = localStorage.getItem('refreshToken');
let refreshInFlight = null;
let currentView = null;
let currentUser = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Create loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loadingIndicator';
    loadingIndicator.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="
                width: 20px;
                height: 20px;
                border: 3px solid var(--border-color);
                border-top-color: var(--primary-color);
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            "></div>
            <span>Bilder werden geladen...</span>
        </div>
    `;
    loadingIndicator.style.cssText = `
        display: none;
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--bg-secondary);
        color: var(--text-primary);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        font-size: 14px;
    `;
    document.body.appendChild(loadingIndicator);

    // Add spin animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

    // Check if redirected from Keycloak with token
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const refreshTokenFromUrl = urlParams.get('refresh_token');

    if (token) {
        authToken = token;
        localStorage.setItem('authToken', token);
        if (refreshTokenFromUrl) {
            refreshToken = refreshTokenFromUrl;
            localStorage.setItem('refreshToken', refreshTokenFromUrl);
        }
        // Clean URL
        window.history.replaceState({}, document.title, "/");
        loadCurrentUser();
    } else if (authToken) {
        refreshToken = localStorage.getItem('refreshToken');
        loadCurrentUser();
    } else {
        showLogin();
    }

    // Add scroll listener for infinite scrolling
    window.addEventListener('scroll', () => {
        // Check if we're near the bottom of the page
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
            // Load more media if we're viewing a collection
            if (currentView === 'gallery' && window.currentCollectionId && hasMoreMedia && !isLoadingMoreMedia) {
                loadMedia(window.currentCollectionId, false);
            }
            if (currentView === 'images' && imagesHasMore && !imagesIsLoadingMore) {
                loadAllImages(false);
            }
        }
    });

    window.addEventListener('popstate', (event) => {
        if (!currentUser) {
            return;
        }
        const state = event.state || parseRouteFromLocation();
        renderRoute(state);
    });
});

// Auth Functions
async function loadCurrentUser() {
    try {
        const response = await authorizedFetch(`${API_BASE_URL}/auth/me`);

        if (response.ok) {
            currentUser = await response.json();
            showApp();
            initializeRouting();
        } else {
            logout();
        }
    } catch (error) {
        console.error('Error loading user:', error);
        logout();
    }
}

function showLogin() {
    document.getElementById('app').innerHTML = `
        <div class="container text-center" style="padding-top: 5rem;">
            <div class="card" style="max-width: 400px; margin: 0 auto;">
                <h1 class="card-title mb-3">MediaHub</h1>
                <p class="mb-3" style="color: var(--text-secondary);">
                    Melde dich mit deinem Keycloak-Account an
                </p>
                <button onclick="loginKeycloak()" class="btn btn-primary" style="width: 100%;">
                    Mit Keycloak anmelden
                </button>
            </div>
        </div>
    `;
}

function loginKeycloak() {
    window.location.href = `${API_BASE_URL}/auth/login`;
}

function handleProfileClick() {
    showProfileDialog().catch(error => {
        console.error('Error in profile dialog:', error);
        showToast('Fehler beim Öffnen des Profils', 'error');
    });
}

async function showProfileDialog() {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.id = 'profileModal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Mein Profil</h2>
                <button class="close-btn" onclick="document.getElementById('profileModal').remove()">✕</button>
            </div>
            <div style="margin-bottom: 2rem;">
                <form id="profileForm">
                    <div class="form-group">
                        <label>Benutzername</label>
                        <input type="text" value="${escapeHtml(currentUser.username)}" disabled style="background: #f0f0f0; cursor: not-allowed; width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 0.375rem;">
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" value="${escapeHtml(currentUser.email)}" disabled style="background: #f0f0f0; cursor: not-allowed; width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 0.375rem;">
                    </div>
                    <div class="form-group">
                        <label>Wasserzeichen Text</label>
                        <input type="text" id="watermarkText" placeholder="z.B. © 2026 Max Mustermann" value="${escapeHtml(currentUser.watermark_text || '')}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 0.375rem;">
                        <small style="color: var(--text-secondary); display: block; margin-top: 0.5rem;">Dieser Text wird auf exportierten Bildern angezeigt</small>
                    </div>
                    <div style="margin-top: 20px; display: flex; gap: 10px;">
                        <button type="submit" class="btn btn-primary">Speichern</button>
                        <button type="button" onclick="document.getElementById('profileModal').remove()" class="btn btn-outline">Abbrechen</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Handle form submission
    document.getElementById('profileForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveProfile();
    });
}

async function saveProfile() {
    const watermarkText = document.getElementById('watermarkText').value;

    try {
        const response = await authorizedFetch(`${API_BASE_URL}/auth/me`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                watermark_text: watermarkText || null
            })
        });

        if (response.ok) {
            const updatedUser = await response.json();
            currentUser = updatedUser;
            showToast('Profil aktualisiert!', 'success');
            document.getElementById('profileModal').remove();
        } else {
            const error = await response.json();
            showToast('Fehler beim Speichern: ' + (error.detail || 'Unbekannter Fehler'), 'error');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showToast('Fehler beim Speichern des Profils', 'error');
    }
}

function logout() {
    authToken = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    showLogin();
}

function showApp() {
    document.getElementById('app').innerHTML = `
        <div class="header">
            <div class="header-content">
                <div class="logo">MediaHub</div>
                <nav class="nav">
                    <a href="#" onclick="navigateTo('images'); return false;">Bilder</a>
                    <a href="#" onclick="navigateTo('collections'); return false;">Sammlungen</a>
                    <div class="user-info">
                        <span>${currentUser.username}</span>
                        <button onclick="handleProfileClick()" class="btn btn-outline">Profil</button>
                        <button onclick="logout()" class="btn btn-outline">Abmelden</button>
                    </div>
                </nav>
            </div>
        </div>
        <div id="content" class="container"></div>
    `;
}

function buildRouteHash(view, params = {}) {
    switch (view) {
        case 'images':
            return '#/images';
        case 'collections':
            return '#/collections';
        case 'gallery':
            return `#/collections/${params.collectionId}`;
        case 'settings':
            return `#/collections/${params.collectionId}/settings`;
        case 'media':
            return `#/media/${params.mediaId}`;
        default:
            return '#/images';
    }
}

function parseRouteFromLocation() {
    const hash = window.location.hash || '#/images';
    const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean);

    if (parts[0] === 'images') {
        return { view: 'images', params: {} };
    }

    if (parts[0] === 'collections' && parts[1] && parts[2] === 'settings') {
        return { view: 'settings', params: { collectionId: Number(parts[1]) } };
    }

    if (parts[0] === 'collections' && parts[1]) {
        return { view: 'gallery', params: { collectionId: Number(parts[1]) } };
    }

    if (parts[0] === 'media' && parts[1]) {
        return { view: 'media', params: { mediaId: Number(parts[1]) } };
    }

    return { view: 'images', params: {} };
}

function navigateTo(view, params = {}, replace = false) {
    const state = { view, params };
    const hash = buildRouteHash(view, params);
    if (replace) {
        history.replaceState(state, '', hash);
    } else {
        history.pushState(state, '', hash);
    }
    renderRoute(state);
}

function goBackOr(view, params = {}) {
    if (history.state) {
        history.back();
        return;
    }
    navigateTo(view, params, true);
}

function initializeRouting() {
    const initialState = parseRouteFromLocation();
    history.replaceState(initialState, '', buildRouteHash(initialState.view, initialState.params));
    renderRoute(initialState);
}

async function renderRoute(state) {
    currentView = state.view;
    switch (state.view) {
        case 'images':
            closeDetailModal();
            await loadImages();
            break;
        case 'collections':
            closeDetailModal();
            await loadCollections();
            break;
        case 'gallery':
            closeDetailModal();
            await loadGallery(state.params.collectionId);
            break;
        case 'settings':
            closeDetailModal();
            await showCollectionSettings(state.params.collectionId);
            break;
        case 'media':
            await showMediaDetail(state.params.mediaId);
            break;
        default:
            closeDetailModal();
            await loadCollections();
            break;
    }
}

async function refreshAuthToken() {
    if (refreshInFlight) {
        return refreshInFlight;
    }

    if (!refreshToken) {
        throw new Error('No refresh token available');
    }

    refreshInFlight = (async () => {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            throw new Error('Token refresh failed');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        if (data.refresh_token) {
            refreshToken = data.refresh_token;
            localStorage.setItem('refreshToken', refreshToken);
        }

        return authToken;
    })();

    try {
        return await refreshInFlight;
    } finally {
        refreshInFlight = null;
    }
}

async function authorizedFetch(url, options = {}) {
    const headers = {
        ...(options.headers || {})
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    let response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status !== 401) {
        return response;
    }

    try {
        await refreshAuthToken();
    } catch (error) {
        logout();
        throw error;
    }

    const retryHeaders = {
        ...(options.headers || {}),
        'Authorization': `Bearer ${authToken}`
    };

    response = await fetch(url, {
        ...options,
        headers: retryHeaders
    });

    return response;
}

// API Helper
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Authorization': `Bearer ${authToken}`,
        ...options.headers
    };

    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    const response = await authorizedFetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

// Collections
async function loadCollections() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="card-header">
            <h1 class="card-title">Sammlungen</h1>
            <button onclick="showCreateCollectionModal()" class="btn btn-primary">
                Neue Sammlung
            </button>
        </div>
        <div id="collectionsGrid" class="loading">
            <div class="spinner"></div>
        </div>
    `;

    try {
        const collections = await apiRequest('/api/collections/');
        displayCollections(collections);
    } catch (error) {
        console.error('Error loading collections:', error);
        document.getElementById('collectionsGrid').innerHTML = `
            <p class="text-center" style="color: var(--danger-color);">
                Fehler beim Laden der Sammlungen
            </p>
        `;
    }
}

function displayCollections(collections) {
    const grid = document.getElementById('collectionsGrid');

    if (collections.length === 0) {
        grid.innerHTML = `
            <p class="text-center" style="color: var(--text-secondary); padding: 3rem;">
                Noch keine Sammlungen vorhanden. Erstelle deine erste Sammlung!
            </p>
        `;
        return;
    }

    grid.className = 'grid grid-cols-3';
    grid.innerHTML = collections.map(collection => `
        <div class="collection-card" onclick="navigateTo('gallery', { collectionId: ${collection.id} })">
            <div class="collection-name">${escapeHtml(collection.name)}</div>
            <div class="collection-info">
                ${collection.location ? `📍 ${escapeHtml(collection.location)}` : ''}
                ${collection.date ? `<br>📅 ${formatDate(collection.date)}` : ''}
            </div>
            <div class="collection-meta">
                <span>📷 ${collection.media_count} Medien</span>
                <span>👤 ${escapeHtml(collection.owner_username)}</span>
            </div>
        </div>
    `).join('');
}

function showCreateCollectionModal() {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Neue Sammlung</h2>
                <button class="close-btn" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <form onsubmit="createCollection(event)">
                <div class="form-group">
                    <label class="form-label">Name *</label>
                    <input type="text" name="name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Ort</label>
                    <input type="text" name="location" class="form-input">
                </div>
                <div class="form-group">
                    <label class="form-label">Datum</label>
                    <input type="date" name="date" class="form-input">
                </div>
                <div class="form-group">
                    <label class="form-label">Beschreibung</label>
                    <textarea name="description" class="form-textarea"></textarea>
                </div>
                <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                    <button type="button" onclick="this.closest('.modal').remove()" 
                        class="btn btn-outline">Abbrechen</button>
                    <button type="submit" class="btn btn-primary">Erstellen</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
}

async function createCollection(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    const data = {
        name: formData.get('name'),
        location: formData.get('location') || null,
        date: formData.get('date') || null,
        description: formData.get('description') || null
    };

    try {
        await apiRequest('/api/collections/', {
            method: 'POST',
            body: data
        });

        form.closest('.modal').remove();
        navigateTo('collections', {}, true);
    } catch (error) {
        showToast('Fehler beim Erstellen der Sammlung: ' + error.message, 'error');
    }
}

// Gallery (placeholder for Phase 10)
async function loadGallery(collectionId) {
    const content = document.getElementById('content');
    content.innerHTML = `
        <button onclick="goBackOr('collections')" class="btn btn-outline mb-2">← Zurück</button>
        <div id="galleryHeader" class="loading">
            <div class="spinner"></div>
        </div>
        <div id="uploadZone"></div>
        <div id="galleryGrid" class="loading">
            <div class="spinner"></div>
        </div>
    `;

    try {
        // Load collection details
        const collection = await apiRequest(`/api/collections/${collectionId}`);

        document.getElementById('galleryHeader').innerHTML = `
            <div class="card-header">
                <div>
                    <h1 class="card-title">${escapeHtml(collection.name)}</h1>
                    <p style="color: var(--text-secondary);">
                        ${collection.location ? `📍 ${escapeHtml(collection.location)} ` : ''}
                        ${collection.date ? `📅 ${formatDate(collection.date)}` : ''}
                    </p>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    ${collection.owner_id === currentUser.id ? `
                        <button onclick="navigateTo('settings', { collectionId: ${collectionId} })" class="btn btn-outline">
                            ⚙️ Einstellungen
                        </button>
                    ` : ''}
                </div>
            </div>
        `;

        // Show upload zone
        setupUploadZone(collectionId);

        // Load media
        await loadMedia(collectionId);

    } catch (error) {
        console.error('Error loading gallery:', error);
        document.getElementById('galleryGrid').innerHTML = `
            <p class="text-center" style="color: var(--danger-color);">
                Fehler beim Laden der Galerie
            </p>
        `;
    }
}

let imagesPage = 1;
let imagesIsLoadingMore = false;
let imagesHasMore = true;
let imagesCollectionId = null;
let imagesDateFilter = '';
let imagesDatesCache = [];
let selectedMediaIds = new Set();
let lastSelectedIndex = null;
let isSelectionMode = false;

async function getOrCreateImagesCollectionId() {
    if (imagesCollectionId) {
        return imagesCollectionId;
    }

    const collections = await apiRequest('/api/collections/');
    const existing = collections.find(c => c.name === 'Bilder' && c.owner_id === currentUser.id);
    if (existing) {
        imagesCollectionId = existing.id;
        return imagesCollectionId;
    }

    const created = await apiRequest('/api/collections/', {
        method: 'POST',
        body: {
            name: 'Bilder',
            description: 'Automatisch erstellt für den Bilder-Tab',
            location: null,
            date: null
        }
    });

    imagesCollectionId = created.id;
    return imagesCollectionId;
}

async function loadImages(reset = true) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="card-header">
            <h1 class="card-title">Bilder</h1>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <button id="bulkEditBtn" class="btn btn-secondary" style="display: none;">
                    <span id="selectedCount">0</span> ausgewählt - Bearbeiten
                </button>
                <label for="imagesDateFilter" style="color: var(--text-secondary);">Datum</label>
                <select id="imagesDateFilter" class="form-input" style="min-width: 200px;"></select>
            </div>
        </div>
        <div id="uploadZone"></div>
        <div id="galleryGrid" class="loading">
            <div class="spinner"></div>
        </div>
    `;

    // Reset selection state
    selectedMediaIds.clear();
    lastSelectedIndex = null;
    isSelectionMode = false;

    try {
        const dates = await loadImageDates();
        renderImageDateFilter(dates);
        const collectionId = await getOrCreateImagesCollectionId();
        setupUploadZone(collectionId);
        await loadAllImages(reset);

        // Setup bulk edit button
        const bulkEditBtn = document.getElementById('bulkEditBtn');
        bulkEditBtn.addEventListener('click', openBulkEditDialog);
    } catch (error) {
        console.error('Error loading images:', error);
        document.getElementById('galleryGrid').innerHTML = `
            <p class="text-center" style="color: var(--danger-color);">
                Fehler beim Laden der Bilder
            </p>
        `;
    } finally {
        loadingIndicator.style.display = 'none';
    }
}

async function loadImageDates() {
    if (imagesDatesCache.length > 0) {
        return imagesDatesCache;
    }

    const dates = await apiRequest('/api/media/dates?media_type=image');
    imagesDatesCache = Array.isArray(dates) ? dates : [];
    return imagesDatesCache;
}

function renderImageDateFilter(dates) {
    const select = document.getElementById('imagesDateFilter');
    if (!select) {
        return;
    }

    const options = ['<option value="">Alle Daten</option>'];
    dates.forEach(dateStr => {
        let label;
        if (dateStr === "no-date") {
            label = "Kein Datum";
        } else {
            label = dateStr; // Display as YYYY-MM-DD
        }
        const selected = dateStr === imagesDateFilter ? ' selected' : '';
        options.push(`<option value="${dateStr}"${selected}>${label}</option>`);
    });

    select.innerHTML = options.join('');

    select.onchange = () => {
        imagesDateFilter = select.value;
        imagesLastDateKey = null;
        loadAllImages(true);
    };
}

function setupUploadZone(collectionId) {
    const uploadZone = document.getElementById('uploadZone');
    uploadZone.innerHTML = `
        <div class="upload-zone" id="dropZone">
            <div class="upload-zone-content">
                <div class="upload-icon">📤</div>
                <div>
                    <strong>Dateien hierher ziehen oder klicken zum Hochladen</strong>
                </div>
                <button class="btn btn-primary">Dateien auswählen</button>
            </div>
            <input type="file" id="fileInput" multiple accept="image/*,video/*,.heic,.heif">
        </div>
        <div id="uploadProgress"></div>
    `;

    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // Click to select
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(collectionId, e.target.files);
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(collectionId, e.dataTransfer.files);
    });
}

async function handleFiles(collectionId, files) {
    if (files.length === 0) return;

    const progressContainer = document.getElementById('uploadProgress');
    const uploadItems = [];
    const MAX_PARALLEL_UPLOADS = 5;

    // Create overall progress bar
    const totalProgressId = `upload-total-${Date.now()}`;
    const overallProgressHTML = `
        <div class="progress-item" id="${totalProgressId}" style="border: 2px solid var(--primary-color); background: var(--bg-secondary);">
            <div class="progress-info">
                <span style="font-weight: bold;">Gesamtfortschritt</span>
                <span id="${totalProgressId}-count">0/${files.length} Dateien</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%; background: var(--primary-color);"></div>
            </div>
            <div class="progress-status">Wartet...</div>
        </div>
    `;
    progressContainer.insertAdjacentHTML('beforeend', overallProgressHTML);

    let completedCount = 0;

    // Create progress items for each file (hidden by default, only show on error)
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const itemId = `upload-${Date.now()}-${i}`;
        const progressHTML = `
            <div class="progress-item" id="${itemId}" style="display: none;">
                <div class="progress-info">
                    <span>${escapeHtml(file.name)}</span>
                    <span>${formatFileSize(file.size)}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-status">Wartet...</div>
            </div>
        `;
        progressContainer.insertAdjacentHTML('beforeend', progressHTML);
        uploadItems.push({ file, itemId });
    }

    // Upload function for a single file
    async function uploadSingleFile({ file, itemId }) {
        try {
            // Update status to uploading
            const progressStatus = document.querySelector(`#${itemId} .progress-status`);
            progressStatus.textContent = 'Wird hochgeladen...';

            // Create FormData for single file
            const formData = new FormData();
            formData.append('files', file);

            // Upload single file
            const response = await authorizedFetch(`${API_BASE_URL}/api/collections/${collectionId}/media/`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();

                // Update overall progress
                completedCount++;
                const overallFill = document.querySelector(`#${totalProgressId} .progress-fill`);
                const overallStatus = document.querySelector(`#${totalProgressId} .progress-status`);
                const overallCount = document.querySelector(`#${totalProgressId}-count`);

                const percentage = (completedCount / files.length) * 100;
                overallFill.style.width = percentage + '%';
                overallCount.textContent = `${completedCount}/${files.length} Dateien`;

                if (completedCount === files.length) {
                    overallStatus.textContent = '✓ Alle Dateien hochgeladen';
                    overallStatus.classList.add('success');
                } else {
                    overallStatus.textContent = `${completedCount} von ${files.length} hochgeladen...`;
                }

                return { success: true, file };
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Upload fehlgeschlagen');
            }
        } catch (error) {
            console.error(`Upload error for ${file.name}:`, error);

            // Show error item
            const progressItem = document.querySelector(`#${itemId}`);
            progressItem.style.display = 'block';

            const progressFill = document.querySelector(`#${itemId} .progress-fill`);
            const progressStatus = document.querySelector(`#${itemId} .progress-status`);

            progressFill.style.width = '100%';
            progressFill.style.background = 'var(--danger-color)';
            progressStatus.textContent = `✗ ${error.message}`;
            progressStatus.classList.add('error');

            // Update overall progress anyway
            completedCount++;
            const overallFill = document.querySelector(`#${totalProgressId} .progress-fill`);
            const overallCount = document.querySelector(`#${totalProgressId}-count`);
            const percentage = (completedCount / files.length) * 100;
            overallFill.style.width = percentage + '%';
            overallCount.textContent = `${completedCount}/${files.length} Dateien`;

            return { success: false, file, error: error.message };
        }
    }

    // Process uploads with max 5 parallel
    async function processInBatches(items, batchSize) {
        const results = [];
        for (let i = 0; i < items.length; i += batchSize) {
            const batch = items.slice(i, i + batchSize);
            const batchResults = await Promise.all(batch.map(uploadSingleFile));
            results.push(...batchResults);
        }
        return results;
    }

    // Start parallel uploads
    const results = await processInBatches(uploadItems, MAX_PARALLEL_UPLOADS);

    // Clear file input
    document.getElementById('fileInput').value = '';

    // Reload gallery after uploads complete
    setTimeout(() => {
        progressContainer.innerHTML = '';
        if (currentView === 'images') {
            imagesDatesCache = [];
            loadImages(true);
        } else {
            loadMedia(collectionId);
        }
    }, 2000);
}

let currentMediaPage = 1;
let isLoadingMoreMedia = false;
let hasMoreMedia = true;
let imagesLastDateKey = null;

async function loadAllImages(reset = true) {
    const grid = document.getElementById('galleryGrid');

    if (reset) {
        imagesPage = 1;
        imagesHasMore = true;
        imagesLastDateKey = null;
        grid.innerHTML = '';
        window.currentMediaList = [];
        window.currentCollectionId = null;
    }

    if (!imagesHasMore || imagesIsLoadingMore) {
        return;
    }

    imagesIsLoadingMore = true;

    try {
        const limit = 20;
        const skip = (imagesPage - 1) * limit;
        const dateParam = imagesDateFilter ? `&date=${encodeURIComponent(imagesDateFilter)}` : '';
        const response = await apiRequest(`/api/media?media_type=image&sort_by=taken_at&sort_order=desc${dateParam}&limit=${limit}&skip=${skip}`);

        window.currentMediaList = window.currentMediaList.concat(response.items);

        if (response.items.length === 0 && imagesPage === 1) {
            grid.innerHTML = `
                <p class="text-center" style="color: var(--text-secondary); padding: 3rem;">
                    Noch keine Bilder vorhanden. Lade deine ersten Fotos hoch!
                </p>
            `;
            imagesHasMore = false;
            return;
        }

        imagesHasMore = response.items.length === limit && skip + limit < response.total;

        grid.className = 'gallery-grid';
        const newItems = response.items.map((media, index) => {
            const dateValue = media.taken_at; // Only use taken_at, don't fall back to created_at
            const dateKey = dateValue ? new Date(dateValue).toISOString().slice(0, 10) : 'no-date';
            const dateLabel = dateValue ? formatDate(dateValue) : 'Kein Datum';
            const showHeader = dateKey !== imagesLastDateKey;
            if (showHeader) {
                imagesLastDateKey = dateKey;
            }

            const mediaIndex = skip + index;
            const isSelected = selectedMediaIds.has(media.id);
            const selectedClass = isSelected ? 'selected' : '';

            return `
                ${showHeader ? `
                    <div class="date-separator" style="grid-column: 1 / -1; margin: 1rem 0 0.5rem; font-weight: 600; color: var(--text-primary);">
                        ${dateLabel}
                    </div>
                ` : ''}
                <div class="media-item ${selectedClass}" 
                     data-media-id="${media.id}" 
                     data-media-index="${mediaIndex}">
                    <div class="media-checkbox">
                        <input type="checkbox" ${isSelected ? 'checked' : ''} data-media-id="${media.id}" data-media-index="${mediaIndex}">
                    </div>
                    <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Crect fill='%23e2e8f0' width='400' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-size='80'%3E📷%3C/text%3E%3C/svg%3E" 
                         alt="${escapeHtml(media.filename)}"
                         data-media-id="${media.id}">
                </div>
            `;
        }).join('');

        grid.innerHTML += newItems;

        // Attach event handlers to newly added media items
        response.items.forEach((media, index) => {
            const mediaIndex = skip + index;
            const item = document.querySelector(`.media-item[data-media-id="${media.id}"][data-media-index="${mediaIndex}"]`);
            if (item && !item.hasAttribute('data-has-listener')) {
                item.setAttribute('data-has-listener', 'true');

                // Checkbox handler
                const checkbox = item.querySelector('.media-checkbox input');
                if (checkbox) {
                    // Use click event to capture shiftKey
                    checkbox.addEventListener('click', (event) => {
                        event.stopPropagation();
                        // Let the checkbox change state first, then handle
                        setTimeout(() => {
                            handleCheckboxChange(media.id, mediaIndex, checkbox.checked, event.shiftKey);
                        }, 0);
                    });
                }

                // Image click handler - open detail only if not in selection mode
                const img = item.querySelector('img');
                if (img) {
                    img.addEventListener('click', (event) => {
                        if (selectedMediaIds.size === 0) {
                            openMediaDetail(media.id);
                        } else {
                            // Toggle checkbox when in selection mode
                            const checkbox = item.querySelector('.media-checkbox input');
                            if (checkbox) {
                                checkbox.checked = !checkbox.checked;
                                handleCheckboxChange(media.id, mediaIndex, checkbox.checked, false);
                            }
                        }
                    });
                }
            }
        });

        response.items.forEach(media => {
            if (media.thumbnail_s3_key) {
                loadThumbnail(media.id);
            }
        });

        if (imagesHasMore) {
            let loadMoreIndicator = document.getElementById('loadMoreIndicator');
            if (!loadMoreIndicator) {
                loadMoreIndicator = document.createElement('div');
                loadMoreIndicator.id = 'loadMoreIndicator';
                loadMoreIndicator.style.cssText = 'text-align: center; padding: 2rem; color: var(--text-secondary);';
                loadMoreIndicator.innerHTML = `<p>Scrolle nach unten, um mehr Bilder zu laden... (${skip + response.items.length} von ${response.total})</p>`;
                grid.parentElement.appendChild(loadMoreIndicator);
            } else {
                loadMoreIndicator.innerHTML = `<p>Scrolle nach unten, um mehr Bilder zu laden... (${skip + response.items.length} von ${response.total})</p>`;
            }
        } else {
            const loadMoreIndicator = document.getElementById('loadMoreIndicator');
            if (loadMoreIndicator) {
                loadMoreIndicator.remove();
            }
        }

        imagesPage++;
    } catch (error) {
        console.error('Error loading images:', error);
        grid.innerHTML = `
            <p class="text-center" style="color: var(--danger-color);">
                Fehler beim Laden der Bilder
            </p>
        `;
    } finally {
        imagesIsLoadingMore = false;
    }
}

async function loadMedia(collectionId, reset = true) {
    const grid = document.getElementById('galleryGrid');
    const loadingIndicator = document.getElementById('loadingIndicator');

    if (reset) {
        loadingIndicator.style.display = 'flex';
        currentMediaPage = 1;
        hasMoreMedia = true;
        grid.innerHTML = '';
        // Store media list globally for navigation
        window.currentMediaList = [];
        window.currentCollectionId = collectionId;
    }

    if (!hasMoreMedia || isLoadingMoreMedia) {
        return;
    }

    isLoadingMoreMedia = true;

    try {
        const limit = 50;
        const skip = (currentMediaPage - 1) * limit;
        const response = await apiRequest(`/api/media/collections/${collectionId}?limit=${limit}&skip=${skip}`);

        // Append to media list
        window.currentMediaList = window.currentMediaList.concat(response.items);

        if (response.items.length === 0 && currentMediaPage === 1) {
            grid.innerHTML = `
                <p class="text-center" style="color: var(--text-secondary); padding: 3rem;">
                    Noch keine Medien in dieser Sammlung. Lade deine ersten Bilder oder Videos hoch!
                </p>
            `;
            hasMoreMedia = false;
            return;
        }

        // Check if there are more items to load
        hasMoreMedia = response.items.length === limit && skip + limit < response.total;

        grid.className = 'gallery-grid';
        const newItems = response.items.map(media => {
            const isVideo = media.media_type === 'video';
            return `
                <div class="media-item" onclick="openMediaDetail(${media.id})">
                    <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Crect fill='%23e2e8f0' width='400' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-size='80'%3E${isVideo ? '🎥' : '📷'}%3C/text%3E%3C/svg%3E" 
                         alt="${escapeHtml(media.filename)}"
                         data-media-id="${media.id}">
                    ${isVideo ? '<div class="media-type-badge">VIDEO</div>' : ''}
                </div>
            `;
        }).join('');

        grid.innerHTML += newItems;

        // Load actual thumbnails
        response.items.forEach(media => {
            if (media.thumbnail_s3_key) {
                loadThumbnail(media.id);
            }
        });

        // Show info if there are more items
        if (hasMoreMedia) {
            // Add loading indicator if it doesn't exist
            let loadMoreIndicator = document.getElementById('loadMoreIndicator');
            if (!loadMoreIndicator) {
                loadMoreIndicator = document.createElement('div');
                loadMoreIndicator.id = 'loadMoreIndicator';
                loadMoreIndicator.style.cssText = 'text-align: center; padding: 2rem; color: var(--text-secondary);';
                loadMoreIndicator.innerHTML = `<p>Scrolle nach unten, um mehr Fotos zu laden... (${skip + response.items.length} von ${response.total})</p>`;
                grid.parentElement.appendChild(loadMoreIndicator);
            } else {
                loadMoreIndicator.innerHTML = `<p>Scrolle nach unten, um mehr Fotos zu laden... (${skip + response.items.length} von ${response.total})</p>`;
            }
        } else {
            const loadMoreIndicator = document.getElementById('loadMoreIndicator');
            if (loadMoreIndicator) {
                loadMoreIndicator.remove();
            }
        }

        currentMediaPage++;
    } catch (error) {
        console.error('Error loading media:', error);
        grid.innerHTML = `
            <p class="text-center" style="color: var(--danger-color);">
                Fehler beim Laden der Medien
            </p>
        `;
    } finally {
        isLoadingMoreMedia = false;
        if (reset) {
            loadingIndicator.style.display = 'none';
        }
    }
}

async function loadThumbnail(mediaId) {
    try {
        const img = document.querySelector(`img[data-media-id="${mediaId}"]`);
        if (img) {
            img.src = `${API_BASE_URL}/api/media/${mediaId}/thumbnail?token=${authToken}`;
        }
    } catch (error) {
        // Thumbnail not available, keep placeholder
    }
}

async function showMediaDetail(mediaId) {
    try {
        const media = await apiRequest(`/api/media/${mediaId}`);
        const downloadUrl = await apiRequest(`/api/media/${mediaId}/download-url`);

        // Find current index in media list
        const currentIndex = window.currentMediaList?.findIndex(m => m.id === mediaId) ?? -1;
        const hasPrev = currentIndex > 0;
        const hasNext = currentIndex < (window.currentMediaList?.length ?? 0) - 1;

        const modal = document.createElement('div');
        modal.className = 'modal active detail-modal';
        modal.id = 'detailModal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title">${escapeHtml(media.original_filename)}</h2>
                    <button class="close-btn" onclick="closeDetailModal()">×</button>
                </div>
                <div class="detail-container">
                    <div class="detail-image-container">
                        ${hasPrev ? `<button class="nav-button prev" onclick="navigateMedia(-1)">‹</button>` : ''}
                        ${media.media_type === 'image' ?
                `<img src="${downloadUrl.download_url}" class="detail-image" id="detailImage" alt="${escapeHtml(media.filename)}">` :
                `<video src="${downloadUrl.download_url}" controls class="detail-image"></video>`
            }
                        ${hasNext ? `<button class="nav-button next" onclick="navigateMedia(1)">›</button>` : ''}
                    </div>
                    <div class="detail-sidebar">
                        ${renderMetadata(media)}
                        <div style="margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem;">
                            ${media.media_type === 'image' ? `
                            <button onclick="rotateImage(${mediaId})" class="btn btn-secondary">
                                🔄 Rotieren
                            </button>
                            <button onclick="showThumbnailCropEditor(${mediaId})" class="btn btn-secondary">
                                ✂️ Thumbnail bearbeiten
                            </button>
                            <button onclick="copyPublicLink('${media.public_hash}')" class="btn btn-secondary">
                                🔗 Public Link kopieren
                            </button>
                            ` : ''}
                            <a href="${downloadUrl.download_url}" download class="btn btn-primary" style="text-align: center; text-decoration: none;">
                                📥 Download
                            </a>
                            <button onclick="deleteMediaFromDetail(${media.collection_id}, ${mediaId})" class="btn btn-danger">
                                🗑️ Löschen
                            </button>
                        </div>
                        ${media.media_type === 'image' && media.thumbnail_s3_key ? `
                        <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border-color);">
                            <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Thumbnail</div>
                            <img id="detailThumbnail" src="${API_BASE_URL}/api/media/${mediaId}/thumbnail?token=${authToken}&t=${Date.now()}" 
                                 style="width: 100%; max-width: 300px; border-radius: 8px; border: 1px solid var(--border-color);" 
                                 alt="Thumbnail">
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal
        document.querySelector('.detail-modal')?.remove();
        document.body.appendChild(modal);

        // Add keyboard navigation
        setupKeyboardNavigation();

    } catch (error) {
        showToast('Fehler beim Laden der Details: ' + error.message, 'error');
    }
}

function openMediaDetail(mediaId) {
    navigateTo('media', { mediaId });
}

function replaceMediaDetail(mediaId) {
    navigateTo('media', { mediaId }, true);
}

function setupKeyboardNavigation() {
    const handler = (e) => {
        if (!document.getElementById('detailModal')) {
            document.removeEventListener('keydown', handler);
            return;
        }

        if (e.key === 'Escape') {
            closeDetailModal();
        } else if (e.key === 'ArrowLeft') {
            navigateMedia(-1);
        } else if (e.key === 'ArrowRight') {
            navigateMedia(1);
        }
    };

    document.addEventListener('keydown', handler);
}

function navigateMedia(direction) {
    if (!window.currentMediaList) return;

    const currentModal = document.getElementById('detailModal');
    if (!currentModal) return;

    // Get current media ID from modal title or store it
    const currentTitle = currentModal.querySelector('.modal-title').textContent;
    const currentIndex = window.currentMediaList.findIndex(m => m.original_filename === currentTitle);

    if (currentIndex === -1) return;

    const newIndex = currentIndex + direction;
    if (newIndex < 0 || newIndex >= window.currentMediaList.length) return;

    const nextMedia = window.currentMediaList[newIndex];
    replaceMediaDetail(nextMedia.id);
}

function closeDetailModal() {
    if (history.state?.view === 'media') {
        history.back();
        return;
    }
    document.getElementById('detailModal')?.remove();
}

async function deleteMediaFromDetail(collectionId, mediaId) {
    if (!confirm('Möchtest du dieses Medium wirklich löschen?')) return;

    try {
        await apiRequest(`/api/collections/${collectionId}/media/${mediaId}`, {
            method: 'DELETE'
        });

        closeDetailModal();
        navigateTo('gallery', { collectionId }, true);
    } catch (error) {
        showToast('Fehler beim Löschen: ' + error.message, 'error');
    }
}

function renderMetadata(media) {
    const sections = [];

    // Basic info
    sections.push(`
        <div class="metadata-section">
            <div class="metadata-title">Basis-Informationen</div>
            ${metadataItem('Dateiname', media.original_filename)}
            ${metadataItem('Typ', media.media_type === 'image' ? 'Bild' : 'Video')}
            ${metadataItem('Größe', formatFileSize(media.file_size))}
            ${media.width && media.height ? metadataItem('Auflösung', `${media.width} × ${media.height}px`) : ''}
            ${metadataItem('Hochgeladen von', media.uploader_username)}
            ${metadataItem('Hochgeladen am', formatDateTime(media.created_at))}
        </div>
    `);

    // Camera info
    if (media.camera_make || media.camera_model) {
        sections.push(`
            <div class="metadata-section">
                <div class="metadata-title">Kamera</div>
                ${media.camera_make ? metadataItem('Hersteller', media.camera_make) : ''}
                ${media.camera_model ? metadataItem('Modell', media.camera_model) : ''}
                ${media.lens_model ? metadataItem('Objektiv', media.lens_model) : ''}
            </div>
        `);
    }

    // Photo settings and capture time
    if (media.taken_at || media.iso || media.aperture || media.shutter_speed || media.focal_length) {
        sections.push(`
            <div class="metadata-section">
                <div class="metadata-title">Aufnahme-Einstellungen</div>
                ${media.taken_at ? metadataItem('Aufnahmedatum', formatDateTime(media.taken_at)) : ''}
                ${media.iso ? metadataItem('ISO', media.iso) : ''}
                ${media.aperture ? metadataItem('Blende', media.aperture) : ''}
                ${media.shutter_speed ? metadataItem('Belichtungszeit', media.shutter_speed) : ''}
                ${media.focal_length ? metadataItem('Brennweite', media.focal_length) : ''}
            </div>
        `);
    }

    // GPS
    if (media.latitude && media.longitude) {
        const mapId = `map-${Date.now()}`;
        sections.push(`
            <div class="metadata-section">
                <div class="metadata-title">Standort</div>
                ${metadataItem('Latitude', media.latitude.toFixed(6))}
                ${metadataItem('Longitude', media.longitude.toFixed(6))}
                ${media.altitude ? metadataItem('Höhe', `${media.altitude.toFixed(1)}m`) : ''}
                <div id="${mapId}" style="height: 200px; width: 100%; margin-top: 0.75rem; border-radius: 0.5rem; overflow: hidden;"></div>
                <a href="https://www.google.com/maps?q=${media.latitude},${media.longitude}" 
                   target="_blank" class="btn btn-outline" style="width: 100%; margin-top: 0.5rem;">
                    🗺️ In Google Maps öffnen
                </a>
            </div>
        `);

        // Initialize map after DOM is ready
        setTimeout(() => {
            const mapElement = document.getElementById(mapId);
            if (mapElement && typeof L !== 'undefined') {
                const map = L.map(mapId).setView([media.latitude, media.longitude], 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }).addTo(map);
                L.marker([media.latitude, media.longitude]).addTo(map)
                    .bindPopup(media.original_filename)
                    .openPopup();
            }
        }, 100);
    }

    return sections.join('');
}

function metadataItem(label, value) {
    return `
        <div class="metadata-item">
            <span class="metadata-label">${label}</span>
            <span class="metadata-value">${escapeHtml(String(value))}</span>
        </div>
    `;
}

async function deleteMedia(collectionId, mediaId) {
    if (!confirm('Möchtest du dieses Medium wirklich löschen?')) return;

    try {
        await apiRequest(`/collections/${collectionId}/media/${mediaId}`, {
            method: 'DELETE'
        });

        loadMedia(collectionId);
    } catch (error) {
        showToast('Fehler beim Löschen: ' + error.message, 'error');
    }
}

async function deleteCollection(collectionId) {
    if (!confirm('Möchtest du diese Sammlung wirklich löschen? Alle Medien werden ebenfalls gelöscht!')) return;

    try {
        await apiRequest(`/api/collections/${collectionId}`, {
            method: 'DELETE'
        });

        navigateTo('collections', {}, true);
    } catch (error) {
        showToast('Fehler beim Löschen: ' + error.message, 'error');
    }
}

async function showCollectionSettings(collectionId) {
    try {
        const collection = await apiRequest(`/api/collections/${collectionId}`);

        const content = document.getElementById('content');
        content.innerHTML = `
            <button onclick="goBackOr('gallery', { collectionId: ${collectionId} })" class="btn btn-outline mb-2">← Zurück zur Galerie</button>
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Einstellungen: ${escapeHtml(collection.name)}</h2>
                </div>
                <div class="card-content">
                    <h3 style="margin-bottom: 1rem;">Sammlung bearbeiten</h3>
                    <form id="editCollectionForm">
                        <div class="form-group">
                            <label class="form-label">Name</label>
                            <input type="text" id="editName" class="form-input" value="${escapeHtml(collection.name)}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Beschreibung</label>
                            <textarea id="editDescription" class="form-textarea">${escapeHtml(collection.description || '')}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Ort</label>
                            <input type="text" id="editLocation" class="form-input" value="${escapeHtml(collection.location || '')}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Datum</label>
                            <input type="date" id="editDate" class="form-input" value="${collection.date || ''}">
                        </div>
                        <button type="submit" class="btn btn-primary">Änderungen speichern</button>
                    </form>
                    
                    <hr style="margin: 2rem 0; border: none; border-top: 1px solid var(--border);">
                    
                    <h3 style="margin-bottom: 1rem; color: var(--danger-color);">Gefahrenzone</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                        Das Löschen einer Sammlung kann nicht rückgängig gemacht werden. Alle zugehörigen Medien werden ebenfalls gelöscht.
                    </p>
                    <button onclick="deleteCollection(${collectionId})" class="btn btn-danger">
                        Sammlung löschen
                    </button>
                </div>
            </div>
        `;

        document.getElementById('editCollectionForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            try {
                await apiRequest(`/api/collections/${collectionId}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        name: document.getElementById('editName').value,
                        description: document.getElementById('editDescription').value || null,
                        location: document.getElementById('editLocation').value || null,
                        date: document.getElementById('editDate').value || null
                    })
                });

                showToast('Änderungen gespeichert!', 'success');
                navigateTo('gallery', { collectionId }, true);
            } catch (error) {
                showToast('Fehler beim Speichern: ' + error.message, 'error');
            }
        });

    } catch (error) {
        console.error('Error loading settings:', error);
        showToast('Fehler beim Laden der Einstellungen', 'error');
    }
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('de-DE');
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('de-DE');
}

// Persons / Face Recognition Functions
async function loadPersons() {
    try {
        const response = await authorizedFetch('/api/persons/');

        const persons = await response.json();

        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="persons-container">
                <h2>Personen erkannt</h2>
                <div class="persons-grid" id="persons-grid"></div>
            </div>
        `;

        const personsGrid = document.getElementById('persons-grid');

        if (persons.length === 0) {
            personsGrid.innerHTML = '<p class="no-data">Keine Personen identifiziert. Laden Sie Fotos hoch, um Gesichter zu erkennen.</p>';
            return;
        }

        for (const person of persons) {
            const personCard = document.createElement('div');
            personCard.className = 'person-card';

            let faceImageHtml = '';
            if (person.sample_face_image_s3_key) {
                const thumbnailUrl = `/api/media/face-thumbnail/${encodeURIComponent(person.sample_face_image_s3_key)}?token=${authToken}`;
                faceImageHtml = `<img src="${thumbnailUrl}" alt="${escapeHtml(person.name)}" class="face-thumbnail" onerror="this.src='/static/default-face.svg'">`;
            } else {
                faceImageHtml = '<div class="face-placeholder">?</div>';
            }

            personCard.innerHTML = `
                <div class="face-image">
                    ${faceImageHtml}
                </div>
                <div class="person-info">
                    <input type="text" class="person-name-input" value="${escapeHtml(person.name)}" placeholder="Name eingeben" data-person-id="${person.id}">
                    <p class="detection-count">${person.detection_count || 0} Erkennungen</p>
                    <button class="btn-view-detections" onclick="navigateTo('person', { personId: ${person.id} })">Fotos anzeigen</button>
                    <button class="btn-delete-person" onclick="deletePerson(${person.id})">Löschen</button>
                </div>
            `;

            // Save name on blur
            const nameInput = personCard.querySelector('.person-name-input');
            nameInput.addEventListener('blur', async (e) => {
                const newName = e.target.value.trim();
                if (newName !== person.name) {
                    await updatePersonName(person.id, newName);
                }
            });

            personsGrid.appendChild(personCard);
        }

    } catch (error) {
        console.error('Error loading persons:', error);
        showToast('Fehler beim Laden der Personen', 'error');
    }
}

async function updatePersonName(personId, newName) {
    try {
        const response = await authorizedFetch(`/api/persons/${personId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: newName })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log('Person name updated successfully');
    } catch (error) {
        console.error('Error updating person name:', error);
        showToast('Fehler beim Aktualisieren des Namens', 'error');
    }
}

async function deletePerson(personId) {
    if (!confirm('Diese Person wirklich löschen?')) {
        return;
    }

    try {
        const response = await authorizedFetch(`/api/persons/${personId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        navigateTo('persons', {}, true); // Reload persons list
    } catch (error) {
        console.error('Error deleting person:', error);
        showToast('Fehler beim Löschen der Person', 'error');
    }
}

async function viewPersonDetections(personId) {
    try {
        const response = await authorizedFetch(`/api/persons/${personId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const person = await response.json();

        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="detections-view">
                <button class="btn-back" onclick="goBackOr('persons')">← Zurück zu Personen</button>
                <h2>${escapeHtml(person.name)}</h2>
                <div class="detections-grid" id="detections-grid"></div>
            </div>
        `;

        const detectionsGrid = document.getElementById('detections-grid');

        if (!person.detections || person.detections.length === 0) {
            detectionsGrid.innerHTML = '<p class="no-data">Keine Erkennungen für diese Person</p>';
            return;
        }

        for (const detection of person.detections) {
            const detectionCard = document.createElement('div');
            detectionCard.className = 'detection-card';

            const mediaUrl = `/api/media/${detection.media_id}/thumbnail?token=${authToken}`;

            detectionCard.innerHTML = `
                <div class="detection-image">
                    <img src="${mediaUrl}" alt="Detection" onerror="this.src='/static/no-image.svg'">
                    <div class="detection-overlay">
                        <div class="detection-box" style="top: ${detection.top}px; left: ${detection.left}px; width: ${detection.right - detection.left}px; height: ${detection.bottom - detection.top}px;"></div>
                    </div>
                </div>
                <div class="detection-info">
                    <p>Konfidenz: ${(detection.confidence * 100).toFixed(1)}%</p>
                    <small>${formatDateTime(detection.created_at)}</small>
                    <button class="btn-view-media" onclick="openMediaDetail(${detection.media_id})">Foto ansehen</button>
                </div>
            `;

            detectionsGrid.appendChild(detectionCard);
        }

    } catch (error) {
        console.error('Error viewing detections:', error);
        showToast('Fehler beim Laden der Erkennungen', 'error');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function handleCheckboxChange(mediaId, mediaIndex, isChecked, shiftKey = false) {
    const item = document.querySelector(`.media-item[data-media-id="${mediaId}"]`);
    if (!item) return;

    // Handle shift+click for range selection
    if (shiftKey && lastSelectedIndex !== null && isChecked) {
        const start = Math.min(lastSelectedIndex, mediaIndex);
        const end = Math.max(lastSelectedIndex, mediaIndex);

        // Select all items in range
        for (let i = start; i <= end; i++) {
            const rangeItem = document.querySelector(`.media-item[data-media-index="${i}"]`);
            if (rangeItem) {
                const rangeMediaId = parseInt(rangeItem.dataset.mediaId);
                const rangeCheckbox = rangeItem.querySelector('.media-checkbox input');

                if (rangeCheckbox && !rangeCheckbox.checked) {
                    rangeCheckbox.checked = true;
                    selectedMediaIds.add(rangeMediaId);
                    rangeItem.classList.add('selected');
                }
            }
        }

        lastSelectedIndex = mediaIndex;
        isSelectionMode = true;
        updateBulkEditButton();
        return;
    }

    if (isChecked) {
        selectedMediaIds.add(mediaId);
        item.classList.add('selected');
        lastSelectedIndex = mediaIndex;
        isSelectionMode = true;
    } else {
        selectedMediaIds.delete(mediaId);
        item.classList.remove('selected');
        if (selectedMediaIds.size === 0) {
            lastSelectedIndex = null;
            isSelectionMode = false;
        }
    }

    updateBulkEditButton();
}

function updateBulkEditButton() {
    const bulkEditBtn = document.getElementById('bulkEditBtn');
    const selectedCount = document.getElementById('selectedCount');

    if (!bulkEditBtn || !selectedCount) return;

    if (selectedMediaIds.size > 0) {
        selectedCount.textContent = selectedMediaIds.size;
        bulkEditBtn.style.display = 'inline-block';
    } else {
        bulkEditBtn.style.display = 'none';
    }
}

async function openBulkEditDialog() {
    if (selectedMediaIds.size === 0) return;

    // Fetch user list for uploader select
    let users = [];
    try {
        users = await apiRequest('/api/users/');
    } catch (error) {
        console.error('Error fetching users:', error);
    }

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2>Bilder bearbeiten (${selectedMediaIds.size} ausgewählt)</h2>
                <button class="btn-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div class="modal-body">
                <form id="bulkEditForm" onsubmit="event.preventDefault(); submitBulkEdit();">
                    <div class="form-group">
                        <label for="bulkUploader">Uploader ändern (optional)</label>
                        <select id="bulkUploader" class="form-input">
                            <option value="">-- Nicht ändern --</option>
                            ${users.map(u => `<option value="${escapeHtml(u.username)}">${escapeHtml(u.full_name || u.username)}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="bulkTakenAt">Aufnahmedatum ändern (optional)</label>
                        <input type="datetime-local" id="bulkTakenAt" class="form-input">
                        <small style="color: var(--text-secondary);">Leer lassen für "Kein Datum"</small>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                            Abbrechen
                        </button>
                        <button type="submit" class="btn btn-primary">
                            Speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

async function submitBulkEdit() {
    const uploaderSelect = document.getElementById('bulkUploader');
    const takenAtInput = document.getElementById('bulkTakenAt');

    const uploaded_by = uploaderSelect.value || null;
    const taken_at = takenAtInput.value ? new Date(takenAtInput.value).toISOString() : null;

    if (!uploaded_by && !taken_at) {
        showToast('Bitte mindestens ein Feld auswählen', 'warning');
        return;
    }

    try {
        const payload = {
            media_ids: Array.from(selectedMediaIds),
        };

        if (uploaded_by) payload.uploaded_by = uploaded_by;
        if (taken_at) payload.taken_at = taken_at;

        const response = await apiRequest('/api/media/bulk', {
            method: 'PATCH',
            body: payload
        });

        // Close modal
        document.querySelector('.modal').remove();

        // Reset selection
        selectedMediaIds.clear();
        lastSelectedIndex = null;
        isSelectionMode = false;

        // Reload images
        showToast(`${response.updated_count} Bilder erfolgreich aktualisiert`, 'success');
        await loadImages(true);

    } catch (error) {
        console.error('Error updating media:', error);
        showToast('Fehler beim Aktualisieren der Bilder', 'error');
    }
}

// Image rotation
async function rotateImage(mediaId) {
    try {
        const response = await apiRequest(`/api/media/${mediaId}/rotate`, {
            method: 'POST',
            body: { angle: 90 }
        });

        // Reload the image with a cache buster to show the rotated version
        const detailImage = document.getElementById('detailImage');
        if (detailImage && detailImage.src) {
            // Remove any CSS rotation since image is now physically rotated in S3
            detailImage.style.transform = 'rotate(0deg)';

            // Add cache buster to force reload of the image
            const url = new URL(detailImage.src, window.location.origin);
            url.searchParams.set('_cache', Date.now());
            detailImage.src = url.toString();
        }

        showToast('Bild um 90° rotiert!', 'success');

        // Update the media list to show rotation_angle is now 0
        if (window.currentMediaList && window.currentMediaList.length > 0) {
            const mediaIndex = window.currentMediaList.findIndex(m => m.id === mediaId);
            if (mediaIndex >= 0) {
                window.currentMediaList[mediaIndex].rotation_angle = 0;
            }
        }

        // Reload thumbnail preview
        const thumbnailImg = document.getElementById('detailThumbnail');
        if (thumbnailImg && thumbnailImg.src) {
            const url = new URL(thumbnailImg.src, window.location.origin);
            url.searchParams.set('_cache', Date.now());
            thumbnailImg.src = url.toString();
        }

    } catch (error) {
        console.error('Error rotating image:', error);
        showToast('Fehler beim Rotieren: ' + error.message, 'error');
    }
}

// Thumbnail Crop Editor
async function showThumbnailCropEditor(mediaId) {
    try {
        const media = await apiRequest(`/api/media/${mediaId}`);
        const downloadUrl = await apiRequest(`/api/media/${mediaId}/download-url`);

        if (media.media_type !== 'image') {
            showToast('Nur Bilder können bearbeitet werden', 'warning');
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.id = 'cropModal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 90vw; max-height: 90vh; width: auto;">
                <div class="modal-header">
                    <h2 class="modal-title">Thumbnail-Ausschnitt bearbeiten</h2>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div style="padding: 1.5rem;">
                    <div style="position: relative; display: inline-block; max-width: 100%; max-height: 70vh;">
                        <img id="cropImage" src="${downloadUrl.download_url}" 
                             style="max-width: 100%; max-height: 70vh; display: block;" 
                             alt="${escapeHtml(media.filename)}">
                        <div id="cropBox" style="
                            position: absolute;
                            border: 2px solid var(--primary-color);
                            background: rgba(66, 153, 225, 0.2);
                            cursor: move;
                            box-shadow: 0 0 0 9999px rgba(0,0,0,0.5);
                        ">
                            <div class="crop-handle" data-position="nw" style="position: absolute; top: -5px; left: -5px; width: 10px; height: 10px; background: var(--primary-color); cursor: nw-resize;"></div>
                            <div class="crop-handle" data-position="ne" style="position: absolute; top: -5px; right: -5px; width: 10px; height: 10px; background: var(--primary-color); cursor: ne-resize;"></div>
                            <div class="crop-handle" data-position="sw" style="position: absolute; bottom: -5px; left: -5px; width: 10px; height: 10px; background: var(--primary-color); cursor: sw-resize;"></div>
                            <div class="crop-handle" data-position="se" style="position: absolute; bottom: -5px; right: -5px; width: 10px; height: 10px; background: var(--primary-color); cursor: se-resize;"></div>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                        <button onclick="resetCropBox()" class="btn btn-secondary">Zurücksetzen</button>
                        <button onclick="saveThumbnailCrop(${mediaId})" class="btn btn-primary">Speichern</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Wait for image to load
        const img = document.getElementById('cropImage');
        await new Promise((resolve) => {
            if (img.complete) {
                resolve();
            } else {
                img.onload = resolve;
            }
        });

        // Initialize crop box
        initializeCropBox(media);

    } catch (error) {
        showToast('Fehler beim Laden des Editors: ' + error.message, 'error');
    }
}

function initializeCropBox(media) {
    const img = document.getElementById('cropImage');
    const cropBox = document.getElementById('cropBox');
    const imgRect = img.getBoundingClientRect();

    // Use existing crop coordinates or default to center square
    let cropX = (media.crop_x !== undefined && media.crop_x !== null) ? media.crop_x : 0.25;
    let cropY = (media.crop_y !== undefined && media.crop_y !== null) ? media.crop_y : 0.25;
    let cropWidth = (media.crop_width || 0.5);
    let cropHeight = (media.crop_height || 0.5);

    // Enforce 1:1 aspect ratio: use the smaller dimension to ensure it fits
    let cropSize = Math.min(cropWidth, cropHeight);

    // Ensure crop box stays within bounds
    if (cropX + cropSize > 1) cropX = 1 - cropSize;
    if (cropY + cropSize > 1) cropY = 1 - cropSize;

    // Always use square dimensions
    window.cropData = { x: cropX, y: cropY, width: cropSize, height: cropSize };

    // Position crop box
    updateCropBoxPosition();

    // Add drag handlers
    let isDragging = false;
    let isResizing = false;
    let resizeHandle = null;
    let startX, startY, startCropX, startCropY, startCropSize;

    cropBox.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('crop-handle')) {
            isResizing = true;
            resizeHandle = e.target.dataset.position;
        } else {
            isDragging = true;
        }
        startX = e.clientX;
        startY = e.clientY;
        startCropX = window.cropData.x;
        startCropY = window.cropData.y;
        startCropSize = window.cropData.width;  // width = height for square
        e.preventDefault();
        e.stopPropagation();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging && !isResizing) return;

        const imgRect = img.getBoundingClientRect();
        const deltaX = (e.clientX - startX) / imgRect.width;
        const deltaY = (e.clientY - startY) / imgRect.height;

        if (isDragging) {
            // Move crop box (keep it square)
            // Allow moving to the edges - the box should be able to touch any edge
            window.cropData.x = Math.max(0, Math.min(1 - window.cropData.width, startCropX + deltaX));
            window.cropData.y = Math.max(0, Math.min(1 - window.cropData.height, startCropY + deltaY));
        } else if (isResizing) {
            // Resize crop box maintaining 1:1 aspect ratio
            let newSize = startCropSize;
            let newX = startCropX;
            let newY = startCropY;

            if (resizeHandle === 'se') {
                // Bottom-right: use the larger delta to maintain square
                const delta = Math.max(deltaX, deltaY);
                newSize = Math.max(0.1, Math.min(1 - startCropX, 1 - startCropY, startCropSize + delta));
            } else if (resizeHandle === 'nw') {
                // Top-left: move both x and y, use smaller delta
                const delta = Math.min(deltaX, deltaY);
                newSize = Math.max(0.1, startCropSize - delta);
                const maxDelta = startCropSize - newSize;
                newX = Math.max(0, startCropX + maxDelta);
                newY = Math.max(0, startCropY + maxDelta);
            } else if (resizeHandle === 'ne') {
                // Top-right: x increases, y decreases
                const delta = Math.max(deltaX, -deltaY);
                newSize = Math.max(0.1, Math.min(1 - startCropX, startCropY + startCropSize, startCropSize + delta));
                newY = Math.max(0, (startCropY + startCropSize) - newSize);
            } else if (resizeHandle === 'sw') {
                // Bottom-left: x decreases, y increases
                const delta = Math.max(-deltaX, deltaY);
                newSize = Math.max(0.1, Math.min(startCropX + startCropSize, 1 - startCropY, startCropSize + delta));
                newX = Math.max(0, (startCropX + startCropSize) - newSize);
            }

            // Ensure crop box stays within image bounds
            if (newX + newSize > 1) {
                newSize = 1 - newX;
            }
            if (newY + newSize > 1) {
                newSize = 1 - newY;
            }

            window.cropData.x = newX;
            window.cropData.y = newY;
            window.cropData.width = newSize;
            window.cropData.height = newSize;  // Always square
        }

        updateCropBoxPosition();
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        isResizing = false;
        resizeHandle = null;
    });
}

function updateCropBoxPosition() {
    const img = document.getElementById('cropImage');
    const cropBox = document.getElementById('cropBox');
    const imgRect = img.getBoundingClientRect();
    const parentRect = img.parentElement.getBoundingClientRect();

    // Calculate pixel positions
    const left = window.cropData.x * imgRect.width;
    const top = window.cropData.y * imgRect.height;

    // For 1:1 aspect ratio, use the smaller dimension as reference
    const pixelSize = Math.min(
        window.cropData.width * imgRect.width,
        window.cropData.height * imgRect.height
    );

    cropBox.style.left = left + 'px';
    cropBox.style.top = top + 'px';
    cropBox.style.width = pixelSize + 'px';
    cropBox.style.height = pixelSize + 'px';
}

function resetCropBox() {
    window.cropData = { x: 0.25, y: 0.25, width: 0.5, height: 0.5 };
    updateCropBoxPosition();
}

async function saveThumbnailCrop(mediaId) {
    try {
        const cropPayload = {
            crop_x: window.cropData.x,
            crop_y: window.cropData.y,
            crop_width: window.cropData.width,
            crop_height: window.cropData.height
        };

        console.log('Sending crop data:', cropPayload);

        const response = await apiRequest(`/api/media/${mediaId}/thumbnail-crop`, {
            method: 'POST',
            body: cropPayload
        });

        showToast('Thumbnail erfolgreich aktualisiert!', 'success');

        // Close modal
        document.getElementById('cropModal').remove();

        // Reload thumbnail in detail view if open
        const detailThumbnail = document.getElementById('detailThumbnail');
        if (detailThumbnail) {
            detailThumbnail.src = `${API_BASE_URL}/api/media/${mediaId}/thumbnail?token=${authToken}&t=${Date.now()}`;
        }

        // Reload gallery to show new thumbnail
        if (window.currentCollectionId) {
            await loadImages(true);
        }

    } catch (error) {
        console.error('Error saving crop:', error);
        const errorMessage = error.message || (error.detail ? error.detail : JSON.stringify(error));
        showToast('Fehler beim Speichern: ' + errorMessage, 'error');
    }
}
async function copyPublicLink(publicHash) {
    try {
        // Construct the public URL using the public hash
        const baseUrl = window.location.origin;
        const path = '/api/media/public/' + publicHash;
        const publicUrl = baseUrl + path;

        // Copy to clipboard
        await navigator.clipboard.writeText(publicUrl);
        showToast('Public Link kopiert!', 'success');

    } catch (error) {
        console.error('Error copying public link:', error);
        showToast('Fehler beim Kopieren: ' + error.message, 'error');
    }
}
