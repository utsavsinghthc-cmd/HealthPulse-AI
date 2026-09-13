const API_BASE = window.location.origin;

let map = null;
let mapMarkers = [];

let categoryGrowthChart = null;
let riskDistributionChart = null;

let locationCategoryChart = null;
let locationTrendChart = null;
let locationForecastChart = null;


/* =========================================================
   HELPERS
========================================================= */

function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-IN");
}


function formatPercent(value) {
    const number = Number(value || 0);

    return `${number >= 0 ? "+" : ""}${number.toFixed(1)}%`;
}


function riskClass(level) {
    return String(level || "LOW").toLowerCase();
}


function directionClass(direction) {
    const value = String(direction || "STABLE").toLowerCase();

    if (value === "rising") return "rising";
    if (value === "declining") return "declining";

    return "stable";
}


function hexToRgba(hex, alpha = 0.12) {
    const clean = hex.replace("#", "");

    const bigint = parseInt(clean, 16);

    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}


function movingAverage(values, windowSize = 7) {

    return values.map((_, index) => {

        const start = Math.max(0, index - windowSize + 1);

        const slice = values.slice(start, index + 1);

        const total = slice.reduce(
            (sum, value) => sum + Number(value || 0),
            0
        );

        return Number((total / slice.length).toFixed(2));
    });
}


async function fetchJSON(url) {

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(
            `Request failed: ${response.status}`
        );
    }

    return await response.json();
}


/* =========================================================
   SYSTEM STATUS
========================================================= */

function setSystemStatus(online = true) {

    const text = document.getElementById("system-status");
    const dot = document.getElementById("status-dot");

    if (!text || !dot) return;

    if (online) {
        text.textContent = "System Operational";
        dot.classList.remove("offline");
    } else {
        text.textContent = "System Offline";
        dot.classList.add("offline");
    }
}


/* =========================================================
   OVERVIEW
========================================================= */

async function loadOverview() {

    const data = await fetchJSON(
        `${API_BASE}/api/overview`
    );

    document.getElementById("total-reports").textContent =
        formatNumber(data.total_reports);

    document.getElementById("locations-count").textContent =
        formatNumber(data.locations);

    document.getElementById("high-risk-count").textContent =
        formatNumber(
            Number(data.risk?.critical || 0) +
            Number(data.risk?.high || 0)
        );

    document.getElementById("anomalies-count").textContent =
        formatNumber(data.active_anomalies);

    document.getElementById("forecasts-count").textContent =
        formatNumber(data.rising_forecasts);

    renderPriorityAlert(data);

    setSystemStatus(true);
}


/* =========================================================
   PRIORITY ALERT
========================================================= */

function renderPriorityAlert(data) {

    const alert = document.getElementById(
        "priority-alert"
    );

    const title = document.getElementById(
        "priority-alert-title"
    );

    const description = document.getElementById(
        "priority-alert-description"
    );

    const score = document.getElementById(
        "priority-alert-score"
    );

    if (!alert) return;

    const signal = data.top_signal;

    alert.className = "priority-alert low";

    if (!signal) {

        title.textContent =
            "No high-priority signals detected";

        description.textContent =
            "Current community indicators are within normal monitoring ranges.";

        score.textContent = "LOW";

        return;
    }

    const priority = String(
        signal.priority || "LOW"
    ).toUpperCase();

    alert.classList.remove("low");

    alert.classList.add(
        priority.toLowerCase()
    );

    title.textContent =
        `${priority} PRIORITY — ${signal.location}`;

    description.textContent =
        signal.explanation ||
        "Community-level health signal detected.";

    score.textContent =
        Number(signal.risk_score || 0).toFixed(1);
}


/* =========================================================
   TOP SIGNAL
========================================================= */

async function loadIntelligence() {

    const data = await fetchJSON(
        `${API_BASE}/api/intelligence`
    );

    renderTopSignal(data.top_signal);
}


