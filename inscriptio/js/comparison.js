/* ============================================================
   inscriptio — comparison.js
   Event handlers and logic for 05_progress_comparison.html
   ============================================================ */

'use strict';

// ── Initialize page on load ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Session.require();
  populateSidebarUser();
  initSidebarNav();
  initComparisonPage();
});

// ── Initialize comparison page ──────────────────────────────
function initComparisonPage() {
  const studentSelect = document.getElementById('student-select');
  const date1Select = document.getElementById('date-select-1');
  const date2Select = document.getElementById('date-select-2');
  const loadBtn = document.getElementById('load-comparison-btn');

  // Student selection
  if (studentSelect) {
    studentSelect.addEventListener('change', () => {
      const studentId = studentSelect.value;
      
      if (studentId) {
        // Enable date selects
        date1Select.disabled = false;
        date2Select.disabled = false;
        
        // Fetch and populate available dates for this student
        populateDateSelects(studentId);
      } else {
        // Clear and disable date selects
        date1Select.value = '';
        date2Select.value = '';
        date1Select.disabled = true;
        date2Select.disabled = true;
        loadBtn.disabled = true;
      }
    });
  }

  // Date selection validation
  if (date1Select && date2Select) {
    const checkDatesValid = () => {
      const date1 = date1Select.value;
      const date2 = date2Select.value;
      loadBtn.disabled = !(date1 && date2);
    };

    date1Select.addEventListener('change', checkDatesValid);
    date2Select.addEventListener('change', checkDatesValid);
  }

  // Load comparison button
  if (loadBtn) {
    loadBtn.addEventListener('click', () => {
      const studentId = studentSelect.value;
      const reportId1 = date1Select.value;
      const reportId2 = date2Select.value;

      if (studentId && reportId1 && reportId2) {
        loadComparison(studentId, reportId1, reportId2);
      }
    });
  }
}

// ── Populate available dates for selected student ──────────────
function populateDateSelects(studentId) {
  const date1Select = document.getElementById('date-select-1');
  const date2Select = document.getElementById('date-select-2');

  // ┌─────────────────────────────────────────────────────────┐
  // │ DEV NOTE FOR BACKEND DEVELOPER:                         │
  // │                                                         │
  // │ 1. Endpoint needed:                                     │
  // │    GET /api/reports?studentId={studentId}              │
  // │                                                         │
  // │ 2. Expected response format:                            │
  // │    {                                                    │
  // │      "reports": [                                       │
  // │        {                                                │
  // │          "id": "RPT-2025-04-01-001",                   │
  // │          "date": "2025-04-01",                          │
  // │          "timestamp": "2025-04-01T14:30:00Z",          │
  // │          "confidenceScore": 87.4,                       │
  // │          "status": "completed"                          │
  // │        },                                               │
  // │        ...                                              │
  // │      ]                                                  │
  // │    }                                                    │
  // │                                                         │
  // │ 3. Error handling: If fetch fails, show toast:         │
  // │    showToast('Failed to load reports', 'error')        │
  // │                                                         │
  // │ 4. PLACEHOLDER BELOW - REMOVE AND IMPLEMENT WITH API   │
  // └─────────────────────────────────────────────────────────┘

  // PLACEHOLDER: Mock data - replace with actual API call
  const mockReports = [
    { id: 'RPT-2025-04-01-001', date: '2025-04-01', label: 'Apr 1, 2025' },
    { id: 'RPT-2025-04-15-001', date: '2025-04-15', label: 'Apr 15, 2025' },
    { id: 'RPT-2025-05-01-001', date: '2025-05-01', label: 'May 1, 2025' },
    { id: 'RPT-2025-05-15-001', date: '2025-05-15', label: 'May 15, 2025' },
  ];

  // IMPLEMENTATION: Replace this with actual fetch call
  // fetch(`/api/reports?studentId=${studentId}`)
  //   .then(res => res.json())
  //   .then(data => {
  //     const options = data.reports.map(r => ({
  //       id: r.id,
  //       date: r.date,
  //       label: new Date(r.date).toLocaleDateString('en-US', 
  //         { year: 'numeric', month: 'short', day: 'numeric' })
  //     }));
  //     populateSelectOptions(date1Select, options);
  //     populateSelectOptions(date2Select, options);
  //   })
  //   .catch(err => {
  //     showToast('Failed to load reports', 'error');
  //     console.error('Error fetching reports:', err);
  //   });

  // PLACEHOLDER: Populate with mock data
  populateSelectOptions(date1Select, mockReports);
  populateSelectOptions(date2Select, mockReports);
}

