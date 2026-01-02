/**
 * FFXIV Battle Tracker - Dashboard JavaScript
 */

// State
let currentAttempt = null;
let sessionData = null;
let attemptData = null;
let isRefreshing = false;
let sortColumn = null;
let sortDirection = 'asc';

// DOM Elements
const elements = {
    zoneName: document.getElementById('zone-name'),
    bossName: document.getElementById('boss-name'),
    parserState: document.getElementById('parser-state'),
    totalAttempts: document.getElementById('total-attempts'),
    totalWipes: document.getElementById('total-wipes'),
    totalVictories: document.getElementById('total-victories'),
    totalDamage: document.getElementById('total-damage'),
    totalDeaths: document.getElementById('total-deaths'),
    avgDuration: document.getElementById('avg-duration'),
    attemptsList: document.getElementById('attempts-list'),
    deathsSummaryList: document.getElementById('deaths-summary-list'),
    attemptHeader: document.querySelector('#attempt-header h2'),
    attemptMeta: document.getElementById('attempt-meta'),
    searchFilter: document.getElementById('search-filter'),
    playerFilter: document.getElementById('player-filter'),
    abilityFilter: document.getElementById('ability-filter'),
    clearFilters: document.getElementById('clear-filters'),
    refreshBtn: document.getElementById('refresh-btn'),
    exportBtn: document.getElementById('export-btn'),
    abilitiesTable: document.querySelector('#abilities-table tbody'),
    debuffsTable: document.querySelector('#debuffs-table tbody'),
    deathsTable: document.querySelector('#deaths-table tbody'),
    abilitiesSummary: document.getElementById('abilities-summary'),
    debuffsSummary: document.getElementById('debuffs-summary'),
    timelineContent: document.getElementById('timeline-content'),
    timelineDuration: document.getElementById('timeline-duration'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFilters();
    initKeyboardShortcuts();
    initSorting();
    initExport();
    initRefresh();
    loadSession();
    loadSummary();
    loadAttempts();
    loadState();
});

// Keyboard shortcuts
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Don't trigger shortcuts when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
            if (e.key === 'Escape') {
                e.target.blur();
                clearAllFilters();
            }
            return;
        }

        // Tab switching with number keys
        if (e.key >= '1' && e.key <= '4') {
            const tabs = ['abilities', 'debuffs', 'deaths', 'timeline'];
            const tabIndex = parseInt(e.key) - 1;
            if (tabs[tabIndex]) {
                switchTab(tabs[tabIndex]);
            }
        }

        // Ctrl+R for refresh
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            refreshData();
        }

        // Ctrl+F for search
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            elements.searchFilter.focus();
        }

        // Ctrl+E for export
        if (e.ctrlKey && e.key === 'e') {
            e.preventDefault();
            exportData();
        }

        // Escape to clear filters
        if (e.key === 'Escape') {
            clearAllFilters();
        }

        // Arrow keys for attempt navigation
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            navigateAttempts(e.key === 'ArrowUp' ? -1 : 1);
        }
    });
}

function navigateAttempts(direction) {
    if (!sessionData || !sessionData.attempts) return;

    const attempts = sessionData.attempts;
    if (attempts.length === 0) return;

    const currentIndex = attempts.findIndex(a => a.attempt_number === currentAttempt);
    let newIndex = currentIndex + direction;

    if (newIndex < 0) newIndex = attempts.length - 1;
    if (newIndex >= attempts.length) newIndex = 0;

    selectAttempt(attempts[newIndex].attempt_number);
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Sorting
function initSorting() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (sortColumn === column) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'asc';
            }

            // Update header styles
            document.querySelectorAll('th.sortable').forEach(h => {
                h.classList.remove('asc', 'desc');
            });
            th.classList.add(sortDirection);

            // Re-render with sort
            if (currentAttempt && attemptData) {
                renderAbilitiesTable(attemptData.ability_hits,
                    elements.playerFilter.value,
                    elements.abilityFilter.value);
            }
        });
    });
}

// Export functionality
function initExport() {
    elements.exportBtn.addEventListener('click', exportData);
}

