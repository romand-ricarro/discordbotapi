document.addEventListener('DOMContentLoaded', function() {
    // Load saved API key if available
    const savedApiKey = localStorage.getItem('discord_bot_api_key');
    if (savedApiKey) {
        document.getElementById('api-key').value = savedApiKey;
        document.getElementById('save-api-key').checked = true;
    }

    // Simple Message Form
    document.getElementById('simple-message-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const channelId = document.getElementById('channel-id').value;
        const message = document.getElementById('simple-message').value;
        const apiKey = document.getElementById('api-key').value;

        if (!apiKey) {
            showToast('Error', 'Please enter your API key', 'error');
            return;
        }

        sendChannelMessage(channelId, message, apiKey);
    });

    // Embed Message Form
    document.getElementById('embed-message-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const channelId = document.getElementById('embed-channel-id').value;
        const title = document.getElementById('embed-title').value;
        const description = document.getElementById('embed-description').value;
        const color = document.getElementById('embed-color').value;
        const thumbnail = document.getElementById('embed-thumbnail').value;
        const image = document.getElementById('embed-image').value;
        const apiKey = document.getElementById('api-key').value;

        if (!apiKey) {
            showToast('Error', 'Please enter your API key', 'error');
            return;
        }

        // Collect fields
        const fields = [];
        const fieldContainers = document.querySelectorAll('.field-container');
        
        fieldContainers.forEach(container => {
            const nameInput = container.querySelector('.field-name');
            const valueInput = container.querySelector('.field-value');
            const inlineInput = container.querySelector('.field-inline');
            
            if (nameInput.value && valueInput.value) {
                fields.push({
                    name: nameInput.value,
                    value: valueInput.value,
                    inline: inlineInput.checked
                });
            }
        });

        sendEmbedMessage(channelId, title, description, color, thumbnail, image, fields, apiKey);
    });

    // Direct Message Form
    document.getElementById('dm-message-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const userId = document.getElementById('user-id').value;
        const message = document.getElementById('dm-message').value;
        const apiKey = document.getElementById('api-key').value;

        if (!apiKey) {
            showToast('Error', 'Please enter your API key', 'error');
            return;
        }

        sendDirectMessage(userId, message, apiKey);
    });

    // Add Field Button
    document.getElementById('add-field-button').addEventListener('click', function() {
        addField();
    });

    // Test Connection Button
    document.getElementById('test-connection').addEventListener('click', function() {
        const apiKey = document.getElementById('api-key').value;
        
        if (!apiKey) {
            showToast('Error', 'Please enter your API key', 'error');
            return;
        }
        
        testConnection(apiKey);
    });

    // Save API key checkbox
    document.getElementById('save-api-key').addEventListener('change', function() {
        const apiKey = document.getElementById('api-key').value;
        
        if (this.checked && apiKey) {
            localStorage.setItem('discord_bot_api_key', apiKey);
            showToast('Success', 'API key saved in browser', 'success');
        } else {
            localStorage.removeItem('discord_bot_api_key');
            showToast('Info', 'API key removed from browser', 'info');
        }
    });

    // API key input change
    document.getElementById('api-key').addEventListener('change', function() {
        const saveCheckbox = document.getElementById('save-api-key');
        
        if (saveCheckbox.checked) {
            localStorage.setItem('discord_bot_api_key', this.value);
        }
    });

    // Add event listener for API Keys tab
    const keysTab = document.getElementById('keys-tab');
    if (keysTab) {
        keysTab.addEventListener('shown.bs.tab', function(e) {
            loadApiKeys();
        });
    }
    
    // Refresh keys button
    const refreshKeysBtn = document.getElementById('refresh-keys-btn');
    if (refreshKeysBtn) {
        refreshKeysBtn.addEventListener('click', function() {
            loadApiKeys();
        });
    }
    
    // Create API key form
    const createKeyForm = document.getElementById('create-key-form');
    if (createKeyForm) {
        createKeyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createApiKey();
        });
    }
    
    // Copy API key button
    const copyKeyBtn = document.getElementById('copy-key-btn');
    if (copyKeyBtn) {
        copyKeyBtn.addEventListener('click', function() {
            copyToClipboard('new-api-key-value');
        });
    }

    // Add initial field for embed form
    addField();
});

