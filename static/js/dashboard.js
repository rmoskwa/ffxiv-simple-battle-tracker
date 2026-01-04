/**
 * FFXIV Battle Tracker - Dashboard JavaScript
 */

// State
let currentFight = null;
let currentAttempt = null;
let sessionData = null;
let fightsData = null;
let attemptData = null;
let currentFightData = null;  // Cached data for the currently selected fight (includes players)
let isRefreshing = false;
let sortColumn = null;
let sortDirection = 'asc';
let expandedFights = new Set();
let selectedFightId = null;  // The fight selected in the header dropdown

// DOM Elements
const elements = {
    fightSelector: document.getElementById('fight-selector'),
    totalFights: document.getElementById('total-fights'),
    totalAttempts: document.getElementById('total-attempts'),
    totalWipes: document.getElementById('total-wipes'),
    totalDeaths: document.getElementById('total-deaths'),
    avgDuration: document.getElementById('avg-duration'),
    fightsList: document.getElementById('fights-list'),
    attemptHeader: document.querySelector('#attempt-header h2'),
    attemptMeta: document.getElementById('attempt-meta'),
    // Abilities tab filters
    abilitiesPlayerFilter: document.getElementById('abilities-player-filter'),
    abilitiesAbilityFilter: document.getElementById('abilities-ability-filter'),
    // Debuffs tab filters
    debuffsPlayerFilter: document.getElementById('debuffs-player-filter'),
    debuffsDebuffFilter: document.getElementById('debuffs-debuff-filter'),
    // Deaths tab filters
    deathsPlayerFilter: document.getElementById('deaths-player-filter'),
    // Global options
    showUnknownFilter: document.getElementById('show-unknown-filter'),
    refreshBtn: document.getElementById('refresh-btn'),
    abilitiesTable: document.querySelector('#abilities-table tbody'),
    debuffsTable: document.querySelector('#debuffs-table tbody'),
    deathsTable: document.querySelector('#deaths-table tbody'),
    // Timeline tab filter
    timelineEventFilter: document.getElementById('timeline-event-filter'),
    timelineSimplifiedToggle: document.getElementById('timeline-simplified-toggle'),
    timelineContainer: document.getElementById('timeline-container'),
    timelineContent: document.getElementById('timeline-content'),
    timelineDuration: document.getElementById('timeline-duration'),
    simplifiedTimelineContainer: document.getElementById('simplified-timeline-container'),
    simplifiedTimelineContent: document.getElementById('simplified-timeline-content'),
    simplifiedTimelineDuration: document.getElementById('simplified-timeline-duration'),
    guessTimelineBtn: document.getElementById('guess-timeline-btn'),
    bestGuessTimelineContainer: document.getElementById('best-guess-timeline-container'),
    bestGuessTimelineContent: document.getElementById('best-guess-timeline-content'),
    bestGuessAttemptCount: document.getElementById('best-guess-attempt-count'),
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
    // Breakdown-specific filters (populated from all attempts)
    breakdownAbilityFilter: document.getElementById('breakdown-ability-filter'),
    breakdownDebuffFilter: document.getElementById('breakdown-debuff-filter'),
    // Manual Hit Type Modal
    manualHitTypeBtn: document.getElementById('manual-hit-type-btn'),
    hitTypeModal: document.getElementById('hit-type-modal'),
    hitTypeModalClose: document.getElementById('hit-type-modal-close'),
    hitTypeTableBody: document.getElementById('hit-type-table-body'),
    hitTypeCancelBtn: document.getElementById('hit-type-cancel-btn'),
    hitTypeConfirmBtn: document.getElementById('hit-type-confirm-btn'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFilters();
    initKeyboardShortcuts();
    initSorting();
    initRefresh();
    initFightSelector();
    initManualHitTypeModal();
    loadSession();
    loadFights();
});

// Fight selector initialization
function initFightSelector() {
    elements.fightSelector.addEventListener('change', () => {
        const value = elements.fightSelector.value;
        selectedFightId = value ? parseInt(value) : null;

        // Clear current selection
        currentFight = null;
        currentAttempt = null;
        expandedFights.clear();

        // Re-render the fights list for the selected fight
        if (fightsData) {
            renderFightsList(fightsData);

            // Auto-select first attempt of the selected fight
            if (selectedFightId) {
                const selectedFight = fightsData.find(f => f.fight_id === selectedFightId);
                if (selectedFight && selectedFight.total_attempts > 0) {
                    expandedFights.add(selectedFight.fight_id);
                    selectAttempt(selectedFight.fight_id, 1);
                    renderFightsList(fightsData);
                }
            }
        }

        // Update summary for selected fight
        loadSummary();
    });
}

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

    // Navigate within current fight only (since we have a fight selector now)
    if (newAttempt >= 1 && newAttempt <= totalAttempts) {
        selectAttempt(currentFight, newAttempt);
    }
    // Wrap around within the selected fight
    else if (newAttempt < 1) {
        selectAttempt(currentFight, totalAttempts);
    } else if (newAttempt > totalAttempts) {
        selectAttempt(currentFight, 1);
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
            // Save current selection to restore after refresh
            const prevSelectedFight = selectedFightId;
            const prevCurrentFight = currentFight;
            const prevCurrentAttempt = currentAttempt;

            // Reload all data
            await loadSession();
            await loadFights();  // This also calls loadSummary()

            // Try to restore selection, or re-select if fight still exists
            if (prevCurrentFight && prevCurrentAttempt) {
                // Check if the fight still exists
                const fightExists = fightsData && fightsData.some(f => f.fight_id === prevCurrentFight);
                if (fightExists) {
                    await loadAttemptDetails(prevCurrentFight, prevCurrentAttempt);
                }
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
    // Abilities tab filters
    elements.abilitiesPlayerFilter.addEventListener('change', applyAbilitiesFilters);
    elements.abilitiesAbilityFilter.addEventListener('change', applyAbilitiesFilters);

    // Debuffs tab filters
    elements.debuffsPlayerFilter.addEventListener('change', applyDebuffsFilters);
    elements.debuffsDebuffFilter.addEventListener('change', applyDebuffsFilters);

    // Deaths tab filters
    elements.deathsPlayerFilter.addEventListener('change', applyDeathsFilters);

    // Timeline tab filter
    elements.timelineEventFilter.addEventListener('change', applyTimelineFilters);
    elements.timelineSimplifiedToggle.addEventListener('change', applyTimelineFilters);

    // Global show unknown filter (affects abilities, debuffs, timeline)
    elements.showUnknownFilter.addEventListener('change', applyAllFilters);

    // Clear buttons for each tab
    document.querySelectorAll('.clear-tab-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            clearTabFilters(btn.dataset.tab);
        });
    });

    // Breakdown-specific filter listeners
    elements.breakdownAbilityFilter.addEventListener('change', () => {
        renderAbilityBreakdown(elements.breakdownAbilityFilter.value);
    });
    elements.breakdownDebuffFilter.addEventListener('change', () => {
        renderDebuffBreakdown(elements.breakdownDebuffFilter.value);
    });

    // Best guess timeline button
    elements.guessTimelineBtn.addEventListener('click', generateBestGuessTimeline);
}