function renderTopSignal(signal) {

    const container =
        document.getElementById("top-signal");

    if (!container) return;

    if (!signal) {

        container.innerHTML = `
            <div class="empty-state">
                No priority signal available.
            </div>
        `;

        return;
    }

    container.innerHTML = `

        <div class="top-signal-content">

            <div class="top-signal-main">

                <span class="signal-priority ${riskClass(signal.priority)}">
                    ${escapeHTML(signal.priority)}
                </span>

                <h4>
                    ${escapeHTML(signal.location)}
                </h4>

                <span class="signal-category">
                    ${escapeHTML(signal.health_category)}
                </span>

            </div>


            <div class="top-signal-stats">

                <div>
                    <span>Risk Score</span>
                    <strong>
                        ${Number(signal.risk_score || 0).toFixed(1)}
                    </strong>
                </div>

                <div>
                    <span>Risk Level</span>
                    <strong>
                        ${escapeHTML(signal.risk_level)}
                    </strong>
                </div>

                <div>
                    <span>Case Growth</span>
                    <strong>
                        ${formatPercent(signal.growth_percent)}
                    </strong>
                </div>

                <div>
                    <span>Forecast</span>
                    <strong>
                        ${escapeHTML(signal.forecast_direction)}
                    </strong>
                </div>

            </div>


            <div class="top-signal-explanation">

                <strong>
                    AI Explanation
                </strong>

                <p>
                    ${escapeHTML(signal.explanation)}
                </p>

            </div>


            <div class="top-signal-action">

                <strong>
                    Recommended Action
                </strong>

                <p>
                    ${escapeHTML(signal.recommended_action)}
                </p>

            </div>

        </div>
    `;
}


/* =========================================================
   TRENDS
========================================================= */

async function loadTrends() {

    const data = await fetchJSON(
        `${API_BASE}/api/trends`
    );

    renderCategoryGrowth(
        data.category_growth || []
    );

    renderSignalsTable(
        data.emerging_signals || []
    );
}