/**
 * Makes an API request with rate limit handling and better error handling
 * @param {string} url - The API endpoint URL
 * @param {string} method - The HTTP method (GET, POST, DELETE, etc.)
 * @param {object} body - The request body (optional)
 * @param {string} apiKey - The API key
 * @returns {Promise} - A promise that resolves to the API response
 */
function makeApiRequest(url, method, body, apiKey) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: body ? JSON.stringify(body) : null
    })
    .then(response => {
        // Handle rate limit headers
        handleRateLimitHeaders(response);
        
        // If we hit a rate limit
        if (response.status === 429) {
            return response.json().then(data => {
                const resetTime = data.detail.match(/\d+/)[0] || 60;
                showToast('Rate Limit', `Too many requests. Please wait ${resetTime} seconds before trying again.`, 'warning');
                addActivityLog(`Rate limit exceeded. Reset in ${resetTime}s`, 'error');
                throw new Error('Rate limit exceeded');
            });
        }
        
        // Handle permission errors
        if (response.status === 403) {
            return response.json().then(data => {
                showToast('Error', 'Permission denied: ' + data.detail, 'error');
                addActivityLog('Permission denied: ' + data.detail, 'error');
                throw new Error('Admin access required');
            });
        }
        
        // Handle other errors
        if (!response.ok) {
            return response.json().then(data => {
                const errorMsg = data.detail || 'Unknown error';
                showToast('Error', errorMsg, 'error');
                addActivityLog('API error: ' + errorMsg, 'error');
                throw new Error(errorMsg);
            }).catch(e => {
                if (e.message !== 'Admin access required') {
                    throw new Error(`HTTP error ${response.status}`);
                }
                throw e;
            });
        }
        
        return response.json();
    });
}

/**
 * Handles response headers for rate limiting
 * @param {Response} response - The fetch response object
 */
function handleRateLimitHeaders(response) {
    // Extract rate limit headers
    const limit = response.headers.get('X-RateLimit-Limit');
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const reset = response.headers.get('X-RateLimit-Reset');
    
    if (limit && remaining) {
        // Update rate limit display in UI
        updateRateLimitDisplay(limit, remaining, reset);
    }
}

/**
 * Updates the UI to display rate limit information
 */
function updateRateLimitDisplay(limit, remaining, reset) {
    // Create or update the rate limit info
    let rateLimitInfo = document.getElementById('rate-limit-info');
    
    if (!rateLimitInfo) {
        // Create the element if it doesn't exist
        rateLimitInfo = document.createElement('div');
        rateLimitInfo.id = 'rate-limit-info';
        rateLimitInfo.className = 'mt-3 text-muted small';
        
        // Add it to the API settings card
        const apiSettingsCard = document.querySelector('.card-body');
        if (apiSettingsCard) {
            apiSettingsCard.appendChild(rateLimitInfo);
        }
    }
    
    // Calculate percentage of rate limit used
    const percentUsed = ((limit - remaining) / limit) * 100;
    let statusClass = 'text-success';
    
    if (percentUsed > 75) {
        statusClass = 'text-danger';
    } else if (percentUsed > 50) {
        statusClass = 'text-warning';
    }
    
    // Update content with usage info
    rateLimitInfo.innerHTML = `
        <div>API Rate Limit: <span class="${statusClass}">${remaining}/${limit} remaining</span></div>
        ${reset > 0 ? `<div>Resets in: ${reset} seconds</div>` : ''}
        <div class="progress mt-1" style="height: 5px;">
            <div class="progress-bar ${statusClass.replace('text-', 'bg-')}" 
                 role="progressbar" 
                 style="width: ${percentUsed}%" 
                 aria-valuenow="${percentUsed}" 
                 aria-valuemin="0" 
                 aria-valuemax="100"></div>
        </div>
    `;
}