// ── Helper: Populate select options ─────────────────────────
function populateSelectOptions(selectEl, options) {
  const currentValue = selectEl.value;
  selectEl.innerHTML = '<option value="">— Select a date —</option>';
  options.forEach(opt => {
    const optionEl = document.createElement('option');
    optionEl.value = opt.id;
    optionEl.textContent = `${opt.label} (${opt.date})`;
    selectEl.appendChild(optionEl);
  });
  if (currentValue) selectEl.value = currentValue;
}

// ── Load and display comparison ─────────────────────────────
function loadComparison(studentId, reportId1, reportId2) {
  // ┌─────────────────────────────────────────────────────────┐
  // │ DEV NOTE FOR BACKEND DEVELOPER:                         │
  // │                                                         │
  // │ 1. Endpoint needed (fetch both reports in parallel):   │
  // │    GET /api/reports/{reportId}                         │
  // │                                                         │
  // │ 2. Expected response format:                            │
  // │    {                                                    │
  // │      "id": "RPT-2025-04-01-001",                       │
  // │      "studentId": "STU-001",                            │
  // │      "date": "2025-04-01",                              │
  // │      "confidenceScore": 87.4,                           │
  // │      "features": [                                      │
  // │        "feature_1", "feature_2", "feature_3"           │
  // │      ],                                                 │
  // │      "dysgraphiaRiskLevel": "high",                    │
  // │      "shapValues": {                                   │
  // │        "stroke_direction": 0.85,                       │
  // │        "loop_closure": 0.72,                            │
  // │        "slant": 0.91,                                   │
  // │        "pressure": 0.68,                                │
  // │        "spacing": 0.77                                  │
  // │      },                                                 │
  // │      "historicalScores": [                             │
  // │        { date: "2025-04-01", score: 87.4 },           │
  // │        { date: "2025-04-15", score: 84.2 },           │
  // │        ...                                              │
  // │      ]                                                  │
  // │    }                                                    │
  // │                                                         │
  // │ 3. Error handling: Show toast and console error        │
  // │                                                         │
  // │ 4. PLACEHOLDER DATA BELOW - REMOVE AND FETCH FROM API  │
  // └─────────────────────────────────────────────────────────┘

  showToast('Loading comparison data...', 'info');

  // PLACEHOLDER: Mock data - replace with actual API calls
  const mockReport1 = {
    id: reportId1,
    date: '2025-04-01',
    confidenceScore: 87.4,
    features: ['Feature 1', 'Feature 2', 'Feature 3'],
    dysgraphiaRiskLevel: 'high',
    shapValues: {
      stroke_direction: 0.85,
      loop_closure: 0.72,
      slant: 0.91,
      pressure: 0.68,
      spacing: 0.77
    }
  };

  const mockReport2 = {
    id: reportId2,
    date: '2025-05-15',
    confidenceScore: 72.1,
    features: ['Feature 1 (Improved)', 'Feature 2'],
    dysgraphiaRiskLevel: 'medium',
    shapValues: {
      stroke_direction: 0.45,
      loop_closure: 0.72,
      slant: 0.85,
      pressure: 0.65,
      spacing: 0.81
    }
  };

  // IMPLEMENTATION: Replace with actual API calls
  // Promise.all([
  //   fetch(`/api/reports/${reportId1}`).then(r => r.json()),
  //   fetch(`/api/reports/${reportId2}`).then(r => r.json())
  // ])
  //   .then(([report1, report2]) => {
  //     displayComparison(report1, report2);
  //     renderTrendChart(report1.historicalScores);
  //     renderHeatmapComparison(report1.shapValues, report2.shapValues);
  //     showToast('Comparison loaded successfully', 'success');
  //   })
  //   .catch(err => {
  //     showToast('Failed to load comparison data', 'error');
  //     console.error('Error loading reports:', err);
  //   });

  // PLACEHOLDER: Use mock data
  setTimeout(() => {
    displayComparison(mockReport1, mockReport2);
    renderTrendChart();
    renderHeatmapComparison();
    showToast('Comparison loaded successfully', 'success');
  }, 500);
}

// ── Display dual-panel comparison ───────────────────────────
function displayComparison(report1, report2) {
  const container = document.getElementById('comparison-container');
  const emptyState = document.getElementById('empty-state');
  
  // Hide empty state and show comparison
  if (emptyState) emptyState.style.display = 'none';
  if (container) container.style.display = 'block';

  // Update panel 1 (Baseline)
  const panel1Date = document.getElementById('panel-1-date');
  const panel1Content = document.getElementById('panel-1-content');
  if (panel1Date) {
    panel1Date.textContent = new Date(report1.date).toLocaleDateString('en-US', 
      { year: 'numeric', month: 'short', day: 'numeric' });
  }
  if (panel1Content) {
    panel1Content.innerHTML = renderReportPanel(report1);
  }

  // Update panel 2 (Current)
  const panel2Date = document.getElementById('panel-2-date');
  const panel2Content = document.getElementById('panel-2-content');
  if (panel2Date) {
    panel2Date.textContent = new Date(report2.date).toLocaleDateString('en-US', 
      { year: 'numeric', month: 'short', day: 'numeric' });
  }
  if (panel2Content) {
    panel2Content.innerHTML = renderReportPanel(report2);
  }

  // Update improvement summary
  updateImprovementSummary(report1, report2);
}