function renderCategoryGrowth(rows) {

    const canvas = document.getElementById(
        "category-growth-chart"
    );

    if (!canvas) return;

    if (categoryGrowthChart) {
        categoryGrowthChart.destroy();
    }

    const labels = rows.map(
        row => row.health_category
    );

    const values = rows.map(
        row => Number(row.growth_percent || 0)
    );

    categoryGrowthChart = new Chart(
        canvas,
        {
            type: "bar",

            data: {
                labels,

                datasets: [
                    {
                        label: "14-Day Growth %",
                        data: values,
                        borderRadius: 6
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        }
    );
}


/* =========================================================
   SIGNAL TABLE
========================================================= */

function renderSignalsTable(rows) {

    const tbody = document.getElementById(
        "signals-table"
    );

    if (!tbody) return;

    if (!rows.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="5">
                    No emerging signals detected.
                </td>
            </tr>
        `;

        return;
    }

    tbody.innerHTML = rows.map(row => {

        const status =
            row.status ||
            row.signal_level ||
            "NORMAL";

        return `
            <tr>

                <td>
                    <strong>
                        ${escapeHTML(row.location)}
                    </strong>
                </td>

                <td>
                    ${escapeHTML(row.health_category)}
                </td>

                <td>
                    ${formatNumber(row.recent_cases)}
                </td>

                <td class="${directionClass(
                    Number(row.growth_percent) >= 0
                        ? "rising"
                        : "declining"
                )}">
                    ${formatPercent(row.growth_percent)}
                </td>

                <td>
                    <span class="table-status ${riskClass(status)}">
                        ${escapeHTML(status)}
                    </span>
                </td>

            </tr>
        `;

    }).join("");
}


/* =========================================================
   RISK
========================================================= */

async function loadRisks() {

    const data = await fetchJSON(
        `${API_BASE}/api/risks`
    );

    renderRiskDistribution(
        data.risk_distribution || {}
    );
}


function renderRiskDistribution(distribution) {

    const canvas = document.getElementById(
        "risk-distribution-chart"
    );

    if (!canvas) return;

    if (riskDistributionChart) {
        riskDistributionChart.destroy();
    }

    riskDistributionChart = new Chart(
        canvas,
        {
            type: "doughnut",

            data: {
                labels: [
                    "Critical",
                    "High",
                    "Moderate",
                    "Low"
                ],

                datasets: [
                    {
                        data: [
                            distribution.critical || 0,
                            distribution.high || 0,
                            distribution.moderate || 0,
                            distribution.low || 0
                        ],

                        borderWidth: 2
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                cutout: "68%",

                plugins: {
                    legend: {
                        position: "bottom"
                    }
                }
            }
        }
    );
}


/* =========================================================
   FORECAST TABLE
========================================================= */

async function loadForecasts() {

    const data = await fetchJSON(
        `${API_BASE}/api/forecasts`
    );

    renderForecastTable(
        data.forecasts || []
    );
}


function renderForecastTable(rows) {

    const tbody = document.getElementById(
        "forecast-table"
    );

    if (!tbody) return;

    if (!rows.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    No forecast data available.
                </td>
            </tr>
        `;

        return;
    }

    tbody.innerHTML = rows.map(row => {

        const direction =
            String(row.direction || "STABLE");

        return `
            <tr>

                <td>
                    <strong>
                        ${escapeHTML(row.location)}
                    </strong>
                </td>

                <td>
                    ${escapeHTML(row.health_category)}
                </td>

                <td>
                    ${Number(
                        row.forecast_average || 0
                    ).toFixed(1)}
                </td>

                <td>
                    ${Number(
                        row.forecast_peak || 0
                    ).toFixed(1)}
                </td>

                <td>
                    <span class="table-status ${directionClass(direction)}">
                        ${escapeHTML(direction)}
                    </span>
                </td>

                <td class="${directionClass(direction)}">
                    ${formatPercent(
                        row.expected_change_percent
                    )}
                </td>

            </tr>
        `;

    }).join("");
}


/* =========================================================
   MAP
========================================================= */

const LOCATION_COORDINATES = {

    "Alambagh": [
        26.8106,
        80.9018
    ],

    "Gomti Nagar": [
        26.8550,
        81.0000
    ],

    "Indira Nagar": [
        26.8840,
        80.9970
    ],

    "Hazratganj": [
        26.8500,
        80.9490
    ],

    "Aliganj": [
        26.8860,
        80.9460
    ],

    "Mahanagar": [
        26.8760,
        80.9560
    ],

    "Chinhat": [
        26.8900,
        81.0550
    ],

    "Rajajipuram": [
        26.8460,
        80.8750
    ]
};


function getRiskColor(level) {

    const colors = {

        CRITICAL: "#7c3aed",
        HIGH: "#dc2626",
        MODERATE: "#d97706",
        LOW: "#16a34a"

    };

    return colors[
        String(level || "LOW").toUpperCase()
    ] || colors.LOW;
}


async function loadMap() {

    const data = await fetchJSON(
        `${API_BASE}/api/risks`
    );

    initializeMap(
        data.risk_scores || []
    );
}


function initializeMap(signals) {

    const mapElement =
        document.getElementById("health-map");

    if (!mapElement) return;

    if (map) {
        map.remove();
        map = null;
    }

    mapMarkers = [];

    map = L.map(
        mapElement,
        {
            zoomControl: true,
            scrollWheelZoom: true
        }
    ).setView(
        [26.8467, 80.9462],
        10
    );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 18,
            attribution:
                '&copy; OpenStreetMap contributors'
        }
    ).addTo(map);


    signals.forEach(signal => {

        const location =
            signal.location;

        const coordinates =
            LOCATION_COORDINATES[location];

        if (!coordinates) return;

        const riskLevel =
            String(
                signal.risk_level || "LOW"
            ).toUpperCase();

        const color =
            getRiskColor(riskLevel);

        const riskScore =
            Number(
                signal.risk_score || 0
            );


        const circle =
            L.circleMarker(
                coordinates,
                {
                    radius:
                        riskLevel === "CRITICAL"
                            ? 15
                            : riskLevel === "HIGH"
                                ? 13
                                : riskLevel === "MODERATE"
                                    ? 11
                                    : 9,

                    color: color,

                    fillColor: color,

                    fillOpacity: 0.78,

                    weight: 2
                }
            ).addTo(map);


        circle.bindPopup(`

            <div class="map-popup">

                <h4>
                    ${escapeHTML(location)}
                </h4>

                <div class="popup-category">
                    ${escapeHTML(
                        signal.health_category
                    )}
                </div>

                <div class="popup-grid">

                    <span>Risk</span>
                    <strong>
                        ${escapeHTML(riskLevel)}
                    </strong>

                    <span>Risk Score</span>
                    <strong>
                        ${riskScore.toFixed(1)}
                    </strong>

                    <span>14-Day Growth</span>
                    <strong>
                        ${formatPercent(
                            signal.growth_percent
                        )}
                    </strong>

                </div>

                <button
                    type="button"
                    class="map-intelligence-button"
                    data-location="${escapeHTML(location)}"
                >
                    View Intelligence →
                </button>

            </div>

        `);


        circle.on(
            "click",
            () => {
                openLocationIntelligence(
                    location
                );
            }
        );


        mapMarkers.push(circle);

    });


    addMapLegend();

    setTimeout(
        () => map.invalidateSize(),
        250
    );
}