function sendChannelMessage(channelId, message, apiKey) {
    return makeApiRequest('/api/channel-message', 'POST', {
        channel_id: channelId,
        message: message
    }, apiKey)
    .then(data => {
        if (data.success) {
            showToast('Success', 'Message sent successfully!', 'success');
            addActivityLog('Channel message sent', 'success');
            document.getElementById('simple-message').value = '';
        } else {
            showToast('Error', data.error || 'Failed to send message', 'error');
            addActivityLog('Failed to send channel message: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        if (error.message !== 'Rate limit exceeded' && error.message !== 'Admin access required') {
            showToast('Error', 'Error connecting to API: ' + error, 'error');
            addActivityLog('API error: ' + error, 'error');
        }
    });
}

function sendEmbedMessage(channelId, title, description, color, thumbnail, image, fields, apiKey) {
    const embedData = {
        channel_id: channelId,
        title: title,
        description: description
    };
    
    if (color) embedData.color = color;
    if (thumbnail) embedData.thumbnail = thumbnail;
    if (image) embedData.image = image;
    if (fields.length > 0) embedData.fields = fields;
    
    return makeApiRequest('/api/embed-message', 'POST', embedData, apiKey)
    .then(data => {
        if (data.success) {
            showToast('Success', 'Embed message sent successfully!', 'success');
            addActivityLog('Embed message sent', 'success');
            document.getElementById('embed-description').value = '';
        } else {
            showToast('Error', data.error || 'Failed to send embed', 'error');
            addActivityLog('Failed to send embed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        if (error.message !== 'Rate limit exceeded' && error.message !== 'Admin access required') {
            showToast('Error', 'Error connecting to API: ' + error, 'error');
            addActivityLog('API error: ' + error, 'error');
        }
    });
}

function sendDirectMessage(userId, message, apiKey) {
    return makeApiRequest('/api/direct-message', 'POST', {
        user_id: userId,
        message: message
    }, apiKey)
    .then(data => {
        if (data.success) {
            showToast('Success', 'Direct message sent successfully!', 'success');
            addActivityLog('Direct message sent', 'success');
            document.getElementById('dm-message').value = '';
        } else {
            showToast('Error', data.error || 'Failed to send direct message', 'error');
            addActivityLog('Failed to send DM: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        if (error.message !== 'Rate limit exceeded' && error.message !== 'Admin access required') {
            showToast('Error', 'Error connecting to API: ' + error, 'error');
            addActivityLog('API error: ' + error, 'error');
        }
    });
}

function testConnection(apiKey) {
    return makeApiRequest('/api/health', 'GET', null, apiKey)
    .then(data => {
        if (data.status === 'healthy') {
            showToast('Success', 'Connection successful! API is healthy.', 'success');
            addActivityLog('Connection test successful', 'success');
        } else {
            showToast('Warning', 'Connected, but API status is not healthy', 'warning');
            addActivityLog('API status warning', 'warning');
        }
    })
    .catch(error => {
        if (error.message !== 'Rate limit exceeded' && error.message !== 'Admin access required') {
            showToast('Error', 'Failed to connect to API: ' + error, 'error');
            addActivityLog('Connection test failed: ' + error, 'error');
        }
    });
}

/**
 * Load and display all API keys
 */
function loadApiKeys() {
    const apiKey = document.getElementById('api-key').value;
    
    if (!apiKey) {
        showToast('Error', 'Please enter your API key first', 'error');
        return;
    }
    
    const keysTable = document.getElementById('api-keys-table');
    keysTable.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';
    
    return makeApiRequest('/api/keys', 'GET', null, apiKey)
        .then(data => {
            if (data.keys && Array.isArray(data.keys)) {
                displayApiKeys(data.keys);
                addActivityLog('Loaded API keys', 'success');
            } else {
                keysTable.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No API keys found</td></tr>';
                addActivityLog('No API keys found', 'warning');
            }
        })
        .catch(error => {
            if (error.message === 'Admin access required') {
                keysTable.innerHTML = '<tr><td colspan="4" class="text-center text-danger">You need admin privileges to view API keys</td></tr>';
                addActivityLog('Unable to view API keys - admin access required', 'error');
            } else if (error.message !== 'Rate limit exceeded') {
                keysTable.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading API keys</td></tr>';
                addActivityLog('Failed to load API keys: ' + error, 'error');
            }
        });
}

/**
 * Display API keys in the table
 */
function displayApiKeys(keys) {
    const keysTable = document.getElementById('api-keys-table');
    
    if (keys.length === 0) {
        keysTable.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No API keys found</td></tr>';
        return;
    }
    
    let html = '';
    
    keys.forEach(key => {
        const isExpired = key.is_expired ? 'text-danger' : '';
        const expiryStatus = key.is_expired ? '(Expired)' : '';
        
        html += `
            <tr>
                <td>${escapeHtml(key.owner)}</td>
                <td><code>${key.key_preview}</code></td>
                <td class="${isExpired}">${key.expires} ${expiryStatus}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="rotateApiKey('${key.key_preview}')">
                        Rotate
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="revokeApiKey('${key.key_preview}')">
                        Revoke
                    </button>
                </td>
            </tr>
        `;
    });
    
    keysTable.innerHTML = html;
}

/**
 * Create a new API key
 */
function createApiKey() {
    const apiKey = document.getElementById('api-key').value;
    const owner = document.getElementById('key-owner').value;
    const description = document.getElementById('key-description').value;
    const expiresDays = document.getElementById('key-expires').value;
    
    if (!apiKey) {
        showToast('Error', 'Please enter your admin API key first', 'error');
        return;
    }
    
    if (!owner) {
        showToast('Error', 'Owner name is required', 'error');
        return;
    }
    
    const requestData = {
        owner: owner,
        description: description || `API Key for ${owner}`,
        expires_days: parseInt(expiresDays)
    };
    
    return makeApiRequest('/api/keys', 'POST', requestData, apiKey)
        .then(data => {
            if (data.key) {
                addActivityLog(`Created new API key for ${owner}`, 'success');
                showNewApiKey(data);
                
                // Clear the form
                document.getElementById('key-owner').value = '';
                document.getElementById('key-description').value = '';
            } else {
                showToast('Error', 'Failed to create API key', 'error');
                addActivityLog('Failed to create API key', 'error');
            }
        })
        .catch(error => {
            if (error.message === 'Admin access required') {
                showToast('Error', 'Admin access required to create API keys', 'error');
                addActivityLog('Failed to create API key - admin access required', 'error');
            } else if (error.message !== 'Rate limit exceeded') {
                showToast('Error', 'Error creating API key: ' + error, 'error');
                addActivityLog('Failed to create API key: ' + error, 'error');
            }
        });
}

/**
 * Show the newly created API key
 */
function showNewApiKey(keyData) {
    // Set modal values
    document.getElementById('new-api-key-value').value = keyData.key;
    document.getElementById('new-key-owner').value = keyData.owner;
    document.getElementById('new-key-expires').value = keyData.expires;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('new-key-modal'));
    modal.show();
    
    // Refresh the API keys list
    loadApiKeys();
}

/**
 * Revoke an API key
 */
function revokeApiKey(keyPreview) {
    if (!confirm(`Are you sure you want to revoke the API key ${keyPreview}? This cannot be undone.`)) {
        return;
    }
    
    const apiKey = document.getElementById('api-key').value;
    
    // Extract the key ID from the preview
    const keyId = keyPreview.replace('...', '');
    
    return makeApiRequest(`/api/keys/${keyId}`, 'DELETE', null, apiKey)
        .then(data => {
            if (data.success) {
                showToast('Success', 'API key revoked successfully', 'success');
                addActivityLog(`Revoked API key ${keyPreview}`, 'success');
                loadApiKeys();
            } else {
                showToast('Error', 'Failed to revoke API key', 'error');
                addActivityLog(`Failed to revoke API key ${keyPreview}`, 'error');
            }
        })
        .catch(error => {
            if (error.message === 'Admin access required') {
                showToast('Error', 'Admin access required to revoke API keys', 'error');
                addActivityLog('Failed to revoke API key - admin access required', 'error');
            } else if (error.message !== 'Rate limit exceeded') {
                showToast('Error', 'Error revoking API key: ' + error, 'error');
                addActivityLog(`Failed to revoke API key ${keyPreview}: ${error}`, 'error');
            }
        });
}

/**
 * Rotate an API key
 */
function rotateApiKey(keyPreview) {
    if (!confirm(`Are you sure you want to rotate the API key ${keyPreview}? The old key will be revoked and a new one will be created.`)) {
        return;
    }
    
    const apiKey = document.getElementById('api-key').value;
    
    // Extract the key ID from the preview
    const keyId = keyPreview.replace('...', '');
    
    return makeApiRequest(`/api/keys/${keyId}/rotate`, 'POST', null, apiKey)
        .then(data => {
            if (data.key) {
                addActivityLog(`Rotated API key ${keyPreview}`, 'success');
                showNewApiKey(data);
            } else {
                showToast('Error', 'Failed to rotate API key', 'error');
                addActivityLog(`Failed to rotate API key ${keyPreview}`, 'error');
            }
        })
        .catch(error => {
            if (error.message === 'Admin access required') {
                showToast('Error', 'Admin access required to rotate API keys', 'error');
                addActivityLog('Failed to rotate API key - admin access required', 'error');
            } else if (error.message !== 'Rate limit exceeded') {
                showToast('Error', 'Error rotating API key: ' + error, 'error');
                addActivityLog(`Failed to rotate API key ${keyPreview}: ${error}`, 'error');
            }
        });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    element.select();
    
    try {
        document.execCommand('copy');
        showToast('Success', 'Copied to clipboard!', 'success');
    } catch (err) {
        showToast('Error', 'Failed to copy: ' + err, 'error');
    }
    
    // Deselect
    window.getSelection().removeAllRanges();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function addField() {
    const container = document.getElementById('fields-container');
    const fieldId = Date.now();
    
    const fieldHTML = `
        <div class="field-container mb-2" id="field-${fieldId}">
            <div class="row">
                <div class="col">
                    <div class="mb-2">
                        <label class="form-label">Name</label>
                        <input type="text" class="form-control field-name" required>
                    </div>
                </div>
                <div class="col-auto d-flex align-items-end">
                    <button type="button" class="btn btn-sm btn-outline-danger mb-2" onclick="removeField(${fieldId})">Remove</button>
                </div>
            </div>
            <div class="mb-2">
                <label class="form-label">Value</label>
                <textarea class="form-control field-value" rows="2" required></textarea>
            </div>
            <div class="form-check">
                <input class="form-check-input field-inline" type="checkbox" value="" id="field-inline-${fieldId}">
                <label class="form-check-label" for="field-inline-${fieldId}">
                    Display inline
                </label>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', fieldHTML);
}

function removeField(fieldId) {
    const field = document.getElementById(`field-${fieldId}`);
    if (field) {
        field.remove();
    }
}

function showToast(title, message, type) {
    const toast = document.getElementById('status-toast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = document.getElementById('toast-icon');
    
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Set icon and color based on type
    switch(type) {
        case 'success':
            toastIcon.textContent = '✅';
            toast.classList.remove('bg-danger', 'bg-warning', 'bg-info');
            toast.classList.add('bg-success', 'text-white');
            break;
        case 'error':
            toastIcon.textContent = '❌';
            toast.classList.remove('bg-success', 'bg-warning', 'bg-info');
            toast.classList.add('bg-danger', 'text-white');
            break;
        case 'warning':
            toastIcon.textContent = '⚠️';
            toast.classList.remove('bg-success', 'bg-danger', 'bg-info');
            toast.classList.add('bg-warning');
            break;
        case 'info':
            toastIcon.textContent = 'ℹ️';
            toast.classList.remove('bg-success', 'bg-danger', 'bg-warning');
            toast.classList.add('bg-info', 'text-white');
            break;
    }
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function addActivityLog(message, type) {
    const activityLog = document.getElementById('activity-log');
    const timestamp = new Date().toLocaleTimeString();
    
    // Clear "No activity yet" message if it exists
    const noActivity = activityLog.querySelector('.text-muted');
    if (noActivity) {
        activityLog.innerHTML = '';
    }
    
    // Create new activity item
    const activityItem = document.createElement('div');
    activityItem.className = `list-group-item activity-item ${type === 'error' ? 'activity-item-error' : 'activity-item-success'}`;
    
    activityItem.innerHTML = `
        <div>${message}</div>
        <div class="timestamp">${timestamp}</div>
    `;
    
    // Add to the top of the log
    activityLog.insertBefore(activityItem, activityLog.firstChild);
    
    // Limit to 10 items
    if (activityLog.children.length > 10) {
        activityLog.removeChild(activityLog.lastChild);
    }
}