function clearTabFilters(tab) {
    switch (tab) {
        case 'abilities':
            elements.abilitiesPlayerFilter.value = '';
            elements.abilitiesAbilityFilter.value = '';
            applyAbilitiesFilters();
            break;
        case 'debuffs':
            elements.debuffsPlayerFilter.value = '';
            elements.debuffsDebuffFilter.value = '';
            applyDebuffsFilters();
            break;
        case 'deaths':
            elements.deathsPlayerFilter.value = '';
            applyDeathsFilters();
            break;
        case 'timeline':
            elements.timelineEventFilter.value = '';
            elements.timelineSimplifiedToggle.checked = false;
            elements.bestGuessTimelineContainer.style.display = 'none';
            applyTimelineFilters();
            break;
    }
}

function applyAbilitiesFilters() {
    if (!attemptData) return;
    const playerFilter = elements.abilitiesPlayerFilter.value;
    const abilityFilter = elements.abilitiesAbilityFilter.value;
    const showUnknown = elements.showUnknownFilter.checked;
    renderAbilitiesTable(attemptData.ability_hits, playerFilter, abilityFilter, showUnknown);
}

function applyDebuffsFilters() {
    if (!attemptData) return;
    const playerFilter = elements.debuffsPlayerFilter.value;
    const debuffFilter = elements.debuffsDebuffFilter.value;
    const showUnknown = elements.showUnknownFilter.checked;
    renderDebuffsTable(attemptData.debuffs_applied, playerFilter, debuffFilter, showUnknown);
}

function applyDeathsFilters() {
    if (!attemptData) return;
    const playerFilter = elements.deathsPlayerFilter.value;
    renderDeathsTable(attemptData.deaths, playerFilter);
}

function applyTimelineFilters() {
    if (!attemptData) return;
    const eventTypeFilter = elements.timelineEventFilter.value;
    const showUnknown = elements.showUnknownFilter.checked;
    const isSimplified = elements.timelineSimplifiedToggle.checked;

    if (isSimplified) {
        elements.timelineContainer.style.display = 'none';
        elements.simplifiedTimelineContainer.style.display = 'block';
        // Simplified view respects showUnknown but not event type filter
        renderSimplifiedTimeline(attemptData, showUnknown);
    } else {
        elements.timelineContainer.style.display = 'block';
        elements.simplifiedTimelineContainer.style.display = 'none';
        renderTimeline(attemptData, showUnknown, eventTypeFilter);
    }
}

function applyAllFilters() {
    applyAbilitiesFilters();
    applyDebuffsFilters();
    applyDeathsFilters();
    applyTimelineFilters();
}

function clearAllFilters() {
    elements.abilitiesPlayerFilter.value = '';
    elements.abilitiesAbilityFilter.value = '';
    elements.debuffsPlayerFilter.value = '';
    elements.debuffsDebuffFilter.value = '';
    elements.deathsPlayerFilter.value = '';
    elements.timelineEventFilter.value = '';
    elements.showUnknownFilter.checked = false;
    applyAllFilters();
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
}

// Load summary with extended stats
async function loadSummary() {
    // If a specific fight is selected, load stats for that fight only
    if (selectedFightId) {
        const fightData = await fetchAPI(`/api/fights/${selectedFightId}`);
        if (!fightData) return;

        // Cache fight data for job lookups in breakdown tables
        currentFightData = fightData;

        elements.totalFights.textContent = 1;
        elements.totalAttempts.textContent = fightData.total_attempts || 0;
        elements.totalWipes.textContent = fightData.total_wipes || 0;

        // Calculate stats from fight data
        let totalDuration = 0;
        const deathsByPlayer = {};

        if (fightData.attempts) {
            for (const attempt of fightData.attempts) {
                totalDuration += attempt.duration_seconds || 0;
                if (attempt.deaths) {
                    for (const death of attempt.deaths) {
                        deathsByPlayer[death.player_name] = (deathsByPlayer[death.player_name] || 0) + 1;
                    }
                }
            }
        }

        const totalDeaths = Object.values(deathsByPlayer).reduce((a, b) => a + b, 0);
        elements.totalDeaths.textContent = totalDeaths;

        const avgDuration = fightData.total_attempts > 0 ? totalDuration / fightData.total_attempts : 0;
        elements.avgDuration.textContent = formatDuration(avgDuration);
    } else {
        // No fight selected - show overall summary
        currentFightData = null;  // Clear cached fight data
        const data = await fetchAPI('/api/summary');
        if (!data) return;

        elements.totalFights.textContent = data.total_fights || 0;
        elements.totalAttempts.textContent = data.total_attempts;
        elements.totalWipes.textContent = data.total_wipes;

        // Calculate extended stats
        const totalDeaths = Object.values(data.deaths_by_player).reduce((a, b) => a + b, 0);
        elements.totalDeaths.textContent = totalDeaths;

        // Load fights for duration calculation
        const fightsDataResp = await fetchAPI('/api/fights');
        if (fightsDataResp && fightsDataResp.fights.length > 0) {
            let totalDuration = 0;
            let totalAttempts = 0;

            for (const fight of fightsDataResp.fights) {
                const fightDetails = await fetchAPI(`/api/fights/${fight.fight_id}`);
                if (fightDetails && fightDetails.attempts) {
                    for (const attempt of fightDetails.attempts) {
                        totalDuration += attempt.duration_seconds || 0;
                        totalAttempts++;
                    }
                }
            }

            const avgDuration = totalAttempts > 0 ? totalDuration / totalAttempts : 0;
            elements.avgDuration.textContent = formatDuration(avgDuration);
        }
    }
}

// Load fights list
async function loadFights() {
    const data = await fetchAPI('/api/fights');
    if (!data) return;

    fightsData = data.fights;

    // Populate the fight selector dropdown
    populateFightSelector(data.fights);

    // Check if current selectedFightId is still valid
    const fightsWithAttempts = data.fights.filter(f => f.total_attempts > 0);
    const selectedStillValid = selectedFightId && fightsWithAttempts.some(f => f.fight_id === selectedFightId);

    if (!selectedStillValid && fightsWithAttempts.length > 0) {
        // Auto-select last fight with attempts if nothing selected or selection invalid
        const lastFight = fightsWithAttempts[fightsWithAttempts.length - 1];
        selectedFightId = lastFight.fight_id;
        elements.fightSelector.value = lastFight.fight_id;
        expandedFights.clear();
        expandedFights.add(lastFight.fight_id);
        currentFight = lastFight.fight_id;
        currentAttempt = 1;
    } else if (selectedStillValid) {
        // Ensure dropdown reflects current selection
        elements.fightSelector.value = selectedFightId;
    }

    // Render the fights list
    renderFightsList(data.fights);

    // Auto-select first attempt if we have a selected fight but no attempt selected
    if (selectedFightId && !currentAttempt) {
        const selectedFight = fightsWithAttempts.find(f => f.fight_id === selectedFightId);
        if (selectedFight && selectedFight.total_attempts > 0) {
            expandedFights.add(selectedFight.fight_id);
            selectAttempt(selectedFight.fight_id, 1);
        }
    }

    // Update summary for selected fight
    loadSummary();
}