// ── Helper: Render report panel content ──────────────────────
function renderReportPanel(report) {
  const riskClass = report.dysgraphiaRiskLevel.toLowerCase();
  const featuresHtml = report.features.map(f => `<li>${f}</li>`).join('');

  return `
    <div class="panel-placeholder">
      <p>Confidence Score: <span class="placeholder-value">${report.confidenceScore}%</span></p>
      <p>Key Features Detected:</p>
      <ul style="margin-left: 20px; margin-top: 8px;">
        ${featuresHtml}
      </ul>
      <p style="margin-top: 12px;">Dysgraphia Risk Level: <span class="risk-badge ${riskClass}">${report.dysgraphiaRiskLevel.charAt(0).toUpperCase() + report.dysgraphiaRiskLevel.slice(1)}</span></p>
    </div>
  `;
}

// ── Helper: Update improvement summary ───────────────────────
function updateImprovementSummary(report1, report2) {
  const scoreDiff = report2.confidenceScore - report1.confidenceScore;
  const improvementDirection = scoreDiff < 0 ? 'positive' : 'negative';
  const daysApart = Math.floor((new Date(report2.date) - new Date(report1.date)) / (1000 * 60 * 60 * 24));
  
  // Count features removed
  const featuresRemoved = report1.features.length - report2.features.length;
  
  // ┌─────────────────────────────────────────────────────────┐
  // │ NOTE: Summary values are calculated from report data    │
  // │ These can be customized based on your scoring algorithm │
  // └─────────────────────────────────────────────────────────┘
  
  // The summary is already rendered in HTML with placeholder values
  // In real implementation, you would dynamically update these values
  // Update via: document.querySelector('.summary-item').textContent
}

// ── Render trend chart ──────────────────────────────────────
function renderTrendChart(historicalScores) {
  const trendSection = document.getElementById('trend-section');
  if (trendSection) {
    trendSection.style.display = 'block';
  }

  // ┌─────────────────────────────────────────────────────────┐
  // │ DEV NOTE FOR FRONTEND/ALGORITHM DEVELOPER:              │
  // │                                                         │
  // │ IMPLEMENTATION STEPS:                                   │
  // │ 1. Add Chart.js library to HTML (via CDN or npm):      │
  // │    <script src="https://cdn.jsdelivr.net/npm/chart.js"  │
  // │                                                         │
  // │ 2. Expected data format:                                │
  // │    [                                                    │
  // │      { date: "2025-04-01", score: 87.4 },             │
  // │      { date: "2025-04-15", score: 84.2 },             │
  // │      { date: "2025-05-01", score: 76.5 },             │
  // │      { date: "2025-05-15", score: 72.1 }              │
  // │    ]                                                    │
  // │                                                         │
  // │ 3. Chart configuration:                                │
  // │    - Type: 'line'                                       │
  // │    - X-axis: Dates                                      │
  // │    - Y-axis: Confidence Score (0-100)                  │
  // │    - Trend: Descending = improvement                   │
  // │    - Threshold line at 80% (flagged level)             │
  // │                                                         │
  // │ 4. Color scheme: Use var(--teal) for line              │
  // │                  Use var(--danger) for threshold        │
  // │                                                         │
  // │ 5. Replace placeholder SVG with real canvas element    │
  // │                                                         │
  // │ PLACEHOLDER CODE - REMOVE WHEN IMPLEMENTING:           │
  // └─────────────────────────────────────────────────────────┘

  // PLACEHOLDER: Chart is currently SVG placeholder in HTML
  // Replace placeholder with Chart.js implementation:
  
  // const chartCanvas = document.createElement('canvas');
  // const chartContainer = document.querySelector('.chart-placeholder');
  // chartContainer.innerHTML = '';
  // chartContainer.appendChild(chartCanvas);
  
  // const ctx = chartCanvas.getContext('2d');
  // new Chart(ctx, {
  //   type: 'line',
  //   data: {
  //     labels: historicalScores.map(h => h.date),
  //     datasets: [{
  //       label: 'Confidence Score',
  //       data: historicalScores.map(h => h.score),
  //       borderColor: 'var(--teal)',
  //       backgroundColor: 'rgba(14, 159, 160, 0.1)',
  //       tension: 0.4,
  //       fill: true
  //     }]
  //   },
  //   options: {
  //     responsive: true,
  //     plugins: {
  //       legend: {
  //         display: true,
  //         labels: { font: { family: "'Figtree', sans-serif" } }
  //       }
  //     },
  //     scales: {
  //       y: {
  //         beginAtZero: true,
  //         max: 100,
  //         title: { display: true, text: 'Confidence Score' }
  //       }
  //     }
  //   }
  // });
}

