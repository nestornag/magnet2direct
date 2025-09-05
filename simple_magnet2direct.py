from flask import Flask, request, render_template_string, jsonify, redirect, send_file
from seedrcc import Seedr
import time
import os
import threading
import requests

app = Flask(__name__)

# Default credentials (can be overridden by user)
DEFAULT_EMAIL = ""
DEFAULT_PASSWORD = ""

# Download folder (for local development only)
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "Magnet2Direct") if os.path.expanduser("~") != "~" else "/tmp"

# Global variables
download_status = {"progress": 0, "status": "idle", "filename": "", "download_url": "", "file_size": "", "error": ""}

# Create download folder (only if not in serverless environment)
try:
    if not os.path.exists(DOWNLOAD_FOLDER) and os.path.expanduser("~") != "~":
        os.makedirs(DOWNLOAD_FOLDER)
except:
    pass  # Skip folder creation in serverless environments

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/site.webmanifest">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Magnet 2 Direct</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 15px;
            line-height: 1.6;
        }
        
        .container {
            max-width: 650px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            padding: 40px;
            margin-top: 20px;
            position: relative;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 25px;
                margin-top: 60px;
                border-radius: 15px;
            }
            
            body {
                padding: 10px;
            }
        }
        
        h1 {
            text-align: center;
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 2.8em;
            font-weight: 700;
        }
        
        @media (max-width: 768px) {
            h1 {
                font-size: 2.2em;
                margin-bottom: 10px;
            }
        }
        
        .subtitle {
            text-align: center;
            color: #718096;
            margin-bottom: 35px;
            font-size: 1.1em;
            font-weight: 400;
        }
        
        @media (max-width: 768px) {
            .subtitle {
                font-size: 1em;
                margin-bottom: 25px;
            }
        }
        
        .form-group {
            margin: 25px 0;
        }
        
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: 600;
            color: #4a5568;
            font-size: 0.95em;
        }
        
        input[type="text"], input[type="email"], input[type="password"] {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8fafc;
            color: #2d3748;
        }
        
        input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            transform: translateY(-1px);
        }
        
        input::placeholder {
            color: #a0aec0;
            font-style: italic;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 8px;
            min-width: 140px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
        }
        
        .btn-copy {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3);
        }
        
        .btn-copy:hover {
            box-shadow: 0 8px 25px rgba(72, 187, 120, 0.4);
        }
        
        .btn-download {
            background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
            box-shadow: 0 4px 15px rgba(66, 153, 225, 0.3);
        }
        
        .btn-download:hover {
            box-shadow: 0 8px 25px rgba(66, 153, 225, 0.4);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);
            box-shadow: 0 4px 15px rgba(245, 101, 101, 0.3);
        }
        
        .btn-danger:hover {
            box-shadow: 0 8px 25px rgba(245, 101, 101, 0.4);
        }
        
        @media (max-width: 768px) {
            .btn {
                width: 100%;
                margin: 5px 0;
                padding: 14px 24px;
                font-size: 15px;
            }
        }
        
        .progress-container {
            margin: 30px 0;
            padding: 25px;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 15px;
            border: 1px solid #e2e8f0;
        }
        
        .account-info {
            margin: 30px 0;
            padding: 25px;
            background: linear-gradient(135deg, #f0fff4 0%, #e6fffa 100%);
            border-radius: 15px;
            border: 1px solid #9ae6b4;
            font-size: 14px;
        }
        
        .account-info h4 {
            margin: 0 0 15px 0;
            color: #22543d;
            font-size: 1.1em;
        }
        
        .storage-bar {
            width: 100%;
            height: 24px;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            margin: 12px 0;
        }
        
        .storage-fill {
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #ed8936, #f56565);
            transition: width 0.5s ease;
        }
        
        .progress-bar {
            width: 100%;
            height: 24px;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            margin: 15px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #48bb78);
            transition: width 0.5s ease;
            animation: shimmer 2s infinite;
        }
        
        .status-filename {
            word-break: break-word;
            overflow-wrap: anywhere;
            font-size: 0.9em;
            color: #4a5568;
            margin-top: 10px;
            padding: 8px 12px;
            background: rgba(255,255,255,0.8);
            border-radius: 6px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        }
        
        @keyframes shimmer {
            0% { opacity: 1; }
            50% { opacity: 0.8; }
            100% { opacity: 1; }
        }
        
        .result {
            margin: 30px 0;
            padding: 25px;
            background: linear-gradient(135deg, #f0fff4 0%, #e6fffa 100%);
            border-radius: 15px;
            border: 1px solid #9ae6b4;
        }
        
        .result.error {
            background: linear-gradient(135deg, #fed7d7 0%, #fbb6ce 100%);
            border: 1px solid #fc8181;
            color: #742a2a;
        }
        
        .file-info {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 15px 0;
            border: 1px solid #e2e8f0;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        
        .file-info p {
            margin: 8px 0;
            line-height: 1.5;
        }
        
        .filename-text {
            word-break: break-all;
            overflow-wrap: anywhere;
            max-width: 100%;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 13px;
            background: rgba(0,0,0,0.05);
            padding: 8px 10px;
            border-radius: 6px;
            margin-top: 5px;
        }
        
        .url-box {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 15px;
            border-radius: 10px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            word-break: break-all;
            overflow-wrap: anywhere;
            border: 1px solid #e2e8f0;
            margin: 15px 0;
            font-size: 13px;
            color: #4a5568;
            max-width: 100%;
            overflow-x: auto;
        }
        
        .settings-btn {
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 6px 15px rgba(72, 187, 120, 0.4);
            transition: all 0.3s ease;
            z-index: 100;
        }
        
        .settings-btn:hover {
            background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);
            transform: scale(1.1);
            box-shadow: 0 12px 30px rgba(72, 187, 120, 0.5);
        }
        
        @media (max-width: 768px) {
            .settings-btn {
                width: 45px;
                height: 45px;
                font-size: 18px;
                top: 12px;
                left: 12px;
            }
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.6);
            backdrop-filter: blur(5px);
            overflow-y: auto;
            align-items: center;
            justify-content: center;
            padding: 20px;
            box-sizing: border-box;
        }
        
        .modal.show {
            display: flex;
        }
        
        .modal-content {
            background: white;
            padding: 40px;
            border-radius: 20px;
            width: 100%;
            max-width: 550px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 25px 50px rgba(0,0,0,0.2);
            position: relative;
            animation: modalSlideIn 0.3s ease;
            margin: auto;
        }
        
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @media (max-width: 768px) {
            .modal {
                padding: 15px;
            }
            
            .modal-content {
                padding: 25px;
                border-radius: 15px;
                max-height: 85vh;
            }
        }
        
        .close {
            color: #a0aec0;
            float: right;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
            transition: color 0.3s ease;
        }
        
        .close:hover {
            color: #4a5568;
        }
        
        .credentials-status {
            padding: 16px 20px;
            border-radius: 12px;
            margin: 20px 0;
            font-weight: 600;
            font-size: 0.95em;
        }
        
        .credentials-status.saved {
            background: linear-gradient(135deg, #c6f6d5 0%, #9ae6b4 100%);
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        
        .credentials-status.not-saved {
            background: linear-gradient(135deg, #fed7d7 0%, #fbb6ce 100%);
            color: #742a2a;
            border: 1px solid #fc8181;
        }
        
        .privacy-note {
            margin-top: 25px;
            padding: 20px;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 12px;
            font-size: 14px;
            color: #4a5568;
            border: 1px solid #e2e8f0;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 25px;
        }
        
        @media (max-width: 768px) {
            .button-group {
                flex-direction: column;
                gap: 8px;
            }
        }
        
        /* Loading states */
        .loading {
            opacity: 0.7;
            pointer-events: none;
        }
        
        /* Improved responsive typography */
        @media (max-width: 480px) {
            html {
                font-size: 14px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            .subtitle {
                font-size: 0.95em;
            }
            
            input[type="text"], input[type="email"], input[type="password"] {
                padding: 14px 16px;
                font-size: 16px; /* Prevents zoom on iOS */
            }
            
            .filename-text {
                font-size: 11px;
                padding: 6px 8px;
                line-height: 1.4;
            }
            
            .url-box {
                font-size: 11px;
                padding: 12px;
                line-height: 1.4;
            }
            
            .status-filename {
                font-size: 0.8em;
                padding: 6px 10px;
            }
            
            .file-info {
                padding: 15px;
            }
        }
        
        /* Footer */
        .footer {
            margin-top: 50px;
            padding: 30px 20px;
            text-align: center;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            border: 1px solid #e2e8f0;
            color: #6c757d;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .footer a {
            color: #007bff;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.3s ease;
        }
        
        .footer a:hover {
            color: #0056b3;
            text-decoration: underline;
        }
        
        .footer .disclaimer {
            font-size: 12px;
            color: #868e96;
            margin-top: 15px;
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .footer {
                margin-top: 30px;
                padding: 20px 15px;
                font-size: 13px;
            }
        }
    </style>
    
    <script>
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const statusEl = document.getElementById('status');
                    const resultEl = document.getElementById('result');
                    const submitBtn = document.getElementById('submitBtn');
                    
                    if (data.status === 'processing') {
                        statusEl.style.display = 'block';
                        statusEl.innerHTML = `
                            <div><strong>Status:</strong> ${data.status}</div>
                            <div>Progress: ${data.progress}%</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${data.progress}%"></div>
                            </div>
                            ${data.filename ? `<div class="status-filename">${data.filename}</div>` : ''}
                        `;
                        submitBtn.disabled = true;
                        setTimeout(checkStatus, 2000);
                    } else if (data.status === 'completed') {
                        statusEl.style.display = 'none';
                        resultEl.innerHTML = `
                            <h3>✅ Video Found!</h3>
                            <div class="file-info">
                                <p><strong>Filename:</strong></p>
                                <div class="filename-text">${data.filename}</div>
                                <p style="margin-top: 15px;"><strong>Size:</strong> ${data.file_size}</p>
                            </div>
                            <div class="url-box" id="downloadUrl">${data.download_url}</div>
                            <div class="button-group" style="margin-top: 20px;">
                                <button class="btn btn-copy" onclick="copyUrl()">📋 Copy Download URL</button>
                                <a href="/download-file" target="_blank" class="btn btn-download">📥 Download File</a>
                            </div>
                        `;
                        resultEl.className = 'result';
                        resultEl.style.display = 'block';
                        submitBtn.disabled = false;
                        
                        // Auto-scroll to results section
                        setTimeout(() => {
                            resultEl.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'center'
                            });
                        }, 100);
                    } else if (data.status === 'error') {
                        statusEl.style.display = 'none';
                        resultEl.innerHTML = `<h3>❌ Error</h3><p>${data.error}</p>`;
                        resultEl.className = 'result error';
                        resultEl.style.display = 'block';
                        submitBtn.disabled = false;
                        
                        // Auto-scroll to error message
                        setTimeout(() => {
                            resultEl.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'center'
                            });
                        }, 100);
                    } else {
                        submitBtn.disabled = false;
                    }
                });
        }
        
        function addMagnet() {
            const magnet = document.getElementById('magnet').value.trim();
            if (!magnet) {
                alert('Please enter a magnet link');
                return;
            }
            
            const credentials = getSavedCredentials();
            if (!credentials.email || !credentials.password) {
                alert('Please set up your Seedr credentials first (click the ⚙️ button)');
                openSettings();
                return;
            }
            
            const formData = new FormData();
            formData.append('magnet', magnet);
            formData.append('email', credentials.email);
            formData.append('password', credentials.password);
            
            fetch('/add-magnet', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'started') {
                    checkStatus();
                } else if (data.error) {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        function copyUrl() {
            const urlText = document.getElementById('downloadUrl').textContent;
            navigator.clipboard.writeText(urlText).then(() => {
                alert('Download URL copied to clipboard!');
            });
        }
        
        // Auto-check status on page load
        window.onload = function() {
            checkStatus();
            loadAccountInfo();
            loadSavedCredentials();
        };
        
        // Credential management functions
        function loadSavedCredentials() {
            const email = localStorage.getItem('seedr_email');
            const password = localStorage.getItem('seedr_password');
            const statusEl = document.getElementById('credentialsStatus');
            
            if (email && password) {
                statusEl.className = 'credentials-status saved';
                statusEl.innerHTML = '✅ Credentials saved for: ' + email;
                document.getElementById('seedrEmail').value = email;
                document.getElementById('seedrPassword').value = password;
            } else {
                statusEl.className = 'credentials-status not-saved';
                statusEl.innerHTML = '❌ No credentials saved - Please add your Seedr account';
            }
        }
        
        function saveCredentials() {
            const email = document.getElementById('seedrEmail').value.trim();
            const password = document.getElementById('seedrPassword').value.trim();
            
            if (!email || !password) {
                alert('Please enter both email and password');
                return;
            }
            
            // Test credentials first
            testCredentials(email, password).then(valid => {
                if (valid) {
                    localStorage.setItem('seedr_email', email);
                    localStorage.setItem('seedr_password', password);
                    loadSavedCredentials();
                    alert('✅ Credentials saved successfully!');
                    closeSettings();
                    loadAccountInfo(); // Refresh account info
                } else {
                    alert('❌ Invalid credentials. Please check your email and password.');
                }
            });
        }
        
        function clearCredentials() {
            if (confirm('Are you sure you want to clear saved credentials?')) {
                localStorage.removeItem('seedr_email');
                localStorage.removeItem('seedr_password');
                document.getElementById('seedrEmail').value = '';
                document.getElementById('seedrPassword').value = '';
                loadSavedCredentials();
                alert('🗑️ Credentials cleared');
            }
        }
        
        function testCredentials(email, password) {
            return fetch('/test-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => data.valid)
            .catch(() => false);
        }
        
        function openSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'flex';
            modal.classList.add('show');
        }
        
        function closeSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('settingsModal');
            if (event.target == modal) {
                closeSettings();
            }
        }
        
        // Modified functions to use saved credentials
        function getSavedCredentials() {
            return {
                email: localStorage.getItem('seedr_email') || '',
                password: localStorage.getItem('seedr_password') || ''
            };
        }
        
        function loadAccountInfo() {
            const credentials = getSavedCredentials();
            if (!credentials.email || !credentials.password) {
                const accountInfoEl = document.getElementById('account-info');
                const accountDetailsEl = document.getElementById('account-details');
                accountDetailsEl.innerHTML = `
                    <div style="color: #dc3545;">
                        <strong>⚠️ No Seedr credentials set</strong><br>
                        <small>Click the ⚙️ button to add your account</small>
                    </div>
                `;
                accountInfoEl.style.display = 'block';
                return;
            }
            
            fetch('/account-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(credentials)
            })
                .then(response => response.json())
                .then(data => {
                    const accountInfoEl = document.getElementById('account-info');
                    const accountDetailsEl = document.getElementById('account-details');
                    
                    if (data.max_file_size !== 'Connection Error') {
                        accountDetailsEl.innerHTML = `
                            <div style="background: #fff3cd; padding: 8px; border-radius: 4px; border: 1px solid #ffeaa7;">
                                <strong>⚠️ Max file size you can download:</strong> <span style="color: #856404; font-weight: bold;">${data.max_file_size}</span>
                            </div>
                        `;
                        accountInfoEl.style.display = 'block';
                    } else {
                        accountDetailsEl.innerHTML = `
                            <div style="color: #dc3545;">
                                <strong>⚠️ Could not load account info</strong><br>
                                <small>Check your Seedr credentials</small>
                            </div>
                        `;
                        accountInfoEl.style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error('Error loading account info:', error);
                    const accountInfoEl = document.getElementById('account-info');
                    const accountDetailsEl = document.getElementById('account-details');
                    accountDetailsEl.innerHTML = `
                        <div style="color: #dc3545;">
                            <strong>⚠️ Connection error</strong><br>
                            <small>Could not load account information</small>
                        </div>
                    `;
                    accountInfoEl.style.display = 'block';
                });
        }
    </script>
</head>
<body>
    <!-- Settings Modal -->
    <div id="settingsModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeSettings()">&times;</span>
            <h2>🔐 Seedr Account Settings</h2>
            <p style="color: #718096; margin-bottom: 25px; font-size: 1.05em;">
                Connect your Seedr account to start downloading. Your credentials are stored securely in your browser only.
            </p>
            
            <div id="credentialsStatus" class="credentials-status not-saved">
                ❌ No credentials saved - Please add your Seedr account
            </div>
            
            <div class="form-group">
                <label for="seedrEmail">📧 Seedr Email Address:</label>
                <input type="email" id="seedrEmail" 
                       placeholder="Enter your Seedr email (e.g., yourname@gmail.com)" 
                       autocomplete="email" required>
            </div>
            
            <div class="form-group">
                <label for="seedrPassword">🔒 Seedr Password:</label>
                <input type="password" id="seedrPassword" 
                       placeholder="Enter your Seedr account password" 
                       autocomplete="current-password" required>
            </div>
            
            <div class="button-group">
                <button type="button" class="btn" onclick="saveCredentials()">
                    💾 Save & Test Connection
                </button>
                <button type="button" class="btn btn-danger" onclick="clearCredentials()">
                    🗑️ Clear Saved Data
                </button>
            </div>
            
            <div class="privacy-note">
                <strong>🔒 Privacy & Security:</strong><br>
                • Your credentials are stored only in your browser's local storage<br>
                • No data is sent to our servers - only directly to Seedr<br>
                • You can clear your data anytime using the button above<br>
                • Your credentials are tested before saving to ensure they work
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Settings Button -->
        <button class="settings-btn" onclick="openSettings()" title="Seedr Account Settings">⚙️</button>
        
        <h1>🧲 Magnet2Direct</h1>
        <p class="subtitle">
            No more Seedr login marathons - Just paste, wait & enjoy! 🍿
        </p>
        
        <div id="account-info" class="account-info" style="display: none;">
            <h4>📊 Your Seedr Account</h4>
            <div id="account-details">Loading account info...</div>
        </div>
        
        <div class="form-group">
            <label for="magnet">🔗 Magnet Link:</label>
            <input type="text" id="magnet" name="magnet" 
                   placeholder="Paste your magnet link here... (e.g., magnet:?xt=urn:btih:...)" 
                   required>
        </div>
        
        <div style="text-align: center;">
            <button type="button" class="btn" id="submitBtn" onclick="addMagnet()">
                🚀 Add Magnet & Download
            </button>
        </div>
        
        <div id="status" class="progress-container" style="display: none;"></div>
        <div id="result" class="result" style="display: none;"></div>
        
        <!-- Footer -->
        <div class="footer">
            <div>
                🍿 <strong>Need magnet links?</strong> <a href="https://github.com/sh13y" target="_blank" rel="noopener">My</a> favorite spot: 
                <a href="https://watchsomuch.to/" target="_blank" rel="noopener">WatchSoMuch</a> 
                <br>
                🎬 <em>"It's like Netflix, but with more... freedom!"</em> 😉
            </div>
            <div class="disclaimer">
                ⚖️ For educational purposes only. We're just converting links here - what you download is between you and your conscience! 
                <br>
                Made with ❤️ (and lots of backpain) for fellow movie lovers who hate repetitive clicking.
            </div>
        </div>
    </div>
</body>
</html>
"""

def get_account_info(client):
    """Get Seedr account information including storage limits."""
    try:
        # Get account settings/info
        settings = client.get_settings()
        
        if settings and hasattr(settings, 'account'):
            account = settings.account
            space_max = getattr(account, 'space_max', 0)
            
            if space_max > 0:
                # Since we clear Seedr each time, max file size = total space
                return {
                    'max_file_size': format_file_size(space_max)
                }
        
        # Fallback for free accounts
        return {
            'max_file_size': '2.0 GB (Free Account Limit)'
        }
            
    except Exception as e:
        print(f"Error getting account info: {e}")
        # Return default values for free account
        return {
            'max_file_size': '2.0 GB (Free Account Limit)'
        }

def connect_to_seedr(email, password, retries=3):
    """Connect to Seedr with retry logic."""
    for attempt in range(retries):
        try:
            print(f"Connecting to Seedr (attempt {attempt + 1}/{retries})...")
            client = Seedr.from_password(email, password)
            print("Connected to Seedr successfully")
            return client
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                raise Exception(f"Could not connect to Seedr after {retries} attempts: {e}")

def clear_seedr_account(client):
    """Delete all files and folders from Seedr account."""
    try:
        contents = client.list_contents()
        deleted_count = 0
        
        # Delete all files
        for file in contents.files:
            try:
                client.delete_file(file.folder_file_id)
                print(f"Deleted file: {file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting file {file.name}: {e}")
        
        # Delete all folders
        for folder in contents.folders:
            try:
                client.delete_folder(folder.id)
                print(f"Deleted folder: {folder.name}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting folder {folder.name}: {e}")
        
        print(f"Cleared Seedr account: {deleted_count} items deleted")
        return True
        
    except Exception as e:
        print(f"Error clearing Seedr account: {e}")
        return False

def process_magnet(magnet_link, email, password):
    """Process magnet link and find video."""
    global download_status
    
    try:
        download_status = {"progress": 10, "status": "processing", "filename": "", "download_url": "", "file_size": "", "error": ""}
        
        client = connect_to_seedr(email, password)
        
        with client:
            print("Connected to Seedr successfully")
            
            # First clear the Seedr account
            download_status["progress"] = 15
            download_status["filename"] = "Clearing Seedr account..."
            
            clear_success = clear_seedr_account(client)
            if not clear_success:
                print("Warning: Could not fully clear Seedr account, continuing anyway...")
            
            # Add the new magnet
            download_status["progress"] = 30
            download_status["filename"] = "Adding magnet to Seedr..."
            
            try:
                result = client.add_torrent(magnet_link)
                print(f"Magnet added successfully: {type(result)}")
            except Exception as e:
                raise Exception(f"Failed to add magnet: {e}")
            
            # Wait for files to appear
            download_status["progress"] = 40
            download_status["filename"] = "Waiting for download..."
            
            max_wait = 300  # 5 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    video_file = find_biggest_video(client)
                    if video_file:
                        print(f"Found video file: {video_file.name}")
                        break
                except Exception as e:
                    print(f"Error checking for files: {e}")
                
                progress = 40 + int((wait_time / max_wait) * 50)  # 40-90%
                download_status["progress"] = progress
                download_status["filename"] = f"Downloading... ({wait_time}s)"
                
                time.sleep(10)
                wait_time += 10
            
            if not video_file:
                raise Exception("No video file found after 5 minutes. The torrent might be slow or invalid.")
            
            # Get download URL
            download_status["progress"] = 95
            download_status["filename"] = video_file.name
            
            try:
                fetch_result = client.fetch_file(video_file.folder_file_id)
                download_url = fetch_result.url if hasattr(fetch_result, 'url') else str(fetch_result)
            except Exception as e:
                raise Exception(f"Could not get download URL: {e}")
            
            # Success
            download_status = {
                "progress": 100,
                "status": "completed",
                "filename": video_file.name,
                "download_url": download_url,
                "file_size": format_file_size(video_file.size),
                "error": ""
            }
            print(f"Success! Video: {video_file.name} ({download_status['file_size']})")
            
    except Exception as e:
        print(f"Process error: {e}")
        import traceback
        traceback.print_exc()
        download_status = {
            "progress": 0,
            "status": "error",
            "filename": "",
            "download_url": "",
            "file_size": "",
            "error": f"Error: {str(e)}. Try again with a different magnet link."
        }

def find_biggest_video(client, folder_id=None):
    """Find the biggest video file."""
    biggest_video = None
    biggest_size = 0
    
    try:
        contents = client.list_contents(folder_id)
        folder_name = "root" if folder_id is None else f"folder_{folder_id}"
        print(f"Searching {folder_name}: {len(contents.files)} files, {len(contents.folders)} folders")
        
        # Check files in current folder
        for file in contents.files:
            print(f"Found file: {file.name} ({format_file_size(file.size)})")
            if file.name.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.webm', '.mpg', '.mpeg')):
                print(f"Video file: {file.name}")
                if file.size > biggest_size:
                    biggest_video = file
                    biggest_size = file.size
                    print(f"New biggest video: {file.name} ({format_file_size(file.size)})")
        
        # Check subfolders
        for subfolder in contents.folders:
            print(f"Checking subfolder: {subfolder.name}")
            result = find_biggest_video(client, subfolder.id)
            if result and result.size > biggest_size:
                biggest_video = result
                biggest_size = result.size
                print(f"New biggest from subfolder: {result.name} ({format_file_size(result.size)})")
                
    except Exception as e:
        print(f"Error searching folder {folder_id}: {e}")
        import traceback
        traceback.print_exc()
    
    if biggest_video:
        print(f"Returning biggest video: {biggest_video.name} ({format_file_size(biggest_video.size)})")
    else:
        print("No video files found in this search")
    
    return biggest_video

def format_file_size(size_bytes):
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/add-magnet', methods=['POST'])
def add_magnet():
    magnet = request.form['magnet']
    email = request.form.get('email', DEFAULT_EMAIL)
    password = request.form.get('password', DEFAULT_PASSWORD)
    
    if not email or not password:
        return jsonify({"status": "error", "error": "Seedr credentials required"})
    
    # Start processing in background
    thread = threading.Thread(target=process_magnet, args=(magnet, email, password))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/test-credentials', methods=['POST'])
def test_credentials():
    """Test if Seedr credentials are valid."""
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    try:
        client = connect_to_seedr(email, password, retries=1)
        with client:
            # Try to get account info to verify credentials
            settings = client.get_settings()
            return jsonify({"valid": True})
    except Exception as e:
        print(f"Credential test failed: {e}")
        return jsonify({"valid": False})

@app.route('/account-info', methods=['POST'])
def get_account_info_route():
    """Get Seedr account information."""
    try:
        data = request.get_json()
        email = data.get('email', DEFAULT_EMAIL)
        password = data.get('password', DEFAULT_PASSWORD)
        
        if not email or not password:
            return jsonify({'max_file_size': 'No credentials provided'})
        
        client = connect_to_seedr(email, password)
        with client:
            account_info = get_account_info(client)
            return jsonify(account_info)
    except Exception as e:
        return jsonify({
            'max_file_size': 'Connection Error'
        })

@app.route('/status')
def get_status():
    return jsonify(download_status)

@app.route('/download-file', methods=['GET'])
def download_file():
    """Redirect to direct download URL for browser download."""
    global download_status
    
    if download_status["status"] != "completed" or not download_status["download_url"]:
        return "No file ready for download", 400
    
    # Redirect browser to the direct download URL
    return redirect(download_status["download_url"])

# Favicon and manifest routes
@app.route('/favicon.ico')
def favicon():
    return send_file('favicon.ico')

@app.route('/apple-touch-icon.png')
def apple_touch_icon():
    return send_file('apple-touch-icon.png')

@app.route('/favicon-32x32.png')
def favicon_32():
    return send_file('favicon-32x32.png')

@app.route('/favicon-16x16.png')
def favicon_16():
    return send_file('favicon-16x16.png')

@app.route('/site.webmanifest')
def site_manifest():
    return send_file('site.webmanifest')

@app.route('/android-chrome-192x192.png')
def android_chrome_192():
    return send_file('android-chrome-192x192.png')

@app.route('/android-chrome-512x512.png')
def android_chrome_512():
    return send_file('android-chrome-512x512.png')

if __name__ == '__main__':
    print("🧲 Starting Simple Magnet2Direct...")
    print(f"📁 Downloads folder: {DOWNLOAD_FOLDER}")
    print("🌐 Open http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
