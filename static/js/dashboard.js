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
    debuffFilter: document.getElementById('debuff-filter'),
    clearFilters: document.getElementById('clear-filters'),
    showUnknownFilter: document.getElementById('show-unknown-filter'),
    refreshBtn: document.getElementById('refresh-btn'),
    exportBtn: document.getElementById('export-btn'),
    abilitiesTable: document.querySelector('#abilities-table tbody'),
    debuffsTable: document.querySelector('#debuffs-table tbody'),
    deathsTable: document.querySelector('#deaths-table tbody'),
    abilitiesSummary: document.getElementById('abilities-summary'),
    debuffsSummary: document.getElementById('debuffs-summary'),
    timelineContent: document.getElementById('timeline-content'),
    timelineDuration: document.getElementById('timeline-duration'),
    breakdownPrompt: document.getElementById('breakdown-prompt'),
    breakdownContent: document.getElementById('breakdown-content'),
    breakdownAbilityName: document.getElementById('breakdown-ability-name'),
    breakdownTableHead: document.querySelector('#breakdown-table thead'),
    breakdownTableBody: document.querySelector('#breakdown-table tbody'),
    debuffBreakdownPrompt: document.getElementById('debuff-breakdown-prompt'),
    debuffBreakdownContent: document.getElementById('debuff-breakdown-content'),
    debuffBreakdownName: document.getElementById('debuff-breakdown-name'),
    debuffBreakdownTableHead: document.querySelector('#debuff-breakdown-table thead'),
    debuffBreakdownTableBody: document.querySelector('#debuff-breakdown-table tbody'),
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
        if (e.key >= '1' && e.key <= '6') {
            const tabs = ['abilities', 'debuffs', 'deaths', 'timeline', 'breakdown', 'debuff-breakdown'];
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
    elements.debuffFilter.addEventListener('change', applyFilters);
    elements.searchFilter.addEventListener('input', debounce(applyFilters, 300));
    elements.showUnknownFilter.addEventListener('change', applyFilters);
    elements.clearFilters.addEventListener('click', clearAllFilters);
}

function clearAllFilters() {
    elements.searchFilter.value = '';
    elements.playerFilter.value = '';
    elements.abilityFilter.value = '';
    elements.debuffFilter.value = '';
    elements.showUnknownFilter.checked = false;
    applyFilters();
}

function applyFilters() {
    if (currentFight && currentAttempt) {
        loadAttemptDetails(currentFight, currentAttempt);
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

    // Populate ability and debuff filters
    populateAbilityFilter(data.ability_hits);
    populateDebuffFilter(data.debuffs_applied);

    // Get filters
    const searchFilter = elements.searchFilter.value.toLowerCase();
    const playerFilter = elements.playerFilter.value;
    const abilityFilter = elements.abilityFilter.value;
    const debuffFilter = elements.debuffFilter.value;
    const showUnknown = elements.showUnknownFilter.checked;

    renderAbilitiesTable(data.ability_hits, playerFilter, abilityFilter, searchFilter, showUnknown);
    renderDebuffsTable(data.debuffs_applied, playerFilter, debuffFilter, searchFilter, showUnknown);
    renderDeathsTable(data.deaths, searchFilter);
    renderTimeline(data, showUnknown);
    renderAbilityBreakdown(abilityFilter);
    renderDebuffBreakdown(debuffFilter);
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

// Populate debuff filter
function populateDebuffFilter(debuffs) {
    const currentValue = elements.debuffFilter.value;
    const uniqueDebuffs = [...new Set(debuffs.map(d => d.effect_name))].sort();

    elements.debuffFilter.innerHTML = '<option value="">All Debuffs</option>';

    uniqueDebuffs.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        elements.debuffFilter.appendChild(option);
    });

    elements.debuffFilter.value = currentValue;
}