// ── Render heatmap comparison ───────────────────────────────
function renderHeatmapComparison(shapValues1, shapValues2) {
  const heatmapSection = document.getElementById('heatmap-section');
  if (heatmapSection) {
    heatmapSection.style.display = 'block';
  }

  // ┌─────────────────────────────────────────────────────────┐
  // │ DEV NOTE FOR ALGORITHM/VISUALIZATION DEVELOPER:         │
  // │                                                         │
  // │ IMPLEMENTATION STEPS:                                   │
  // │ 1. Add Plotly.js or similar heatmap library (optional) │
  // │    or implement with HTML table (current placeholder)   │
  // │                                                         │
  // │ 2. Expected data structure:                             │
  // │    {                                                    │
  // │      "stroke_direction": 0.85,    // Baseline          │
  // │      "loop_closure": 0.72,                              │
  // │      "slant": 0.91,                                     │
  // │      "pressure": 0.68,                                  │
  // │      "spacing": 0.77                                    │
  // │    }                                                    │
  // │                                                         │
  // │ 3. Color mapping:                                       │
  // │    - 0.0-0.3: Green/Teal (low risk)                    │
  // │    - 0.3-0.6: Amber (medium risk)                       │
  // │    - 0.6-1.0: Red (high risk/dysgraphia indicator)     │
  // │                                                         │
  // │ 4. Interpretation:                                      │
  // │    - Shrinking red zones = improvement                  │
  // │    - Each value represents SHAP importance              │
  // │    - Higher = stronger indicator of dysgraphia         │
  // │                                                         │
  // │ 5. Update table rows with calculated values/changes    │
  // │                                                         │
  // │ PLACEHOLDER DATA - REMOVE WHEN IMPLEMENTING:           │
  // └─────────────────────────────────────────────────────────┘

  // PLACEHOLDER: Table is already rendered in HTML with placeholder values
  // In real implementation:
  // 1. Calculate value changes (baseline - current)
  // 2. Determine color codes based on SHAP value ranges
  // 3. Update table rows dynamically with actual SHAP values
  // 4. Add visualization of color intensity (heatmap)

  // Example implementation structure:
  // const features = ['stroke_direction', 'loop_closure', 'slant', 'pressure', 'spacing'];
  // const tableBody = document.querySelector('.heatmap-table tbody');
  // 
  // features.forEach(feature => {
  //   const val1 = shapValues1[feature] || 0;
  //   const val2 = shapValues2[feature] || 0;
  //   const change = val2 - val1;
  //   
  //   const row = document.createElement('tr');
  //   row.innerHTML = `
  //     <td>${formatFeatureName(feature)}</td>
  //     <td><div class="heatmap-cell" style="background: ${getColorForValue(val1)}">${val1.toFixed(2)}</div></td>
  //     <td><div class="heatmap-cell" style="background: ${getColorForValue(val2)}">${val2.toFixed(2)}</div></td>
  //     <td><span class="change-badge ${change < 0 ? 'positive' : 'negative'}">
  //       ${change >= 0 ? '+' : ''}${change.toFixed(2)} ${change < 0 ? '↓' : '↑'}
  //     </span></td>
  //   `;
  //   tableBody.appendChild(row);
  // });
}

// ── Helper: Format feature names ────────────────────────────
function formatFeatureName(featureName) {
  const names = {
    'stroke_direction': 'Stroke Direction Inconsistency',
    'loop_closure': 'Loop Closure Difficulty',
    'slant': 'Slant Variability',
    'pressure': 'Pressure Inconsistency',
    'spacing': 'Letter Spacing Anomaly'
  };
  return names[featureName] || featureName;
}

// ── Helper: Get color for SHAP value ────────────────────────
function getColorForValue(value) {
  // Color scale: Green (low) → Amber (medium) → Red (high)
  if (value < 0.3) return 'rgba(14, 159, 160, 0.4)';  // Teal
  if (value < 0.6) return 'rgba(232, 160, 32, 0.5)';  // Amber
  return 'rgba(192, 57, 43, 0.8)';                     // Red
}