// Populate the fight selector dropdown
function populateFightSelector(fights) {
    const currentValue = elements.fightSelector.value;

    // Filter to only fights with attempts (actual boss encounters)
    const fightsWithAttempts = fights.filter(f => f.total_attempts > 0);

    elements.fightSelector.innerHTML = '';

    if (fightsWithAttempts.length === 0) {
        elements.fightSelector.innerHTML = '<option value="">No fights found</option>';
        return;
    }

    fightsWithAttempts.forEach(fight => {
        const option = document.createElement('option');
        option.value = fight.fight_id;
        // Show zone name and boss name (if different)
        const bossText = fight.boss_name && fight.boss_name !== fight.zone_name
            ? ` - ${fight.boss_name}`
            : '';
        option.textContent = `${fight.zone_name}${bossText} (${fight.total_attempts} attempts)`;
        elements.fightSelector.appendChild(option);
    });

    // Restore selection if still valid
    if (currentValue && fightsWithAttempts.some(f => f.fight_id === parseInt(currentValue))) {
        elements.fightSelector.value = currentValue;
    }
}

// Render fights list with nested attempts
function renderFightsList(fights) {
    elements.fightsList.innerHTML = '';

    // Filter to show only the selected fight if one is selected
    let displayFights = fights;
    if (selectedFightId) {
        displayFights = fights.filter(f => f.fight_id === selectedFightId);
    } else {
        // If no fight selected, only show fights with attempts
        displayFights = fights.filter(f => f.total_attempts > 0);
    }

    if (displayFights.length === 0) {
        elements.fightsList.innerHTML = '<div class="empty-state"><p>No fights recorded</p></div>';
        return;
    }

    displayFights.forEach(fight => {
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
                <div class="fight-attempts">${fight.total_attempts} attempts</div>
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

    // Filter out in_progress attempts (incomplete attempts from log end)
    const completedAttempts = data.attempts.filter(a => a.outcome !== 'in_progress');

    if (completedAttempts.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No attempts</p></div>';
        return;
    }

    completedAttempts.forEach(attempt => {
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

    // Populate tab-specific filters
    populateAbilitiesTabFilters(data);
    populateDebuffsTabFilters(data);
    populateDeathsTabFilters(data);

    // Populate breakdown-specific filters (all abilities/debuffs across all attempts)
    populateBreakdownAbilityFilter();
    populateBreakdownDebuffFilter();

    // Render all tables with current filter values
    const showUnknown = elements.showUnknownFilter.checked;
    renderAbilitiesTable(data.ability_hits, elements.abilitiesPlayerFilter.value, elements.abilitiesAbilityFilter.value, showUnknown);
    renderDebuffsTable(data.debuffs_applied, elements.debuffsPlayerFilter.value, elements.debuffsDebuffFilter.value, showUnknown);
    renderDeathsTable(data.deaths, elements.deathsPlayerFilter.value);
    // Use applyTimelineFilters to respect simplified view toggle
    applyTimelineFilters();

    // Breakdown tabs use their own dedicated dropdowns
    renderAbilityBreakdown(elements.breakdownAbilityFilter.value);
    renderDebuffBreakdown(elements.breakdownDebuffFilter.value);
}

// Populate abilities tab filters (player + ability)
function populateAbilitiesTabFilters(data) {
    // Get unique players from ability hits (targets that are players)
    const players = extractPlayersFromData(data);
    populatePlayerDropdown(elements.abilitiesPlayerFilter, players);

    // Populate ability filter
    const currentAbilityValue = elements.abilitiesAbilityFilter.value;
    const uniqueAbilities = [...new Set(data.ability_hits.map(a => a.ability_name))].sort();
    elements.abilitiesAbilityFilter.innerHTML = '<option value="">All Abilities</option>';
    uniqueAbilities.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        elements.abilitiesAbilityFilter.appendChild(option);
    });
    if (uniqueAbilities.includes(currentAbilityValue)) {
        elements.abilitiesAbilityFilter.value = currentAbilityValue;
    }
}

// Populate debuffs tab filters (player + debuff)
function populateDebuffsTabFilters(data) {
    // Get unique players from debuffs (targets that are players)
    const players = extractPlayersFromData(data);
    populatePlayerDropdown(elements.debuffsPlayerFilter, players);

    // Populate debuff filter with optgroups
    const currentDebuffValue = elements.debuffsDebuffFilter.value;
    const debuffsByType = { environment: new Set(), enemy: new Set() };
    data.debuffs_applied.forEach(d => {
        const sourceType = d.source_type || 'enemy';
        debuffsByType[sourceType].add(d.effect_name);
    });

    elements.debuffsDebuffFilter.innerHTML = '<option value="">All Debuffs</option>';

    if (debuffsByType.environment.size > 0) {
        const mechGroup = document.createElement('optgroup');
        mechGroup.label = 'Mechanic';
        [...debuffsByType.environment].sort().forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            mechGroup.appendChild(option);
        });
        elements.debuffsDebuffFilter.appendChild(mechGroup);
    }

    if (debuffsByType.enemy.size > 0) {
        const enemyGroup = document.createElement('optgroup');
        enemyGroup.label = 'Enemy';
        [...debuffsByType.enemy].sort().forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            enemyGroup.appendChild(option);
        });
        elements.debuffsDebuffFilter.appendChild(enemyGroup);
    }

    // Restore selection if valid
    const allDebuffs = [...debuffsByType.environment, ...debuffsByType.enemy];
    if (allDebuffs.includes(currentDebuffValue)) {
        elements.debuffsDebuffFilter.value = currentDebuffValue;
    }
}

// Populate deaths tab filters (player only)
function populateDeathsTabFilters(data) {
    const players = extractPlayersFromData(data);
    populatePlayerDropdown(elements.deathsPlayerFilter, players);
}