/* =========================================================
   MAP POPUP BUTTON
========================================================= */

document.addEventListener(
    "click",
    event => {

        const button =
            event.target.closest(
                ".map-intelligence-button"
            );

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        const location =
            button.dataset.location;

        if (location) {
            openLocationIntelligence(
                location
            );
        }

    }
);


/* =========================================================
   MAP LEGEND
========================================================= */

function addMapLegend() {

    const legend =
        L.control({
            position: "bottomright"
        });


    legend.onAdd = function () {

        const div =
            L.DomUtil.create(
                "div",
                "map-legend"
            );

        div.innerHTML = `

            <strong>Risk Level</strong>

            <span>
                <i class="legend-dot critical"></i>
                Critical
            </span>

            <span>
                <i class="legend-dot high"></i>
                High
            </span>

            <span>
                <i class="legend-dot moderate"></i>
                Moderate
            </span>

            <span>
                <i class="legend-dot low"></i>
                Low
            </span>

        `;

        return div;
    };


    legend.addTo(map);
}


/* =========================================================
   LOCATION INTELLIGENCE
========================================================= */

async function openLocationIntelligence(
    location
) {

    const empty =
        document.getElementById(
            "location-empty"
        );

    const loading =
        document.getElementById(
            "location-loading"
        );

    const content =
        document.getElementById(
            "location-content"
        );

    const loadingName =
        document.getElementById(
            "loading-location-name"
        );


    if (!empty || !loading || !content) {
        return;
    }


    /*
     * IMPORTANT:
     * Immediately replace the empty state.
     * We do NOT create another panel.
     */

    empty.hidden = true;

    content.hidden = true;

    loading.hidden = false;

    loadingName.textContent =
        location;


    try {

        const data =
            await fetchJSON(
                `${API_BASE}/api/location-intelligence/${encodeURIComponent(location)}`
            );


        renderLocationIntelligence(
            data
        );


        loading.hidden = true;

        content.hidden = false;


        /*
         * Scroll the right intelligence panel
         * into a comfortable position on mobile.
         */

        if (
            window.innerWidth < 900
        ) {

            document
                .getElementById(
                    "location-intelligence"
                )
                ?.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

        }

    } catch (error) {

        console.error(
            "Location intelligence error:",
            error
        );

        loading.hidden = true;

        content.hidden = false;

        content.innerHTML = `

            <div class="location-error">

                <div class="error-icon">
                    !
                </div>

                <h3>
                    Unable to load intelligence
                </h3>

                <p>
                    We could not retrieve community
                    intelligence for
                    <strong>
                        ${escapeHTML(location)}
                    </strong>.
                </p>

                <button
                    type="button"
                    class="retry-button"
                    onclick="openLocationIntelligence('${String(location).replace(/'/g, "\\'")}')"
                >
                    Retry
                </button>

            </div>

        `;
    }
}


/* =========================================================
   RENDER LOCATION DATA
========================================================= */

