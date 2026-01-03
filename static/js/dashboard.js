/**
 * FFXIV Battle Tracker - Dashboard JavaScript
 */

// State
let currentFight = null;
let currentAttempt = null;
let sessionData = null;
let fightsData = null;
let attemptData = null;
let isRefreshing = false;
let sortColumn = null;
let sortDirection = 'asc';
let expandedFights = new Set();

// DOM Elements
const elements = {
    zoneName: document.getElementById('zone-name'),
    bossName: document.getElementById('boss-name'),
    parserState: document.getElementById('parser-state'),
    totalFights: document.getElementById('total-fights'),
    totalAttempts: document.getElementById('total-attempts'),
    totalWipes: document.getElementById('total-wipes'),
    totalVictories: document.getElementById('total-victories'),
    totalDamage: document.getElementById('total-damage'),
    totalDeaths: document.getElementById('total-deaths'),
    avgDuration: document.getElementById('avg-duration'),
    fightsList: document.getElementById('fights-list'),
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
    loadFights();
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
    if (!fightsData || fightsData.length === 0) return;
    if (!currentFight) return;

    // Find current fight
    const fightIndex = fightsData.findIndex(f => f.fight_id === currentFight);
    if (fightIndex === -1) return;

    const currentFightData = fightsData[fightIndex];
    const totalAttempts = currentFightData.total_attempts;

    if (totalAttempts === 0) return;

    let newAttempt = currentAttempt + direction;

    // Navigate within current fight
    if (newAttempt >= 1 && newAttempt <= totalAttempts) {
        selectAttempt(currentFight, newAttempt);
    } else if (newAttempt < 1 && fightIndex > 0) {
        // Go to previous fight's last attempt
        const prevFight = fightsData[fightIndex - 1];
        expandedFights.add(prevFight.fight_id);
        selectAttempt(prevFight.fight_id, prevFight.total_attempts);
        renderFightsList(fightsData);
    } else if (newAttempt > totalAttempts && fightIndex < fightsData.length - 1) {
        // Go to next fight's first attempt
        const nextFight = fightsData[fightIndex + 1];
        if (nextFight.total_attempts > 0) {
            expandedFights.add(nextFight.fight_id);
            selectAttempt(nextFight.fight_id, 1);
            renderFightsList(fightsData);
        }
    }
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
            await loadFights();
            await loadState();

            if (currentFight && currentAttempt) {
                await loadAttemptDetails(currentFight, currentAttempt);
            }

            showNotification(`Refreshed: ${data.lines_processed.toLocaleString()} lines, ${data.fights} fights, ${data.attempts} attempts`);
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

    elements.totalFights.textContent = data.total_fights || 0;
    elements.totalAttempts.textContent = data.total_attempts;
    elements.totalWipes.textContent = data.total_wipes;
    elements.totalVictories.textContent = data.total_victories;

    // Calculate extended stats
    const totalDeaths = Object.values(data.deaths_by_player).reduce((a, b) => a + b, 0);
    elements.totalDeaths.textContent = totalDeaths;

    // Load fights for duration and damage calculation
    const fightsDataResp = await fetchAPI('/api/fights');
    if (fightsDataResp && fightsDataResp.fights.length > 0) {
        let totalDuration = 0;
        let totalAttempts = 0;
        let totalDamage = 0;

        for (const fight of fightsDataResp.fights) {
            const fightDetails = await fetchAPI(`/api/fights/${fight.fight_id}`);
            if (fightDetails && fightDetails.attempts) {
                for (const attempt of fightDetails.attempts) {
                    totalDuration += attempt.duration_seconds || 0;
                    totalAttempts++;
                    if (attempt.ability_hits) {
                        totalDamage += attempt.ability_hits.reduce((sum, h) => sum + h.damage, 0);
                    }
                }
            }
        }

        const avgDuration = totalAttempts > 0 ? totalDuration / totalAttempts : 0;
        elements.avgDuration.textContent = formatDuration(avgDuration);
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

// Load fights list
async function loadFights() {
    const data = await fetchAPI('/api/fights');
    if (!data) return;

    fightsData = data.fights;
    renderFightsList(data.fights);

    // Auto-select first attempt of last fight if nothing selected
    if (data.fights.length > 0 && !currentAttempt) {
        const lastFight = data.fights[data.fights.length - 1];
        if (lastFight.total_attempts > 0) {
            expandedFights.add(lastFight.fight_id);
            selectAttempt(lastFight.fight_id, 1);
        }
    }
}

// Render fights list with nested attempts
function renderFightsList(fights) {
    elements.fightsList.innerHTML = '';

    if (fights.length === 0) {
        elements.fightsList.innerHTML = '<div class="empty-state"><p>No fights recorded</p></div>';
        return;
    }

    fights.forEach(fight => {
        const fightItem = document.createElement('div');
        fightItem.className = 'fight-item';
        fightItem.dataset.fightId = fight.fight_id;

        if (expandedFights.has(fight.fight_id)) {
            fightItem.classList.add('expanded');
        }

        // Fight header
        const header = document.createElement('div');
        header.className = 'fight-header';
        header.innerHTML = `
            <div class="fight-info">
                <div class="fight-zone">${fight.zone_name}</div>
                <div class="fight-boss">${fight.boss_name}</div>
            </div>
            <div class="fight-stats">
                <span class="fight-stat">${fight.total_attempts} attempts</span>
                <span class="fight-stat">${fight.total_deaths} deaths</span>
            </div>
            <span class="fight-toggle">▼</span>
        `;

        header.addEventListener('click', () => toggleFight(fight.fight_id));
        fightItem.appendChild(header);

        // Attempts list (hidden by default unless expanded)
        const attemptsList = document.createElement('div');
        attemptsList.className = 'attempts-list';
        attemptsList.style.display = expandedFights.has(fight.fight_id) ? 'flex' : 'none';

        // Load attempts for this fight
        loadFightAttempts(fight.fight_id, attemptsList);

        fightItem.appendChild(attemptsList);
        elements.fightsList.appendChild(fightItem);
    });
}

// Toggle fight expansion
function toggleFight(fightId) {
    const fightItem = document.querySelector(`.fight-item[data-fight-id="${fightId}"]`);
    const attemptsList = fightItem.querySelector('.attempts-list');

    if (expandedFights.has(fightId)) {
        expandedFights.delete(fightId);
        fightItem.classList.remove('expanded');
        attemptsList.style.display = 'none';
    } else {
        expandedFights.add(fightId);
        fightItem.classList.add('expanded');
        attemptsList.style.display = 'flex';
        loadFightAttempts(fightId, attemptsList);
    }
}

// Load attempts for a specific fight
async function loadFightAttempts(fightId, container) {
    const data = await fetchAPI(`/api/fights/${fightId}/attempts`);
    if (!data) return;

    container.innerHTML = '';

    if (data.attempts.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No attempts</p></div>';
        return;
    }

    data.attempts.forEach(attempt => {
        const item = document.createElement('div');
        item.className = 'attempt-item';
        item.dataset.fightId = fightId;
        item.dataset.attemptNumber = attempt.attempt_number;

        if (currentFight === fightId && currentAttempt === attempt.attempt_number) {
            item.classList.add('selected');
        }

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

        item.addEventListener('click', (e) => {
            e.stopPropagation();
            selectAttempt(fightId, attempt.attempt_number);
        });
        container.appendChild(item);
    });
}

// Select an attempt
function selectAttempt(fightId, attemptNumber) {
    currentFight = fightId;
    currentAttempt = attemptNumber;

    // Clear all selections
    document.querySelectorAll('.attempt-item').forEach(item => {
        item.classList.remove('selected');
    });

    // Select the current attempt
    const selectedItem = document.querySelector(
        `.attempt-item[data-fight-id="${fightId}"][data-attempt-number="${attemptNumber}"]`
    );
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }

    loadAttemptDetails(fightId, attemptNumber);
}

// Load attempt details
async function loadAttemptDetails(fightId, attemptNumber) {
    const data = await fetchAPI(`/api/fights/${fightId}/attempts/${attemptNumber}`);
    if (!data) return;

    attemptData = data;

    // Find the fight to get zone name
    const fight = fightsData?.find(f => f.fight_id === fightId);
    const zoneName = fight ? fight.zone_name : '';

    // Update header
    elements.attemptHeader.textContent = `Attempt #${data.attempt_number} - ${data.outcome.toUpperCase()}`;
    elements.attemptMeta.textContent = `${zoneName} - ${data.boss_name} - ${formatDuration(data.duration_seconds)} - ${formatTime(data.start_time)}`;

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
                    valA = a.relative_time_seconds;
                    valB = b.relative_time_seconds;
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
            <td>${formatRelativeTime(ability.relative_time_seconds)}</td>
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
            <td>${formatRelativeTime(debuff.relative_time_seconds)}</td>
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
            <td>${formatRelativeTime(death.relative_time_seconds)}</td>
            <td>${death.player_name}</td>
            <td>${death.source_name || '(unknown)'}</td>
        `;
        elements.deathsTable.appendChild(row);
    });
}

// Render timeline
function renderTimeline(data) {
    elements.timelineDuration.textContent = formatDuration(data.duration_seconds);

    // Combine all events and sort by relative time
    const events = [];

    data.ability_hits.forEach(a => {
        events.push({
            type: 'ability',
            relative_time: a.relative_time_seconds,
            name: a.ability_name,
            target: a.target_name,
            value: a.damage,
        });
    });

    data.deaths.forEach(d => {
        events.push({
            type: 'death',
            relative_time: d.relative_time_seconds,
            name: d.player_name,
            target: d.source_name || 'unknown',
            value: null,
        });
    });

    data.debuffs_applied.forEach(d => {
        events.push({
            type: 'debuff',
            relative_time: d.relative_time_seconds,
            name: d.effect_name,
            target: d.target_name,
            value: d.duration,
        });
    });

    // Sort by relative time
    events.sort((a, b) => a.relative_time - b.relative_time);

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
            <span class="time">${formatRelativeTime(event.relative_time)}</span>
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

function formatRelativeTime(seconds) {
    // Format relative time as MM:SS (fight time from 00:00)
    if (seconds === undefined || seconds === null) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}