async function exportData() {
    try {
        const data = await fetchAPI('/api/session');
        if (!data) {
            showNotification('Export failed - no data');
            return;
        }

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ffxiv-battle-tracker-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showNotification('Data exported successfully');
    } catch (error) {
        console.error('Export failed:', error);
        showNotification('Export failed');
    }
}

// Manual refresh functionality
function initRefresh() {
    elements.refreshBtn.addEventListener('click', refreshData);
}

async function refreshData() {
    if (isRefreshing) return;

    isRefreshing = true;
    elements.refreshBtn.textContent = 'Refreshing...';
    elements.refreshBtn.disabled = true;

    try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const data = await response.json();

        if (response.ok && data.success) {
            // Reload all data
            await loadSession();
            await loadSummary();
            await loadAttempts();
            await loadState();

            if (currentAttempt) {
                await loadAttemptDetails(currentAttempt);
            }

            showNotification(`Refreshed: ${data.lines_processed.toLocaleString()} lines, ${data.attempts} attempts`);
        } else {
            showNotification(data.error || 'Refresh failed');
        }
    } catch (error) {
        console.error('Refresh failed:', error);
        showNotification('Refresh failed - check console');
    } finally {
        isRefreshing = false;
        elements.refreshBtn.textContent = 'Refresh';
        elements.refreshBtn.disabled = false;
    }
}

function showNotification(message) {
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Tab switching
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });
}

// Filter handling
function initFilters() {
    elements.playerFilter.addEventListener('change', applyFilters);
    elements.abilityFilter.addEventListener('change', applyFilters);
    elements.searchFilter.addEventListener('input', debounce(applyFilters, 300));
    elements.clearFilters.addEventListener('click', clearAllFilters);
}

function clearAllFilters() {
    elements.searchFilter.value = '';
    elements.playerFilter.value = '';
    elements.abilityFilter.value = '';
    applyFilters();
}