// Helper: Extract players from attempt data
function extractPlayersFromData(data) {
    const participantNames = new Set();
    const playerInfo = {};

    // From ability hits
    if (data.ability_hits) {
        data.ability_hits.forEach(hit => {
            if (hit.target_id && hit.target_id.startsWith('10') && hit.target_name) {
                participantNames.add(hit.target_name);
            }
        });
    }

    // From debuffs
    if (data.debuffs_applied) {
        data.debuffs_applied.forEach(debuff => {
            if (debuff.target_id && debuff.target_id.startsWith('10') && debuff.target_name) {
                participantNames.add(debuff.target_name);
            }
        });
    }

    // From deaths
    if (data.deaths) {
        data.deaths.forEach(death => {
            if (death.player_name) {
                participantNames.add(death.player_name);
            }
        });
    }

    // Get job info from current fight data
    if (currentFightData && currentFightData.players) {
        Object.values(currentFightData.players).forEach(p => {
            if (participantNames.has(p.name)) {
                playerInfo[p.name] = p.job_name || '';
            }
        });
    }

    return Array.from(participantNames).map(name => ({
        name,
        job_name: playerInfo[name] || ''
    }));
}

// Helper: Populate a player dropdown
function populatePlayerDropdown(selectElement, players) {
    const currentValue = selectElement.value;
    selectElement.innerHTML = '<option value="">All Players</option>';

    // Sort by job name then player name
    const sorted = players.sort((a, b) => {
        const jobCompare = (a.job_name || '').localeCompare(b.job_name || '');
        if (jobCompare !== 0) return jobCompare;
        return a.name.localeCompare(b.name);
    });

    sorted.forEach(player => {
        const option = document.createElement('option');
        option.value = player.name;
        const jobLabel = player.job_name ? ` (${player.job_name})` : '';
        option.textContent = `${player.name}${jobLabel}`;
        selectElement.appendChild(option);
    });

    // Restore selection if still valid
    const validNames = players.map(p => p.name);
    if (validNames.includes(currentValue)) {
        selectElement.value = currentValue;
    }
}

// Populate breakdown ability filter from ALL attempts in the current fight
async function populateBreakdownAbilityFilter() {
    if (!currentFight) {
        elements.breakdownAbilityFilter.innerHTML = '<option value="">Select an ability...</option>';
        return;
    }

    const currentValue = elements.breakdownAbilityFilter.value;

    // Fetch fight data to get all attempts
    const fightData = await fetchAPI(`/api/fights/${currentFight}`);
    if (!fightData || !fightData.attempts) {
        elements.breakdownAbilityFilter.innerHTML = '<option value="">No abilities found</option>';
        return;
    }

    // Collect all unique abilities across all attempts
    const allAbilities = new Set();
    const showUnknown = elements.showUnknownFilter.checked;

    fightData.attempts.forEach(attempt => {
        if (attempt.ability_hits) {
            attempt.ability_hits.forEach(hit => {
                // Filter out unknown abilities unless showUnknown is checked
                if (showUnknown || !hit.ability_name.toLowerCase().includes('unknown')) {
                    allAbilities.add(hit.ability_name);
                }
            });
        }
    });

    const sortedAbilities = [...allAbilities].sort();

    elements.breakdownAbilityFilter.innerHTML = '<option value="">Select an ability...</option>';

    sortedAbilities.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        elements.breakdownAbilityFilter.appendChild(option);
    });

    // Restore selection if still valid
    if (currentValue && allAbilities.has(currentValue)) {
        elements.breakdownAbilityFilter.value = currentValue;
    }
}

// Populate breakdown debuff filter from ALL attempts in the current fight
async function populateBreakdownDebuffFilter() {
    if (!currentFight) {
        elements.breakdownDebuffFilter.innerHTML = '<option value="">Select a debuff...</option>';
        return;
    }

    const currentValue = elements.breakdownDebuffFilter.value;

    // Fetch fight data to get all attempts
    const fightData = await fetchAPI(`/api/fights/${currentFight}`);
    if (!fightData || !fightData.attempts) {
        elements.breakdownDebuffFilter.innerHTML = '<option value="">No debuffs found</option>';
        return;
    }

    // Collect all unique debuffs across all attempts, grouped by source type
    const debuffsByType = { environment: new Set(), enemy: new Set() };
    const showUnknown = elements.showUnknownFilter.checked;

    fightData.attempts.forEach(attempt => {
        if (attempt.debuffs_applied) {
            attempt.debuffs_applied.forEach(debuff => {
                // Filter out unknown debuffs unless showUnknown is checked
                if (showUnknown || !debuff.effect_name.toLowerCase().includes('unknown')) {
                    const sourceType = debuff.source_type || 'enemy';
                    debuffsByType[sourceType].add(debuff.effect_name);
                }
            });
        }
    });

    elements.breakdownDebuffFilter.innerHTML = '<option value="">Select a debuff...</option>';

    // Add Mechanic (environment) group first if there are any
    if (debuffsByType.environment.size > 0) {
        const mechGroup = document.createElement('optgroup');
        mechGroup.label = 'Mechanic';
        [...debuffsByType.environment].sort().forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            mechGroup.appendChild(option);
        });
        elements.breakdownDebuffFilter.appendChild(mechGroup);
    }

    // Add Enemy group
    if (debuffsByType.enemy.size > 0) {
        const enemyGroup = document.createElement('optgroup');
        enemyGroup.label = 'Enemy';
        [...debuffsByType.enemy].sort().forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            enemyGroup.appendChild(option);
        });
        elements.breakdownDebuffFilter.appendChild(enemyGroup);
    }

    // Restore selection if still valid
    const allDebuffs = new Set([...debuffsByType.environment, ...debuffsByType.enemy]);
    if (currentValue && allDebuffs.has(currentValue)) {
        elements.breakdownDebuffFilter.value = currentValue;
    }
}

// Render abilities table with sorting
function renderAbilitiesTable(abilities, playerFilter, abilityFilter, showUnknown = false) {
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
                case 'unmitigated':
                    valA = a.unmitigated_damage || 0;
                    valB = b.unmitigated_damage || 0;
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
        return;
    }

    filtered.forEach(ability => {
        const row = document.createElement('tr');
        // Format unmitigated damage - show N/A if not calculated yet
        const unmitigatedDisplay = ability.unmitigated_damage
            ? ability.unmitigated_damage.toLocaleString()
            : '<span class="not-available">N/A</span>';
        // Format hit type - show Unknown if not determined yet
        const hitTypeDisplay = ability.hit_type || '<span class="not-available">Unknown</span>';

        // Format damage with absorbed amount
        // Show "damage (absorbed)" if there was shield absorption
        let damageDisplay = ability.damage.toLocaleString();
        if (ability.absorbed_damage && ability.absorbed_damage > 0) {
            damageDisplay += ` <span class="absorbed-damage">(${ability.absorbed_damage.toLocaleString()})</span>`;
        }

        row.innerHTML = `
            <td>${formatRelativeTime(ability.relative_time_seconds)}</td>
            <td>${ability.ability_name}</td>
            <td>${ability.target_name}</td>
            <td class="damage-value">${damageDisplay}</td>
            <td class="damage-value">${unmitigatedDisplay}</td>
            <td>${hitTypeDisplay}</td>
        `;
        elements.abilitiesTable.appendChild(row);
    });
}

