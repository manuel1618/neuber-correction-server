// static/js/main.js
// Utility functions for the Neuber Correction application

/**
 * Format a number to a specified number of decimal places
 * @param {number} num - The number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted number
 */
function formatNumber(num, decimals = 2) {
    return Number(num).toFixed(decimals);
}

/**
 * Calculate percentage reduction between two values
 * @param {number} original - Original value
 * @param {number} corrected - Corrected value
 * @returns {string} Percentage reduction with 2 decimal places
 */
function calculateReduction(original, corrected) {
    return ((original - corrected) / original * 100).toFixed(2);
}

/**
 * Validate stress values input
 * @param {string} input - Comma-separated stress values
 * @returns {Array<number>} Array of valid stress values
 */
function parseStressValues(input) {
    return input
        .split(',')
        .map(s => parseFloat(s.trim()))
        .filter(s => !isNaN(s) && s > 0);
}

/**
 * Show loading state for a button
 * @param {HTMLElement} button - The button element
 * @param {string} loadingText - Text to show while loading
 */
function showLoadingState(button, loadingText = 'Loading...') {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
}

/**
 * Restore button to original state
 * @param {HTMLElement} button - The button element
 */
function restoreButtonState(button) {
    if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
        button.disabled = false;
    }
}