function applyFilters() {
    if (currentAttempt) {
        loadAttemptDetails(currentAttempt);
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// API calls
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch ${endpoint}:`, error);
        return null;
    }
}

// Load session info
async function loadSession() {
    const data = await fetchAPI('/api/session');
    if (!data) return;

    sessionData = data;
    elements.zoneName.textContent = data.zone_name || 'No zone';
    elements.bossName.textContent = data.boss_name ? `- ${data.boss_name}` : '';

    populatePlayerFilter(data.players);
}

// Load summary with extended stats
async function loadSummary() {
    const data = await fetchAPI('/api/summary');
    if (!data) return;

    elements.totalAttempts.textContent = data.total_attempts;
    elements.totalWipes.textContent = data.total_wipes;
    elements.totalVictories.textContent = data.total_victories;

    // Calculate extended stats
    const totalDeaths = Object.values(data.deaths_by_player).reduce((a, b) => a + b, 0);
    elements.totalDeaths.textContent = totalDeaths;

    // Load attempts for duration and damage calculation
    const attemptsData = await fetchAPI('/api/attempts');
    if (attemptsData && attemptsData.attempts.length > 0) {
        const attempts = attemptsData.attempts;
        const totalDuration = attempts.reduce((sum, a) => sum + (a.duration_seconds || 0), 0);
        const avgDuration = totalDuration / attempts.length;
        elements.avgDuration.textContent = formatDuration(avgDuration);

        // Calculate total damage from all attempts
        let totalDamage = 0;
        for (const attempt of attempts) {
            const details = await fetchAPI(`/api/attempts/${attempt.attempt_number}`);
            if (details && details.ability_hits) {
                totalDamage += details.ability_hits.reduce((sum, h) => sum + h.damage, 0);
            }
        }
        elements.totalDamage.textContent = totalDamage.toLocaleString();
    }

    renderDeathsSummary(data.deaths_by_player);
}

// Load parser state
async function loadState() {
    const data = await fetchAPI('/api/state');
    if (!data) return;

    elements.parserState.textContent = data.state;
    elements.parserState.className = `state-badge ${data.state}`;
}

// Load attempts list
async function loadAttempts() {
    const data = await fetchAPI('/api/attempts');
    if (!data) return;

    sessionData = { ...sessionData, attempts: data.attempts };
    renderAttemptsList(data.attempts);

    if (data.attempts.length > 0 && !currentAttempt) {
        const lastAttempt = data.attempts[data.attempts.length - 1];
        selectAttempt(lastAttempt.attempt_number);
    }
}

// Render attempts list
function renderAttemptsList(attempts) {
    elements.attemptsList.innerHTML = '';

    if (attempts.length === 0) {
        elements.attemptsList.innerHTML = '<div class="empty-state"><p>No attempts recorded</p></div>';
        return;
    }

    attempts.forEach(attempt => {
        const item = document.createElement('div');
        item.className = 'attempt-item';
        item.dataset.attemptNumber = attempt.attempt_number;

        const duration = formatDuration(attempt.duration_seconds);
        const time = formatTime(attempt.start_time);

        item.innerHTML = `
            <div class="attempt-header">
                <span class="attempt-number">Attempt #${attempt.attempt_number}</span>
                <span class="attempt-outcome ${attempt.outcome}">${attempt.outcome}</span>
            </div>
            <div class="attempt-details">
                ${time} - ${duration} - ${attempt.total_deaths} deaths
            </div>
        `;

        item.addEventListener('click', () => selectAttempt(attempt.attempt_number));
        elements.attemptsList.appendChild(item);
    });

    // Update selected state
    if (currentAttempt) {
        document.querySelectorAll('.attempt-item').forEach(item => {
            item.classList.toggle('selected', parseInt(item.dataset.attemptNumber) === currentAttempt);
        });
    }
}

// Select an attempt
function selectAttempt(attemptNumber) {
    currentAttempt = attemptNumber;

    document.querySelectorAll('.attempt-item').forEach(item => {
        item.classList.toggle('selected', parseInt(item.dataset.attemptNumber) === attemptNumber);
    });

    loadAttemptDetails(attemptNumber);
}

// Load attempt details
async function loadAttemptDetails(attemptNumber) {
    const data = await fetchAPI(`/api/attempts/${attemptNumber}`);
    if (!data) return;

    attemptData = data;

    // Update header
    elements.attemptHeader.textContent = `Attempt #${data.attempt_number} - ${data.outcome.toUpperCase()}`;
    elements.attemptMeta.textContent = `${data.boss_name} - ${formatDuration(data.duration_seconds)} - ${formatTime(data.start_time)}`;

    // Populate ability filter
    populateAbilityFilter(data.ability_hits);

    // Get filters
    const searchFilter = elements.searchFilter.value.toLowerCase();
    const playerFilter = elements.playerFilter.value;
    const abilityFilter = elements.abilityFilter.value;

    renderAbilitiesTable(data.ability_hits, playerFilter, abilityFilter, searchFilter);
    renderDebuffsTable(data.debuffs_applied, playerFilter, searchFilter);
    renderDeathsTable(data.deaths, searchFilter);
    renderTimeline(data);
}

// Populate player filter
function populatePlayerFilter(players) {
    const currentValue = elements.playerFilter.value;
    elements.playerFilter.innerHTML = '<option value="">All Players</option>';

    Object.values(players).forEach(player => {
        const option = document.createElement('option');
        option.value = player.name;
        option.textContent = player.name;
        elements.playerFilter.appendChild(option);
    });

    elements.playerFilter.value = currentValue;
}

// Populate ability filter
function populateAbilityFilter(abilities) {
    const currentValue = elements.abilityFilter.value;
    const uniqueAbilities = [...new Set(abilities.map(a => a.ability_name))].sort();

    elements.abilityFilter.innerHTML = '<option value="">All Abilities</option>';

    uniqueAbilities.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        elements.abilityFilter.appendChild(option);
    });

    elements.abilityFilter.value = currentValue;
}