// Render debuffs table
function renderDebuffsTable(debuffs, playerFilter, debuffFilter, showUnknown = false) {
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

    elements.debuffsTable.innerHTML = '';

    if (filtered.length === 0) {
        elements.debuffsTable.innerHTML = '<tr><td colspan="5" class="empty-state">No debuffs applied</td></tr>';
        return;
    }

    filtered.forEach(debuff => {
        const row = document.createElement('tr');
        const sourceType = debuff.source_type || 'enemy';
        row.className = `source-${sourceType}`;
        row.innerHTML = `
            <td>${formatRelativeTime(debuff.relative_time_seconds)}</td>
            <td>${debuff.effect_name}</td>
            <td>${debuff.target_name}</td>
            <td>${debuff.duration.toFixed(1)}s</td>
            <td>${debuff.stacks || '-'}</td>
        `;
        elements.debuffsTable.appendChild(row);
    });
}

// Render deaths table
function renderDeathsTable(deaths, playerFilter = '') {
    let filtered = deaths;

    if (playerFilter) {
        filtered = filtered.filter(d => d.player_name === playerFilter);
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
function renderTimeline(data, showUnknown = false, eventTypeFilter = '') {
    elements.timelineDuration.textContent = formatDuration(data.duration_seconds);

    // Combine all events and sort by relative time
    const events = [];

    // Add abilities if not filtered out
    if (!eventTypeFilter || eventTypeFilter === 'ability') {
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
    }

    // Add deaths if not filtered out
    if (!eventTypeFilter || eventTypeFilter === 'death') {
        data.deaths.forEach(d => {
            events.push({
                type: 'death',
                relative_time: d.relative_time_seconds,
                name: d.player_name,
                target: d.source_name || 'unknown',
                value: null,
            });
        });
    }

    // Add debuffs if not filtered out (both environment and enemy sources)
    if (!eventTypeFilter || eventTypeFilter === 'debuff') {
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
                source_type: d.source_type || 'enemy',
            });
        });
    }

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
        // Add source-type class for debuffs (environment vs enemy)
        const sourceClass = group.type === 'debuff' && group.source_type ? `source-${group.source_type}` : '';
        div.className = `timeline-event ${group.type} ${sourceClass}`.trim();

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
                // Preserve source_type for debuffs
                source_type: event.source_type || null,
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