// Render abilities table with sorting
function renderAbilitiesTable(abilities, playerFilter, abilityFilter, searchFilter = '', showUnknown = false) {
    let filtered = abilities;

    // Filter out unknown abilities unless showUnknown is checked
    if (!showUnknown) {
        filtered = filtered.filter(a => !a.ability_name.toLowerCase().includes('unknown'));
    }

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
function renderDebuffsTable(debuffs, playerFilter, debuffFilter, searchFilter = '', showUnknown = false) {
    let filtered = debuffs;

    // Filter out unknown debuffs unless showUnknown is checked
    if (!showUnknown) {
        filtered = filtered.filter(d => !d.effect_name.toLowerCase().includes('unknown'));
    }

    if (playerFilter) {
        filtered = filtered.filter(d => d.target_name === playerFilter);
    }
    if (debuffFilter) {
        filtered = filtered.filter(d => d.effect_name === debuffFilter);
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
function renderTimeline(data, showUnknown = false) {
    elements.timelineDuration.textContent = formatDuration(data.duration_seconds);

    // Combine all events and sort by relative time
    const events = [];

    // Filter abilities
    let abilities = data.ability_hits;
    if (!showUnknown) {
        abilities = abilities.filter(a => !a.ability_name.toLowerCase().includes('unknown'));
    }
    abilities.forEach(a => {
        events.push({
            type: 'ability',
            relative_time: a.relative_time_seconds,
            name: a.ability_name,
            target: a.target_name,
            value: a.damage,
        });
    });

    // Deaths are always shown
    data.deaths.forEach(d => {
        events.push({
            type: 'death',
            relative_time: d.relative_time_seconds,
            name: d.player_name,
            target: d.source_name || 'unknown',
            value: null,
        });
    });

    // Filter debuffs
    let debuffs = data.debuffs_applied;
    if (!showUnknown) {
        debuffs = debuffs.filter(d => !d.effect_name.toLowerCase().includes('unknown'));
    }
    debuffs.forEach(d => {
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

    // Group events with same type and name within 5 seconds
    const groupedEvents = groupTimelineEvents(events, 5);

    elements.timelineContent.innerHTML = '';

    if (groupedEvents.length === 0) {
        elements.timelineContent.innerHTML = '<div class="empty-state">No events</div>';
        return;
    }

    groupedEvents.forEach(group => {
        const div = document.createElement('div');
        div.className = `timeline-event ${group.type}`;

        let icon, details, valueStr;
        const uniqueCount = group.displayTargets.length;
        const targetList = group.displayTargets.join(', ');

        switch (group.type) {
            case 'ability':
                icon = 'A';
                if (group.isMultiRound) {
                    // Multi-round: same players hit multiple times
                    const roundsBadge = `<span class="event-count">x${group.rounds}</span>`;
                    details = `<strong>${group.name}</strong> ${roundsBadge} across ${uniqueCount} players`;
                    valueStr = group.totalValue.toLocaleString() + ' dmg';
                } else if (group.count > 1) {
                    // Single round hitting multiple targets
                    details = `<strong>${group.name}</strong> hit ${targetList}`;
                    valueStr = group.totalValue.toLocaleString() + ' dmg';
                } else {
                    // Single hit
                    details = `<strong>${group.name}</strong> hit ${targetList}`;
                    valueStr = group.totalValue.toLocaleString() + ' dmg';
                }
                break;
            case 'death':
                icon = 'D';
                if (group.isMultiRound) {
                    const roundsBadge = `<span class="event-count">x${group.rounds}</span>`;
                    details = `${uniqueCount} players ${roundsBadge} killed by <strong>${group.name}</strong>`;
                } else if (group.count > 1) {
                    details = `<strong>${targetList}</strong> killed by ${group.name}`;
                } else {
                    details = `<strong>${targetList}</strong> killed by ${group.name}`;
                }
                valueStr = '';
                break;
            case 'debuff':
                icon = 'B';
                if (group.isMultiRound) {
                    const roundsBadge = `<span class="event-count">x${group.rounds}</span>`;
                    details = `<strong>${group.name}</strong> ${roundsBadge} across ${uniqueCount} players`;
                } else if (group.count > 1) {
                    details = `<strong>${group.name}</strong> on ${targetList}`;
                } else {
                    details = `<strong>${group.name}</strong> on ${targetList}`;
                }
                valueStr = group.avgValue ? group.avgValue.toFixed(1) + 's' : '';
                break;
        }

        div.innerHTML = `
            <span class="time">${formatRelativeTime(group.relative_time)}</span>
            <span class="event-icon">${icon}</span>
            <span class="event-details">${details}</span>
            <span class="event-value">${valueStr}</span>
        `;

        elements.timelineContent.appendChild(div);
    });
}

// Group timeline events with same type and name within a time window
function groupTimelineEvents(events, windowSeconds) {
    if (events.length === 0) return [];

    const groups = [];
    let currentGroup = null;

    events.forEach(event => {
        // For deaths, we group by the killer (source), not the victim
        const groupKey = event.type === 'death' ? event.target : event.name;

        // Check if this event can be added to the current group
        // Use rolling window: compare against last event time, not first
        const canGroup = currentGroup &&
            currentGroup.type === event.type &&
            currentGroup.groupKey === groupKey &&
            (event.relative_time - currentGroup.lastEventTime) <= windowSeconds;

        if (canGroup) {
            // Add to current group
            currentGroup.count++;
            currentGroup.lastEventTime = event.relative_time; // Update rolling window
            const targetName = event.type === 'death' ? event.name : event.target;
            currentGroup.allTargets.push(targetName);
            currentGroup.uniqueTargets.add(targetName);
            if (event.value !== null) {
                currentGroup.totalValue += event.value;
            }
        } else {
            // Finalize current group and start new one
            if (currentGroup) {
                finalizeGroup(currentGroup);
                groups.push(currentGroup);
            }

            const targetName = event.type === 'death' ? event.name : event.target;
            currentGroup = {
                type: event.type,
                name: event.type === 'death' ? event.target : event.name,
                groupKey: groupKey,
                relative_time: event.relative_time,
                lastEventTime: event.relative_time, // Track last event for rolling window
                count: 1,
                allTargets: [targetName],
                uniqueTargets: new Set([targetName]),
                totalValue: event.value || 0,
                avgValue: 0,
                // These will be set by finalizeGroup
                displayTargets: [],
                rounds: 1,
                isMultiRound: false,
            };
        }
    });

    // Don't forget the last group
    if (currentGroup) {
        finalizeGroup(currentGroup);
        groups.push(currentGroup);
    }

    return groups;
}

// Finalize a group by calculating display properties
function finalizeGroup(group) {
    group.avgValue = group.count > 0 ? group.totalValue / group.count : 0;

    const uniqueCount = group.uniqueTargets.size;
    const totalCount = group.count;

    // Check if this is a multi-round pattern (same players hit multiple times)
    if (totalCount > uniqueCount && totalCount % uniqueCount === 0) {
        group.rounds = totalCount / uniqueCount;
        group.isMultiRound = true;
        group.displayTargets = Array.from(group.uniqueTargets);
    } else {
        group.rounds = 1;
        group.isMultiRound = false;
        group.displayTargets = Array.from(group.uniqueTargets);
    }
}

// Render ability breakdown across all attempts
async function renderAbilityBreakdown(selectedAbility) {
    // If no specific ability selected, show prompt
    if (!selectedAbility || !currentFight) {
        elements.breakdownPrompt.style.display = 'block';
        elements.breakdownContent.style.display = 'none';
        return;
    }

    // Show content, hide prompt
    elements.breakdownPrompt.style.display = 'none';
    elements.breakdownContent.style.display = 'block';
    elements.breakdownAbilityName.textContent = selectedAbility;

    // Fetch fight data to get all attempts
    const fightData = await fetchAPI(`/api/fights/${currentFight}`);
    if (!fightData || !fightData.attempts) {
        elements.breakdownTableBody.innerHTML = '<tr><td colspan="100%" class="empty-state">No data available</td></tr>';
        return;
    }

    // Collect all unique players across all attempts
    const allPlayers = new Set();
    const attemptData = [];

    fightData.attempts.forEach(attempt => {
        const hitsByPlayer = {};

        attempt.ability_hits.forEach(hit => {
            if (hit.ability_name === selectedAbility) {
                allPlayers.add(hit.target_name);
                hitsByPlayer[hit.target_name] = (hitsByPlayer[hit.target_name] || 0) + 1;
            }
        });

        attemptData.push({
            attemptNumber: attempt.attempt_number,
            outcome: attempt.outcome,
            hitsByPlayer: hitsByPlayer
        });
    });

    const playerList = Array.from(allPlayers).sort();

    // If no hits found for this ability
    if (playerList.length === 0) {
        elements.breakdownTableHead.innerHTML = '';
        elements.breakdownTableBody.innerHTML = '<tr><td class="empty-state">No hits recorded for this ability</td></tr>';
        return;
    }

    // Build header row
    let headerHtml = '<tr><th>Attempt</th>';
    playerList.forEach(player => {
        headerHtml += `<th>${player}</th>`;
    });
    headerHtml += '<th>Total</th></tr>';
    elements.breakdownTableHead.innerHTML = headerHtml;

    // Build data rows
    let bodyHtml = '';
    attemptData.forEach(attempt => {
        const outcomeClass = attempt.outcome === 'victory' ? 'victory' : (attempt.outcome === 'wipe' ? 'wipe' : '');
        bodyHtml += `<tr>`;
        bodyHtml += `<td class="attempt-cell ${outcomeClass}">#${attempt.attemptNumber}</td>`;

        let rowTotal = 0;
        playerList.forEach(player => {
            const count = attempt.hitsByPlayer[player] || 0;
            rowTotal += count;
            bodyHtml += `<td class="count-cell ${count > 0 ? 'has-hits' : ''}">${count || ''}</td>`;
        });

        bodyHtml += `<td class="total-cell">${rowTotal || ''}</td>`;
        bodyHtml += '</tr>';
    });

    // Add totals row
    bodyHtml += '<tr class="totals-row"><td><strong>Total</strong></td>';
    let grandTotal = 0;
    playerList.forEach(player => {
        let playerTotal = 0;
        attemptData.forEach(attempt => {
            playerTotal += attempt.hitsByPlayer[player] || 0;
        });
        grandTotal += playerTotal;
        bodyHtml += `<td class="total-cell">${playerTotal || ''}</td>`;
    });
    bodyHtml += `<td class="total-cell grand-total">${grandTotal}</td></tr>`;

    elements.breakdownTableBody.innerHTML = bodyHtml;
}

// Render debuff breakdown across all attempts
async function renderDebuffBreakdown(selectedDebuff) {
    // If no specific debuff selected, show prompt
    if (!selectedDebuff || !currentFight) {
        elements.debuffBreakdownPrompt.style.display = 'block';
        elements.debuffBreakdownContent.style.display = 'none';
        return;
    }

    // Show content, hide prompt
    elements.debuffBreakdownPrompt.style.display = 'none';
    elements.debuffBreakdownContent.style.display = 'block';
    elements.debuffBreakdownName.textContent = selectedDebuff;

    // Fetch fight data to get all attempts
    const fightData = await fetchAPI(`/api/fights/${currentFight}`);
    if (!fightData || !fightData.attempts) {
        elements.debuffBreakdownTableBody.innerHTML = '<tr><td colspan="100%" class="empty-state">No data available</td></tr>';
        return;
    }

    // Collect all unique players across all attempts
    const allPlayers = new Set();
    const attemptData = [];

    fightData.attempts.forEach(attempt => {
        const debuffsByPlayer = {};

        attempt.debuffs_applied.forEach(debuff => {
            if (debuff.effect_name === selectedDebuff) {
                allPlayers.add(debuff.target_name);
                debuffsByPlayer[debuff.target_name] = (debuffsByPlayer[debuff.target_name] || 0) + 1;
            }
        });

        attemptData.push({
            attemptNumber: attempt.attempt_number,
            outcome: attempt.outcome,
            debuffsByPlayer: debuffsByPlayer
        });
    });

    const playerList = Array.from(allPlayers).sort();

    // If no applications found for this debuff
    if (playerList.length === 0) {
        elements.debuffBreakdownTableHead.innerHTML = '';
        elements.debuffBreakdownTableBody.innerHTML = '<tr><td class="empty-state">No applications recorded for this debuff</td></tr>';
        return;
    }

    // Build header row
    let headerHtml = '<tr><th>Attempt</th>';
    playerList.forEach(player => {
        headerHtml += `<th>${player}</th>`;
    });
    headerHtml += '<th>Total</th></tr>';
    elements.debuffBreakdownTableHead.innerHTML = headerHtml;

    // Build data rows
    let bodyHtml = '';
    attemptData.forEach(attempt => {
        const outcomeClass = attempt.outcome === 'victory' ? 'victory' : (attempt.outcome === 'wipe' ? 'wipe' : '');
        bodyHtml += `<tr>`;
        bodyHtml += `<td class="attempt-cell ${outcomeClass}">#${attempt.attemptNumber}</td>`;

        let rowTotal = 0;
        playerList.forEach(player => {
            const count = attempt.debuffsByPlayer[player] || 0;
            rowTotal += count;
            bodyHtml += `<td class="count-cell ${count > 0 ? 'has-hits' : ''}">${count || ''}</td>`;
        });

        bodyHtml += `<td class="total-cell">${rowTotal || ''}</td>`;
        bodyHtml += '</tr>';
    });

    // Add totals row
    bodyHtml += '<tr class="totals-row"><td><strong>Total</strong></td>';
    let grandTotal = 0;
    playerList.forEach(player => {
        let playerTotal = 0;
        attemptData.forEach(attempt => {
            playerTotal += attempt.debuffsByPlayer[player] || 0;
        });
        grandTotal += playerTotal;
        bodyHtml += `<td class="total-cell">${playerTotal || ''}</td>`;
    });
    bodyHtml += `<td class="total-cell grand-total">${grandTotal}</td></tr>`;

    elements.debuffBreakdownTableBody.innerHTML = bodyHtml;
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