function renderLocationIntelligence(data) {

    const summary =
        data.summary || {};

    const signal =
        data.signals?.[0] || {};

    const forecast =
        data.forecasts?.[0] || {};

    const categories =
        data.categories || [];

    const location =
        data.location || "Unknown";


    document.getElementById(
        "location-name"
    ).textContent =
        location;


    document.getElementById(
        "location-subtitle"
    ).textContent =
        `Community-level intelligence through ${data.latest_date}`;


    document.getElementById(
        "location-category"
    ).textContent =
        signal.health_category ||
        categories[0]?.health_category ||
        "Multiple Signals";


    document.getElementById(
        "location-total-cases"
    ).textContent =
        formatNumber(
            summary.total_cases
        );


    document.getElementById(
        "location-recent-cases"
    ).textContent =
        formatNumber(
            summary.recent_cases
        );


    document.getElementById(
        "location-previous-cases"
    ).textContent =
        formatNumber(
            summary.previous_cases
        );


    document.getElementById(
        "location-growth"
    ).textContent =
        formatPercent(
            summary.growth_percent
        );


    document.getElementById(
        "location-risk-score"
    ).textContent =
        Number(
            signal.risk_score || 0
        ).toFixed(1);


    const riskLevel =
        String(
            signal.risk_level || "LOW"
        ).toUpperCase();


    const riskBadge =
        document.getElementById(
            "location-risk-badge"
        );


    riskBadge.textContent =
        riskLevel;


    riskBadge.className =
        `risk-badge ${riskClass(riskLevel)}`;


    document.getElementById(
        "location-anomaly"
    ).textContent =
        signal.anomaly_level ||
        "NORMAL";


    document.getElementById(
        "location-cluster"
    ).textContent =
        signal.cluster_level ||
        "LOW";


    document.getElementById(
        "location-forecast-status"
    ).textContent =
        signal.forecast_direction ||
        forecast.direction ||
        "STABLE";


    document.getElementById(
        "location-expected-change"
    ).textContent =
        formatPercent(
            signal.forecast_change_percent ??
            forecast.expected_change_percent
        );


    document.getElementById(
        "location-forecast-direction"
    ).textContent =
        signal.forecast_direction ||
        forecast.direction ||
        "STABLE";


    document.getElementById(
        "location-explanation"
    ).textContent =
        signal.explanation ||
        "No AI explanation is currently available.";


    document.getElementById(
        "location-action"
    ).textContent =
        signal.recommended_action ||
        "Continue community-level monitoring and verify signals with local health data.";


    const trendDirection =
        getTrendDirection(
            Number(summary.growth_percent || 0)
        );


    const trendBadge =
        document.getElementById(
            "location-trend-badge"
        );


    trendBadge.textContent =
        trendDirection;


    trendBadge.className =
        `trend-badge ${directionClass(trendDirection)}`;


    const forecastBadge =
        document.getElementById(
            "forecast-badge"
        );


    forecastBadge.textContent =
        forecast.direction ||
        signal.forecast_direction ||
        "STABLE";


    forecastBadge.className =
        `trend-badge ${directionClass(
            forecast.direction ||
            signal.forecast_direction
        )}`;


    renderLocationCategoryChart(
        categories
    );


    renderLocationTrendChart(
        data.daily || [],
        trendDirection
    );


    renderLocationForecastChart(
        summary,
        forecast
    );
}


/* =========================================================
   LOCATION TREND
========================================================= */

function getTrendDirection(growth) {

    if (growth >= 15) {
        return "RISING";
    }

    if (growth <= -15) {
        return "DECLINING";
    }

    return "STABLE";
}