// Render simplified timeline - 3 columns (Abilities, Debuffs, Deaths) by timestamp
function renderSimplifiedTimeline(data, showUnknown = false) {
    elements.simplifiedTimelineDuration.textContent = formatDuration(data.duration_seconds);

    // Collect all events grouped by timestamp (floored to seconds)
    const eventsByTime = new Map();

    // Helper to add event to a timestamp
    const addEvent = (time, type, name, sourceType = null) => {
        const timeKey = Math.floor(time);
        if (!eventsByTime.has(timeKey)) {
            eventsByTime.set(timeKey, { abilities: [], debuffs: [], deaths: [] });
        }
        const events = eventsByTime.get(timeKey);

        if (type === 'ability') {
            // Check if ability already exists at this timestamp
            const existing = events.abilities.find(e => e.name === name);
            if (existing) {
                existing.count++;
            } else {
                events.abilities.push({ name, count: 1 });
            }
        } else if (type === 'debuff') {
            const existing = events.debuffs.find(e => e.name === name);
            if (existing) {
                existing.count++;
            } else {
                events.debuffs.push({ name, count: 1, sourceType });
            }
        } else if (type === 'death') {
            // For deaths, name is the player who died
            events.deaths.push({ name, count: 1 });
        }
    };

    // Filter abilities based on showUnknown setting
    let abilities = data.ability_hits;
    if (!showUnknown) {
        abilities = abilities.filter(a => !a.ability_name.toLowerCase().includes('unknown'));
    }

    // Filter debuffs based on showUnknown setting
    let debuffs = data.debuffs_applied;
    if (!showUnknown) {
        debuffs = debuffs.filter(d => !d.effect_name.toLowerCase().includes('unknown'));
    }

    // Add abilities (simplified: just ability name)
    abilities.forEach(a => {
        addEvent(a.relative_time_seconds, 'ability', a.ability_name);
    });

    // Add debuffs (simplified: just debuff name)
    debuffs.forEach(d => {
        addEvent(d.relative_time_seconds, 'debuff', d.effect_name, d.source_type);
    });

    // Add deaths (simplified: just player name)
    data.deaths.forEach(d => {
        addEvent(d.relative_time_seconds, 'death', d.player_name);
    });

    // Sort timestamps
    const sortedTimes = Array.from(eventsByTime.keys()).sort((a, b) => a - b);

    // Build the 3-column layout
    let html = `
        <div class="simplified-column abilities">
            <div class="simplified-column-header">Abilities</div>
            <div class="simplified-events-list">
    `;

    // Build rows for each timestamp
    sortedTimes.forEach(time => {
        const events = eventsByTime.get(time);
        const timeStr = formatRelativeTime(time);

        // Abilities column events
        if (events.abilities.length > 0) {
            events.abilities.forEach(evt => {
                html += `
                    <div class="simplified-event-row">
                        <span class="simplified-time">${timeStr}</span>
                        <div class="simplified-event-cell ability">
                            <span class="simplified-event-name">${evt.name}</span>
                        </div>
                    </div>
                `;
            });
        }
    });

    html += `
            </div>
        </div>
        <div class="simplified-column debuffs">
            <div class="simplified-column-header">Debuffs</div>
            <div class="simplified-events-list">
    `;

    // Debuffs column
    sortedTimes.forEach(time => {
        const events = eventsByTime.get(time);
        const timeStr = formatRelativeTime(time);

        if (events.debuffs.length > 0) {
            events.debuffs.forEach(evt => {
                const sourceClass = evt.sourceType === 'environment' ? 'source-environment' : '';
                html += `
                    <div class="simplified-event-row">
                        <span class="simplified-time">${timeStr}</span>
                        <div class="simplified-event-cell debuff ${sourceClass}">
                            <span class="simplified-event-name">${evt.name}</span>
                        </div>
                    </div>
                `;
            });
        }
    });

    html += `
            </div>
        </div>
        <div class="simplified-column deaths">
            <div class="simplified-column-header">Deaths</div>
            <div class="simplified-events-list">
    `;

    // Deaths column
    sortedTimes.forEach(time => {
        const events = eventsByTime.get(time);
        const timeStr = formatRelativeTime(time);

        if (events.deaths.length > 0) {
            events.deaths.forEach(evt => {
                html += `
                    <div class="simplified-event-row">
                        <span class="simplified-time">${timeStr}</span>
                        <div class="simplified-event-cell death">
                            <span class="simplified-event-name">${evt.name}</span>
                        </div>
                    </div>
                `;
            });
        }
    });

    html += `
            </div>
        </div>
    `;

    elements.simplifiedTimelineContent.innerHTML = html;

    // Handle empty state
    if (sortedTimes.length === 0) {
        elements.simplifiedTimelineContent.innerHTML = '<div class="empty-state">No events</div>';
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

    // Sort players by role (Tank -> Healer -> DPS) then by name
    const playerList = sortPlayersByRole(Array.from(allPlayers));

    // If no hits found for this ability
    if (playerList.length === 0) {
        elements.breakdownTableHead.innerHTML = '';
        elements.breakdownTableBody.innerHTML = '<tr><td class="empty-state">No hits recorded for this ability</td></tr>';
        return;
    }

    // Build header row with role-based coloring
    let headerHtml = '<tr><th>Attempt</th>';
    playerList.forEach(player => {
        const role = getPlayerRole(player);
        const roleClass = role ? `role-${role}` : '';
        headerHtml += `<th class="${roleClass}">${player}</th>`;
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

    // Sort players by role (Tank -> Healer -> DPS) then by name
    const playerList = sortPlayersByRole(Array.from(allPlayers));

    // If no applications found for this debuff
    if (playerList.length === 0) {
        elements.debuffBreakdownTableHead.innerHTML = '';
        elements.debuffBreakdownTableBody.innerHTML = '<tr><td class="empty-state">No applications recorded for this debuff</td></tr>';
        return;
    }

    // Build header row with role-based coloring
    let headerHtml = '<tr><th>Attempt</th>';
    playerList.forEach(player => {
        const role = getPlayerRole(player);
        const roleClass = role ? `role-${role}` : '';
        headerHtml += `<th class="${roleClass}">${player}</th>`;
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

// Get player job info from session or current fight data
function getPlayerJob(playerName) {
    // First check current fight's players (most relevant for multi-fight logs)
    if (currentFightData && currentFightData.players) {
        const fightPlayers = Object.values(currentFightData.players);
        const fightPlayer = fightPlayers.find(p => p.name === playerName);
        if (fightPlayer && fightPlayer.job_name) {
            return fightPlayer.job_name;
        }
    }

    // Fall back to session players
    if (sessionData && sessionData.players) {
        const players = Object.values(sessionData.players);
        const player = players.find(p => p.name === playerName);
        if (player && player.job_name) {
            return player.job_name;
        }
    }

    return null;
}

// Job role mappings
const TANK_JOBS = ['Paladin', 'Warrior', 'Dark Knight', 'Gunbreaker', 'Gladiator', 'Marauder'];
const HEALER_JOBS = ['White Mage', 'Scholar', 'Astrologian', 'Sage', 'Conjurer'];
const DPS_JOBS = [
    // Melee
    'Monk', 'Dragoon', 'Ninja', 'Samurai', 'Reaper', 'Viper', 'Pugilist', 'Lancer', 'Rogue',
    // Ranged
    'Bard', 'Machinist', 'Dancer', 'Archer',
    // Caster
    'Black Mage', 'Summoner', 'Red Mage', 'Pictomancer', 'Thaumaturge', 'Arcanist', 'Blue Mage'
];

// Get job role from job name
function getJobRole(jobName) {
    if (!jobName) return null;
    if (TANK_JOBS.includes(jobName)) return 'tank';
    if (HEALER_JOBS.includes(jobName)) return 'healer';
    if (DPS_JOBS.includes(jobName)) return 'dps';
    return null;
}

// Get job role for a player by name
function getPlayerRole(playerName) {
    const jobName = getPlayerJob(playerName);
    return getJobRole(jobName);
}

// Sort players by role (Tank -> Healer -> DPS) then by name
function sortPlayersByRole(players) {
    const roleOrder = { 'tank': 0, 'healer': 1, 'dps': 2 };
    return players.sort((a, b) => {
        const roleA = getPlayerRole(a) || 'zzz';
        const roleB = getPlayerRole(b) || 'zzz';
        const orderA = roleOrder[roleA] ?? 3;
        const orderB = roleOrder[roleB] ?? 3;
        if (orderA !== orderB) return orderA - orderB;
        return a.localeCompare(b);
    });
}

// Best Guess Timeline Generation
async function generateBestGuessTimeline() {
    if (!currentFight) {
        showNotification('Please select a fight first');
        return;
    }

    // Fetch fight data to get all attempts
    const fightData = await fetchAPI(`/api/fights/${currentFight}`);
    if (!fightData || !fightData.attempts) {
        showNotification('Failed to load fight data');
        return;
    }

    const attempts = fightData.attempts.filter(a => a.outcome !== 'in_progress');

    // Require at least 5 attempts
    if (attempts.length < 5) {
        showNotification(`Need at least 5 attempts (have ${attempts.length})`);
        return;
    }

    const showUnknown = elements.showUnknownFilter.checked;

    // Collect ordinal-matched events
    const abilityEvents = collectOrdinalMatchedEvents(attempts, 'ability_hits', 'ability_name', showUnknown);
    const debuffEvents = collectOrdinalMatchedEvents(attempts, 'debuffs_applied', 'effect_name', showUnknown);

    // Filter to events appearing in at least 3 attempts within ±10s of median
    const filteredAbilities = filterByConsensus(abilityEvents, 3, 10);
    const filteredDebuffs = filterByConsensus(debuffEvents, 3, 10);

    // Detect and merge choice points (±5s median tolerance)
    const mergedAbilities = detectChoicePoints(filteredAbilities, 5);
    const mergedDebuffs = detectChoicePoints(filteredDebuffs, 5);

    // Combine and sort by time
    const allEvents = [
        ...mergedAbilities.map(e => ({ ...e, type: 'ability' })),
        ...mergedDebuffs.map(e => ({ ...e, type: 'debuff' }))
    ].sort((a, b) => a.medianTime - b.medianTime);

    // Render the best guess timeline
    renderBestGuessTimeline(allEvents, attempts.length);
}

// Collect events matched by ordinal position across attempts
function collectOrdinalMatchedEvents(attempts, eventKey, nameKey, showUnknown) {
    // Get all unique event names
    const allNames = new Set();
    attempts.forEach(attempt => {
        const events = attempt[eventKey] || [];
        events.forEach(event => {
            const name = event[nameKey];
            if (showUnknown || !name.toLowerCase().includes('unknown')) {
                allNames.add(name);
            }
        });
    });

    const result = [];

    allNames.forEach(eventName => {
        // Get occurrences per attempt, sorted by time
        // Now also collect unmitigated damage for abilities
        const occurrencesByAttempt = new Map();
        let maxOrdinal = 0;

        attempts.forEach((attempt, attemptIdx) => {
            const events = attempt[eventKey] || [];
            // Get all matching events with time and damage info
            const matchingEvents = events
                .filter(e => e[nameKey] === eventName)
                .map(e => ({
                    time: e.relative_time_seconds,
                    damage: e.unmitigated_damage || 0  // Only ability_hits have this
                }))
                .sort((a, b) => a.time - b.time);

            // Deduplicate times within the same second (AoE abilities hit multiple players)
            // For damage, collect all damages at that second to average later
            const occurrences = [];
            let lastSecond = -1;
            let currentDamages = [];

            matchingEvents.forEach(evt => {
                const second = Math.floor(evt.time);
                if (second !== lastSecond) {
                    // Save previous occurrence if exists
                    if (currentDamages.length > 0 && occurrences.length > 0) {
                        // Calculate average damage for the previous second
                        const validDamages = currentDamages.filter(d => d > 0);
                        occurrences[occurrences.length - 1].avgDamage = validDamages.length > 0
                            ? Math.round(validDamages.reduce((a, b) => a + b, 0) / validDamages.length)
                            : 0;
                    }
                    // Start new occurrence
                    occurrences.push({ time: evt.time, avgDamage: 0 });
                    currentDamages = [evt.damage];
                    lastSecond = second;
                } else {
                    // Same second, collect damage
                    currentDamages.push(evt.damage);
                }
            });

            // Handle last occurrence
            if (currentDamages.length > 0 && occurrences.length > 0) {
                const validDamages = currentDamages.filter(d => d > 0);
                occurrences[occurrences.length - 1].avgDamage = validDamages.length > 0
                    ? Math.round(validDamages.reduce((a, b) => a + b, 0) / validDamages.length)
                    : 0;
            }

            occurrencesByAttempt.set(attemptIdx, occurrences);
            maxOrdinal = Math.max(maxOrdinal, occurrences.length);
        });

        // For each ordinal position, collect times and damages
        for (let ordinal = 0; ordinal < maxOrdinal; ordinal++) {
            const timesAtOrdinal = [];
            const damagesAtOrdinal = [];
            const attemptsWithOrdinal = [];

            occurrencesByAttempt.forEach((occurrences, attemptIdx) => {
                if (occurrences.length > ordinal) {
                    timesAtOrdinal.push(occurrences[ordinal].time);
                    damagesAtOrdinal.push(occurrences[ordinal].avgDamage);
                    attemptsWithOrdinal.push(attemptIdx);
                }
            });

            if (timesAtOrdinal.length > 0) {
                result.push({
                    name: eventName,
                    ordinal: ordinal + 1,
                    times: timesAtOrdinal,
                    damages: damagesAtOrdinal,
                    attempts: attemptsWithOrdinal
                });
            }
        }
    });

    return result;
}

// Filter events by consensus threshold
function filterByConsensus(events, minAttempts, toleranceSeconds) {
    return events.map(event => {
        const medianTime = calculateMedian(event.times);

        // Find attempts within tolerance of median
        const withinTolerance = [];
        const timesWithinTolerance = [];
        const damagesWithinTolerance = [];

        event.times.forEach((time, idx) => {
            if (Math.abs(time - medianTime) <= toleranceSeconds) {
                withinTolerance.push(event.attempts[idx]);
                timesWithinTolerance.push(time);
                // Include damage if available (only for abilities)
                if (event.damages && event.damages[idx] !== undefined) {
                    damagesWithinTolerance.push(event.damages[idx]);
                }
            }
        });

        // Calculate average unmitigated damage from valid (non-zero) damages
        const validDamages = damagesWithinTolerance.filter(d => d > 0);
        const avgDamage = validDamages.length > 0
            ? Math.round(validDamages.reduce((a, b) => a + b, 0) / validDamages.length)
            : 0;

        return {
            name: event.name,
            ordinal: event.ordinal,
            medianTime: calculateMedian(timesWithinTolerance),
            consensusCount: withinTolerance.length,
            attempts: new Set(withinTolerance),
            avgDamage: avgDamage
        };
    }).filter(event => event.consensusCount >= minAttempts);
}

// Detect choice points and merge alternative abilities
function detectChoicePoints(events, toleranceSeconds) {
    if (events.length === 0) return [];

    // Sort by median time
    const sorted = [...events].sort((a, b) => a.medianTime - b.medianTime);
    const merged = [];
    const processed = new Set();

    for (let i = 0; i < sorted.length; i++) {
        if (processed.has(i)) continue;

        const event = sorted[i];
        const alternatives = [event];

        // Look for other events with different names within tolerance
        for (let j = i + 1; j < sorted.length; j++) {
            if (processed.has(j)) continue;

            const other = sorted[j];

            // Check if medians are within tolerance
            if (Math.abs(event.medianTime - other.medianTime) > toleranceSeconds) {
                break; // Sorted by time, so no more candidates
            }

            // Check if different ability name
            if (event.name === other.name) continue;

            // Check if attempts are mostly disjoint (overlap < 30%)
            const intersection = new Set([...event.attempts].filter(x => other.attempts.has(x)));
            const minSize = Math.min(event.attempts.size, other.attempts.size);
            const overlapRatio = intersection.size / minSize;

            if (overlapRatio <= 0.3) {
                alternatives.push(other);
                processed.add(j);
            }
        }

        processed.add(i);

        if (alternatives.length === 1) {
            merged.push(event);
        } else {
            // Merge alternatives
            const allTimes = [];
            const allAttempts = new Set();

            // Sort alternatives by name to ensure consistent ordering
            const sortedAlternatives = [...alternatives].sort((a, b) => a.name.localeCompare(b.name));
            const names = sortedAlternatives.map(a => a.name);
            // Collect damages in the same order as names
            const damages = sortedAlternatives.map(a => a.avgDamage || 0);

            sortedAlternatives.forEach(alt => {
                // We need the original times, but we only have medianTime
                // Use the median as representative
                allTimes.push(alt.medianTime);
                alt.attempts.forEach(a => allAttempts.add(a));
            });

            merged.push({
                name: names.join(' / '),
                ordinal: null, // Mixed ordinals
                medianTime: calculateMedian(allTimes),
                consensusCount: allAttempts.size,
                attempts: allAttempts,
                isChoicePoint: true,
                // For choice points, store damages array corresponding to each ability name
                choiceDamages: damages
            });
        }
    }

    return merged;
}

// Format unmitigated damage string for display in estimated timeline
function formatUnmitigatedDamage(evt) {
    // Only format for abilities (which have damage data)
    if (evt.type !== 'ability') return '';

    if (evt.isChoicePoint && evt.choiceDamages) {
        // For choice points, format as "(U:xxx/U:xxx)" for each ability
        const damageStrs = evt.choiceDamages.map(d => d > 0 ? `U:${d}` : 'U:?');
        return ` (${damageStrs.join('/')})`;
    } else if (evt.avgDamage && evt.avgDamage > 0) {
        // For single abilities, format as "(U: xxx)"
        return ` (U: ${evt.avgDamage})`;
    }

    return '';
}

// Render the best guess timeline
function renderBestGuessTimeline(events, totalAttempts) {
    // Hide other timeline views, show best guess
    elements.timelineContainer.style.display = 'none';
    elements.simplifiedTimelineContainer.style.display = 'none';
    elements.bestGuessTimelineContainer.style.display = 'block';

    elements.bestGuessAttemptCount.textContent = `(from ${totalAttempts} attempts)`;

    if (events.length === 0) {
        elements.bestGuessTimelineContent.innerHTML = '<div class="empty-state">No consistent mechanics found across attempts</div>';
        return;
    }

    // Build 2-column layout (Abilities | Debuffs)
    const eventsByTime = new Map();

    events.forEach(event => {
        const timeKey = Math.floor(event.medianTime);
        if (!eventsByTime.has(timeKey)) {
            eventsByTime.set(timeKey, { abilities: [], debuffs: [] });
        }

        const bucket = eventsByTime.get(timeKey);
        if (event.type === 'ability') {
            bucket.abilities.push(event);
        } else {
            bucket.debuffs.push(event);
        }
    });

    const sortedTimes = Array.from(eventsByTime.keys()).sort((a, b) => a - b);

    let html = `
        <div class="simplified-column abilities">
            <div class="simplified-column-header">Abilities</div>
            <div class="simplified-events-list">
    `;

    sortedTimes.forEach(time => {
        const bucket = eventsByTime.get(time);
        const timeStr = formatRelativeTime(time);

        bucket.abilities.forEach(evt => {
            const choiceClass = evt.isChoicePoint ? 'choice-point' : '';
            const damageStr = formatUnmitigatedDamage(evt);
            html += `
                <div class="simplified-event-row">
                    <span class="simplified-time">${timeStr}</span>
                    <div class="simplified-event-cell ability ${choiceClass}">
                        <span class="simplified-event-name">${evt.name}${damageStr}</span>
                    </div>
                </div>
            `;
        });
    });

    html += `
            </div>
        </div>
        <div class="simplified-column debuffs">
            <div class="simplified-column-header">Debuffs</div>
            <div class="simplified-events-list">
    `;

    sortedTimes.forEach(time => {
        const bucket = eventsByTime.get(time);
        const timeStr = formatRelativeTime(time);

        bucket.debuffs.forEach(evt => {
            const choiceClass = evt.isChoicePoint ? 'choice-point' : '';
            html += `
                <div class="simplified-event-row">
                    <span class="simplified-time">${timeStr}</span>
                    <div class="simplified-event-cell debuff ${choiceClass}">
                        <span class="simplified-event-name">${evt.name}</span>
                    </div>
                </div>
            `;
        });
    });

    html += `
            </div>
        </div>
    `;

    elements.bestGuessTimelineContent.innerHTML = html;
}

// Calculate median of an array of numbers
function calculateMedian(arr) {
    if (arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// Manual Hit Type Modal Functions
function initManualHitTypeModal() {
    // Open modal button
    elements.manualHitTypeBtn.addEventListener('click', openManualHitTypeModal);

    // Close modal buttons
    elements.hitTypeModalClose.addEventListener('click', closeManualHitTypeModal);
    elements.hitTypeCancelBtn.addEventListener('click', closeManualHitTypeModal);

    // Confirm button
    elements.hitTypeConfirmBtn.addEventListener('click', submitManualHitTypes);

    // Close on backdrop click
    elements.hitTypeModal.addEventListener('click', (e) => {
        if (e.target === elements.hitTypeModal) {
            closeManualHitTypeModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.hitTypeModal.classList.contains('show')) {
            closeManualHitTypeModal();
        }
    });
}

async function openManualHitTypeModal() {
    if (!currentFight || !currentAttempt) {
        showNotification('Please select an attempt first');
        return;
    }

    // Fetch unique abilities for this attempt
    const data = await fetchAPI(
        `/api/fights/${currentFight}/attempts/${currentAttempt}/unique-abilities`
    );

    if (!data || !data.abilities) {
        showNotification('Failed to load abilities');
        return;
    }

    // Populate the table
    populateHitTypeTable(data.abilities);

    // Show modal
    elements.hitTypeModal.classList.add('show');
}

function closeManualHitTypeModal() {
    elements.hitTypeModal.classList.remove('show');
}

function populateHitTypeTable(abilities) {
    elements.hitTypeTableBody.innerHTML = '';

    if (abilities.length === 0) {
        elements.hitTypeTableBody.innerHTML = `
            <tr>
                <td colspan="2" class="empty-state">No abilities found</td>
            </tr>
        `;
        return;
    }

    const hitTypeOptions = ['Unknown', 'Physical', 'Magical', 'Special'];

    abilities.forEach(ability => {
        const row = document.createElement('tr');
        if (ability.is_manual_override) {
            row.classList.add('manual-override');
        }

        // Create options for select
        const optionsHtml = hitTypeOptions.map(type => {
            const selected = ability.hit_type === type ? 'selected' : '';
            return `<option value="${type}" ${selected}>${type}</option>`;
        }).join('');

        row.innerHTML = `
            <td>
                ${ability.ability_name}
                <span class="ability-id">(${ability.ability_id})</span>
            </td>
            <td>
                <select data-ability-id="${ability.ability_id}" data-original-value="${ability.hit_type}">
                    ${optionsHtml}
                </select>
            </td>
        `;

        elements.hitTypeTableBody.appendChild(row);
    });
}

async function submitManualHitTypes() {
    // Collect only hit type selections that changed from their original value
    const overrides = {};
    const selects = elements.hitTypeTableBody.querySelectorAll('select');

    selects.forEach(select => {
        const abilityId = select.dataset.abilityId;
        const hitType = select.value;
        const originalValue = select.dataset.originalValue;
        // Only include if the value was actually changed by the user
        if (hitType !== originalValue && hitType !== 'Unknown') {
            overrides[abilityId] = hitType;
        }
    });

    if (Object.keys(overrides).length === 0) {
        showNotification('No hit types to save');
        closeManualHitTypeModal();
        return;
    }

    try {
        const response = await fetch('/api/manual-hit-types', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ overrides }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showNotification(
                `Updated ${data.abilities_updated} abilities (${data.total_overrides} total overrides)`
            );

            // Close modal
            closeManualHitTypeModal();

            // Reload the current attempt to show updated values
            if (currentFight && currentAttempt) {
                await loadAttemptDetails(currentFight, currentAttempt);
            }
        } else {
            showNotification(data.error || 'Failed to save hit types');
        }
    } catch (error) {
        console.error('Failed to submit manual hit types:', error);
        showNotification('Failed to save hit types - check console');
    }
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