// Render abilities table with sorting
function renderAbilitiesTable(abilities, playerFilter, abilityFilter, searchFilter = '') {
    let filtered = abilities;

    if (playerFilter) {
        filtered = filtered.filter(a => a.target_name === playerFilter);
    }
    if (abilityFilter) {
        filtered = filtered.filter(a => a.ability_name === abilityFilter);
    }
    if (searchFilter) {
        filtered = filtered.filter(a =>
            a.ability_name.toLowerCase().includes(searchFilter) ||
            a.target_name.toLowerCase().includes(searchFilter)
        );
    }

    // Sort if needed
    if (sortColumn) {
        filtered = [...filtered].sort((a, b) => {
            let valA, valB;
            switch (sortColumn) {
                case 'time':
                    valA = new Date(a.timestamp);
                    valB = new Date(b.timestamp);
                    break;
                case 'ability':
                    valA = a.ability_name.toLowerCase();
                    valB = b.ability_name.toLowerCase();
                    break;
                case 'target':
                    valA = a.target_name.toLowerCase();
                    valB = b.target_name.toLowerCase();
                    break;
                case 'damage':
                    valA = a.damage;
                    valB = b.damage;
                    break;
                default:
                    return 0;
            }
            if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    elements.abilitiesTable.innerHTML = '';

    if (filtered.length === 0) {
        elements.abilitiesTable.innerHTML = '<tr><td colspan="6" class="empty-state">No ability hits</td></tr>';
        elements.abilitiesSummary.innerHTML = '';
        return;
    }

    filtered.forEach(ability => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatTime(ability.timestamp)}</td>
            <td>${ability.ability_name}</td>
            <td>${ability.target_name}</td>
            <td class="damage-value">${ability.damage.toLocaleString()}</td>
            <td class="${ability.is_critical ? 'crit-yes' : ''}">${ability.is_critical ? 'Yes' : '-'}</td>
            <td class="${ability.is_direct_hit ? 'dh-yes' : ''}">${ability.is_direct_hit ? 'Yes' : '-'}</td>
        `;
        elements.abilitiesTable.appendChild(row);
    });

    renderAbilitiesSummary(filtered);
}

// Render abilities summary
function renderAbilitiesSummary(abilities) {
    const byAbility = {};
    abilities.forEach(a => {
        if (!byAbility[a.ability_name]) {
            byAbility[a.ability_name] = { count: 0, damage: 0 };
        }
        byAbility[a.ability_name].count++;
        byAbility[a.ability_name].damage += a.damage;
    });

    const sorted = Object.entries(byAbility).sort((a, b) => b[1].count - a[1].count);

    elements.abilitiesSummary.innerHTML = `
        <h3>Summary by Ability</h3>
        <div class="summary-grid">
            ${sorted.map(([name, data]) => `
                <div class="summary-item">
                    <span class="name">${name}</span>
                    <span class="value">${data.count} hits (${data.damage.toLocaleString()} dmg)</span>
                </div>
            `).join('')}
        </div>
    `;
}

// Render debuffs table
function renderDebuffsTable(debuffs, playerFilter, searchFilter = '') {
    let filtered = debuffs;

    if (playerFilter) {
        filtered = filtered.filter(d => d.target_name === playerFilter);
    }
    if (searchFilter) {
        filtered = filtered.filter(d =>
            d.effect_name.toLowerCase().includes(searchFilter) ||
            d.target_name.toLowerCase().includes(searchFilter)
        );
    }

    elements.debuffsTable.innerHTML = '';

    if (filtered.length === 0) {
        elements.debuffsTable.innerHTML = '<tr><td colspan="5" class="empty-state">No debuffs applied</td></tr>';
        elements.debuffsSummary.innerHTML = '';
        return;
    }

    filtered.forEach(debuff => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatTime(debuff.timestamp)}</td>
            <td>${debuff.effect_name}</td>
            <td>${debuff.target_name}</td>
            <td>${debuff.duration.toFixed(1)}s</td>
            <td>${debuff.stacks || '-'}</td>
        `;
        elements.debuffsTable.appendChild(row);
    });

    renderDebuffsSummary(filtered);
}

// Render debuffs summary
function renderDebuffsSummary(debuffs) {
    const byDebuff = {};
    debuffs.forEach(d => {
        if (!byDebuff[d.effect_name]) {
            byDebuff[d.effect_name] = 0;
        }
        byDebuff[d.effect_name]++;
    });

    const sorted = Object.entries(byDebuff).sort((a, b) => b[1] - a[1]);

    elements.debuffsSummary.innerHTML = `
        <h3>Summary by Debuff</h3>
        <div class="summary-grid">
            ${sorted.map(([name, count]) => `
                <div class="summary-item">
                    <span class="name">${name}</span>
                    <span class="value">${count} applications</span>
                </div>
            `).join('')}
        </div>
    `;
}

// Render deaths table
function renderDeathsTable(deaths, searchFilter = '') {
    let filtered = deaths;

    if (searchFilter) {
        filtered = filtered.filter(d =>
            d.player_name.toLowerCase().includes(searchFilter) ||
            (d.source_name && d.source_name.toLowerCase().includes(searchFilter))
        );
    }

    elements.deathsTable.innerHTML = '';

    if (filtered.length === 0) {
        elements.deathsTable.innerHTML = '<tr><td colspan="3" class="empty-state">No deaths</td></tr>';
        return;
    }

    filtered.forEach(death => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatTime(death.timestamp)}</td>
            <td>${death.player_name}</td>
            <td>${death.source_name || '(unknown)'}</td>
        `;
        elements.deathsTable.appendChild(row);
    });
}

// Render timeline
function renderTimeline(data) {
    elements.timelineDuration.textContent = formatDuration(data.duration_seconds);

    // Combine all events and sort by time
    const events = [];

    data.ability_hits.forEach(a => {
        events.push({
            type: 'ability',
            timestamp: a.timestamp,
            name: a.ability_name,
            target: a.target_name,
            value: a.damage,
        });
    });

    data.deaths.forEach(d => {
        events.push({
            type: 'death',
            timestamp: d.timestamp,
            name: d.player_name,
            target: d.source_name || 'unknown',
            value: null,
        });
    });

    data.debuffs_applied.forEach(d => {
        events.push({
            type: 'debuff',
            timestamp: d.timestamp,
            name: d.effect_name,
            target: d.target_name,
            value: d.duration,
        });
    });

    // Sort by timestamp
    events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Limit to last 50 events for performance
    const displayEvents = events.slice(-50);

    elements.timelineContent.innerHTML = '';

    if (displayEvents.length === 0) {
        elements.timelineContent.innerHTML = '<div class="empty-state">No events</div>';
        return;
    }

    displayEvents.forEach(event => {
        const div = document.createElement('div');
        div.className = `timeline-event ${event.type}`;

        let icon, details, valueStr;
        switch (event.type) {
            case 'ability':
                icon = 'A';
                details = `<strong>${event.name}</strong> hit ${event.target}`;
                valueStr = event.value.toLocaleString() + ' dmg';
                break;
            case 'death':
                icon = 'D';
                details = `<strong>${event.name}</strong> killed by ${event.target}`;
                valueStr = '';
                break;
            case 'debuff':
                icon = 'B';
                details = `<strong>${event.name}</strong> on ${event.target}`;
                valueStr = event.value ? event.value.toFixed(1) + 's' : '';
                break;
        }

        div.innerHTML = `
            <span class="time">${formatTime(event.timestamp)}</span>
            <span class="event-icon">${icon}</span>
            <span class="event-details">${details}</span>
            <span class="event-value">${valueStr}</span>
        `;

        elements.timelineContent.appendChild(div);
    });
}

// Render deaths summary
function renderDeathsSummary(deathsByPlayer) {
    elements.deathsSummaryList.innerHTML = '';

    const sorted = Object.entries(deathsByPlayer).sort((a, b) => b[1] - a[1]);

    if (sorted.length === 0) {
        elements.deathsSummaryList.innerHTML = '<div class="empty-state"><p>No deaths recorded</p></div>';
        return;
    }

    sorted.forEach(([player, count]) => {
        const item = document.createElement('div');
        item.className = 'death-summary-item';
        item.innerHTML = `
            <span class="player-name">${player}</span>
            <span class="death-count">${count}</span>
        `;
        elements.deathsSummaryList.appendChild(item);
    });
}

// Utility functions
function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour12: false });
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}