function renderLocationTrendChart(
    daily,
    direction
) {

    const canvas =
        document.getElementById(
            "location-trend-chart"
        );

    if (!canvas) return;

    if (locationTrendChart) {
        locationTrendChart.destroy();
    }


    const labels =
        daily.map(
            item => item.date.slice(5)
        );


    const values =
        daily.map(
            item => Number(
                item.case_count || 0
            )
        );


    const average =
        movingAverage(
            values,
            7
        );


    let lineColor =
        "#16a34a";


    if (direction === "RISING") {
        lineColor = "#dc2626";
    }

    if (direction === "DECLINING") {
        lineColor = "#2563eb";
    }


    locationTrendChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label: "Daily Cases",

                            data: values,

                            borderColor:
                                lineColor,

                            backgroundColor:
                                hexToRgba(
                                    lineColor,
                                    0.10
                                ),

                            fill: true,

                            tension: 0.35,

                            pointRadius: 2,

                            pointHoverRadius: 5
                        },

                        {
                            label: "7-Day Moving Average",

                            data: average,

                            borderColor:
                                "#111827",

                            borderDash: [
                                6,
                                4
                            ],

                            borderWidth: 2,

                            pointRadius: 0,

                            fill: false,

                            tension: 0.35
                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false
                    },

                    plugins: {

                        legend: {
                            display: true,
                            position: "top"
                        }

                    },

                    scales: {

                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: "Cases"
                            }
                        },

                        x: {
                            ticks: {
                                maxTicksLimit: 8
                            }
                        }

                    }

                }

            }
        );
}


/* =========================================================
   LOCATION CATEGORY PIE
========================================================= */

function renderLocationCategoryChart(
    categories
) {

    const canvas =
        document.getElementById(
            "location-category-chart"
        );

    if (!canvas) return;

    if (locationCategoryChart) {
        locationCategoryChart.destroy();
    }


    const labels =
        categories.map(
            item => item.health_category
        );


    const values =
        categories.map(
            item => Number(
                item.case_count || 0
            )
        );


    locationCategoryChart =
        new Chart(
            canvas,
            {

                type: "doughnut",

                data: {

                    labels,

                    datasets: [
                        {
                            data: values,
                            borderWidth: 2
                        }
                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    cutout: "62%",

                    plugins: {

                        legend: {
                            position: "right"
                        }

                    }

                }

            }
        );
}


/* =========================================================
   LOCATION FORECAST
========================================================= */

function renderLocationForecastChart(
    summary,
    forecast
) {

    const canvas =
        document.getElementById(
            "location-forecast-chart"
        );

    if (!canvas) return;

    if (locationForecastChart) {
        locationForecastChart.destroy();
    }


    /*
     * Backend provides a 7-day forecast summary,
     * not seven individual predicted points.
     *
     * So we clearly show:
     * Recent Average
     * Forecast Average
     * Forecast Peak
     */

    const recentAverage =
        Number(
            summary.recent_cases || 0
        ) / 14;


    const forecastAverage =
        Number(
            forecast.forecast_average || 0
        );


    const forecastPeak =
        Number(
            forecast.forecast_peak || 0
        );


    locationForecastChart =
        new Chart(
            canvas,
            {

                type: "bar",

                data: {

                    labels: [
                        "Recent Avg",
                        "7-Day Forecast Avg",
                        "Forecast Peak"
                    ],

                    datasets: [

                        {
                            label:
                                "Cases / Day",

                            data: [
                                recentAverage,
                                forecastAverage,
                                forecastPeak
                            ],

                            borderRadius: 7
                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {
                            display: false
                        }

                    },

                    scales: {

                        y: {
                            beginAtZero: true,

                            title: {
                                display: true,
                                text: "Cases / Day"
                            }

                        }

                    }

                }

            }
        );
}


/* =========================================================
   CLOSE LOCATION
========================================================= */

document.addEventListener(
    "click",
    event => {

        if (
            event.target.closest(
                "#close-location"
            )
        ) {

            clearLocationIntelligence();

        }

    }
);


function clearLocationIntelligence() {

    const empty =
        document.getElementById(
            "location-empty"
        );

    const loading =
        document.getElementById(
            "location-loading"
        );

    const content =
        document.getElementById(
            "location-content"
        );


    loading.hidden = true;

    content.hidden = true;

    empty.hidden = false;


    if (locationCategoryChart) {
        locationCategoryChart.destroy();
        locationCategoryChart = null;
    }


    if (locationTrendChart) {
        locationTrendChart.destroy();
        locationTrendChart = null;
    }


    if (locationForecastChart) {
        locationForecastChart.destroy();
        locationForecastChart = null;
    }
}


/* =========================================================
   UPLOAD
========================================================= */

let selectedFile = null;


function initializeUpload() {

    const input =
        document.getElementById(
            "csv-file"
        );

    const browse =
        document.getElementById(
            "browse-button"
        );

    const dropZone =
        document.getElementById(
            "upload-drop-zone"
        );

    const upload =
        document.getElementById(
            "upload-button"
        );

    const remove =
        document.getElementById(
            "remove-file"
        );


    if (!input) return;


    browse.addEventListener(
        "click",
        () => input.click()
    );


    input.addEventListener(
        "change",
        () => {

            if (
                input.files &&
                input.files.length
            ) {

                setSelectedFile(
                    input.files[0]
                );

            }

        }
    );


    remove.addEventListener(
        "click",
        clearSelectedFile
    );


    dropZone.addEventListener(
        "dragover",
        event => {

            event.preventDefault();

            dropZone.classList.add(
                "dragging"
            );

        }
    );


    dropZone.addEventListener(
        "dragleave",
        () => {

            dropZone.classList.remove(
                "dragging"
            );

        }
    );


    dropZone.addEventListener(
        "drop",
        event => {

            event.preventDefault();

            dropZone.classList.remove(
                "dragging"
            );


            const file =
                event.dataTransfer.files?.[0];


            if (
                file &&
                file.name.toLowerCase().endsWith(".csv")
            ) {

                setSelectedFile(file);

            }

        }
    );


    upload.addEventListener(
        "click",
        uploadCSV
    );
}


function setSelectedFile(file) {

    selectedFile = file;

    const selected =
        document.getElementById(
            "selected-file"
        );

    const name =
        document.getElementById(
            "file-name"
        );

    const size =
        document.getElementById(
            "file-size"
        );

    const button =
        document.getElementById(
            "upload-button"
        );


    name.textContent =
        file.name;


    size.textContent =
        `${(
            file.size / 1024
        ).toFixed(1)} KB`;


    selected.hidden = false;

    button.disabled = false;
}


function clearSelectedFile() {

    selectedFile = null;

    const input =
        document.getElementById(
            "csv-file"
        );

    const selected =
        document.getElementById(
            "selected-file"
        );

    const button =
        document.getElementById(
            "upload-button"
        );


    input.value = "";

    selected.hidden = true;

    button.disabled = true;
}


async function uploadCSV() {

    if (!selectedFile) return;


    const replaceExisting =
        document.getElementById(
            "replace-existing"
        ).checked;


    const button =
        document.getElementById(
            "upload-button"
        );


    const status =
        document.getElementById(
            "upload-status"
        );


    button.disabled = true;

    button.textContent =
        "Uploading & Analyzing...";


    status.textContent =
        "Processing medical reports...";


    try {

        const formData =
            new FormData();


        formData.append(
            "file",
            selectedFile
        );


        const response =
            await fetch(
                `${API_BASE}/api/upload?replace_existing=${replaceExisting}`,
                {
                    method: "POST",
                    body: formData
                }
            );


        if (!response.ok) {
            throw new Error(
                "Upload failed"
            );
        }


        const data =
            await response.json();


        status.textContent =
            `${formatNumber(
                data.uploaded_rows
            )} reports analyzed successfully.`;


        clearSelectedFile();


        await refreshDashboard();

    } catch (error) {

        console.error(error);

        status.textContent =
            "Upload failed. Please check the CSV file.";

    } finally {

        button.disabled =
            !selectedFile;

        button.textContent =
            "Upload & Analyze";

    }
}


/* =========================================================
   DASHBOARD REFRESH
========================================================= */

async function refreshDashboard() {

    try {

        await Promise.all([
            loadOverview(),
            loadIntelligence(),
            loadTrends(),
            loadRisks(),
            loadForecasts(),
            loadMap()
        ]);

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

        setSystemStatus(false);
    }
}


/* =========================================================
   START
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        initializeUpload();

        await refreshDashboard();

    }
);