"""Comprehensive Skadi Dashboard with all requested visualizations.

Features:
1. FOSS Heat Map - Rack-by-rack grid with hover details, toggle views
2. IMS Deviation Gauge - Real-time D(x) with MMS badges
3. Optimizer Loop Panel - Policy flags, action queue, audit trail
4. Savings Attribution - % breakdown by optimization strategy
5. Timeline Graphs - All metrics over time
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

from ingestors.mock_generators import MockDataGenerator
from ims.train import IMSTrainer
from ims.score import IMSScorer
from mms.filter import MMSFilter
from core.logging import logger


class DashboardState:
    """Dashboard state management."""
    
    def __init__(self):
        self.telemetry_history: List[Dict] = []
        self.ims_scores: List[Dict] = []
        self.mms_states: Dict[str, Dict] = {}  # rack_id -> {state, history}
        self.actions_taken: List[Dict] = []
        self.savings_data: Dict[str, float] = {
            'batching': 0,
            'routing': 0,
            'vfd': 0,
            'supply_temp': 0
        }
        self.policy_flags: Dict[str, bool] = {
            'routing': True,
            'batch_window': True,
            'admission_control': True,
            'setpoint_nudge': True,
            'rpm_nudge': True
        }
        self.max_history = 300
        self.heatmap_view = 'inlet'  # inlet, outlet, liquid_supply, liquid_return
        
        # Load IMS model
        self.ims_trainer = None
        self.ims_scorer = None
        self.mms_filters: Dict[str, MMSFilter] = {}
        
        # Active scenario
        self.scenario = None
        self.demo_running = False
        
    def add_telemetry(self, sample: Dict):
        """Add telemetry sample."""
        self.telemetry_history.append(sample)
        if len(self.telemetry_history) > self.max_history:
            self.telemetry_history.pop(0)
    
    def add_ims_score(self, rack_id: str, deviation: float, level: str):
        """Add IMS score."""
        self.ims_scores.append({
            'ts': datetime.utcnow().isoformat(),
            'rack_id': rack_id,
            'deviation': deviation,
            'level': level
        })
        if len(self.ims_scores) > self.max_history:
            self.ims_scores.pop(0)
    
    def update_mms_state(self, rack_id: str, state: str, persist_count: int = 0):
        """Update MMS state."""
        self.mms_states[rack_id] = {
            'state': state,
            'persist_count': persist_count,
            'updated': datetime.utcnow().isoformat()
        }
    
    def add_action(self, action: Dict):
        """Add optimizer action."""
        self.actions_taken.append(action)
        if len(self.actions_taken) > 50:
            self.actions_taken.pop(0)
        
        # Update savings attribution
        action_type = action.get('action_type', '')
        if 'batch' in action_type:
            self.savings_data['batching'] += np.random.uniform(2, 5)
        elif 'traffic' in action_type or 'routing' in action_type:
            self.savings_data['routing'] += np.random.uniform(1, 3)
        elif 'fan' in action_type or 'pump' in action_type:
            self.savings_data['vfd'] += np.random.uniform(3, 7)
        elif 'supply_temp' in action_type:
            self.savings_data['supply_temp'] += np.random.uniform(1, 4)


# Global state
state = DashboardState()
generator = MockDataGenerator()

# Load IMS model
try:
    import glob
    model_files = glob.glob('artifacts/ims_*.pkl')
    if model_files:
        latest_model = sorted(model_files)[-1]
        state.ims_trainer = IMSTrainer.load(latest_model)
        state.ims_scorer = IMSScorer(state.ims_trainer)
        logger.info(f"Loaded IMS model: {latest_model}")
        
        # Initialize MMS filters
        for row in ['A', 'B', 'C', 'D', 'E', 'F']:
            for pos in range(1, 13):
                rack_id = f"R-{row}-{pos:02d}"
                state.mms_filters[rack_id] = MMSFilter()
except Exception as e:
    logger.warning(f"Could not load IMS model: {e}")


app = FastAPI(title="Skadi Comprehensive Dashboard")


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve comprehensive dashboard HTML."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Skadi - AI Datacenter Energy Optimizer</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0a0e27;
                color: #e0e0e0;
                overflow-x: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            
            .header h1 {
                font-size: 42px;
                margin: 0;
                color: #ffffff;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }
            
            .header .subtitle {
                font-size: 16px;
                color: #b3d9ff;
                margin-top: 5px;
            }
            
            .controls {
                display: flex;
                justify-content: center;
                gap: 15px;
                padding: 15px;
                background: #141b2d;
                border-bottom: 2px solid #2a5298;
            }
            
            .btn {
                padding: 10px 25px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }
            
            .btn-start { background: #10b981; color: white; }
            .btn-stop { background: #ef4444; color: white; }
            .btn-heat { background: #f59e0b; color: white; }
            .btn-cool { background: #3b82f6; color: white; }
            .btn-clear { background: #6b7280; color: white; }
            
            .main-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                padding: 20px;
            }
            
            .left-panel {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            
            .right-panel {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            
            .card {
                background: #1a1f3a;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                border: 1px solid #2a3a5a;
            }
            
            .card-title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #60a5fa;
                border-bottom: 2px solid #2a5298;
                padding-bottom: 10px;
            }
            
            .heatmap-controls {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            
            .heatmap-controls button {
                flex: 1;
                padding: 8px;
                background: #374151;
                color: #d1d5db;
                border: 1px solid #4b5563;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .heatmap-controls button.active {
                background: #2563eb;
                color: white;
                border-color: #3b82f6;
            }
            
            .heatmap-controls button:hover {
                background: #4b5563;
            }
            
            .gauge-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            
            .policy-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 10px;
            }
            
            .policy-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px;
                background: #0f1729;
                border-radius: 5px;
                border-left: 3px solid #10b981;
            }
            
            .policy-item.disabled {
                border-left-color: #6b7280;
                opacity: 0.6;
            }
            
            .toggle {
                width: 40px;
                height: 20px;
                background: #374151;
                border-radius: 10px;
                position: relative;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .toggle.active {
                background: #10b981;
            }
            
            .toggle-slider {
                width: 16px;
                height: 16px;
                background: white;
                border-radius: 50%;
                position: absolute;
                top: 2px;
                left: 2px;
                transition: left 0.3s;
            }
            
            .toggle.active .toggle-slider {
                left: 22px;
            }
            
            .action-queue {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .action-item {
                padding: 10px;
                margin-bottom: 8px;
                background: #0f1729;
                border-radius: 5px;
                border-left: 3px solid #3b82f6;
            }
            
            .action-item .action-header {
                display: flex;
                justify-content: space-between;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .action-item .action-details {
                font-size: 13px;
                color: #9ca3af;
            }
            
            .savings-bar {
                height: 30px;
                background: #1f2937;
                border-radius: 5px;
                overflow: hidden;
                display: flex;
                margin-top: 10px;
            }
            
            .savings-segment {
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
                transition: all 0.3s;
            }
            
            .savings-batching { background: #10b981; }
            .savings-routing { background: #3b82f6; }
            .savings-vfd { background: #f59e0b; }
            .savings-temp { background: #8b5cf6; }
            
            .savings-legend {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
                margin-top: 15px;
            }
            
            .savings-legend-item {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13px;
            }
            
            .savings-legend-color {
                width: 20px;
                height: 20px;
                border-radius: 3px;
            }
            
            .status-bar {
                background: #141b2d;
                padding: 10px 20px;
                text-align: center;
                font-size: 14px;
                border-top: 2px solid #2a5298;
            }
            
            .mms-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
                margin-left: 8px;
            }
            
            .mms-transient {
                background: #fbbf24;
                color: #78350f;
            }
            
            .mms-persistent {
                background: #ef4444;
                color: white;
            }
            
            .mms-nominal {
                background: #10b981;
                color: white;
            }
            
            .hotspot-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-left: 5px;
            }
            
            .hotspot-none { background: #10b981; }
            .hotspot-warning { background: #fbbf24; }
            .hotspot-critical { background: #ef4444; }
            
            ::-webkit-scrollbar {
                width: 8px;
            }
            
            ::-webkit-scrollbar-track {
                background: #1f2937;
            }
            
            ::-webkit-scrollbar-thumb {
                background: #4b5563;
                border-radius: 4px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: #6b7280;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌡️ SKADI - AI Datacenter Energy Optimizer</h1>
            <div class="subtitle">Measure → Decide → Act | FOSS • IMS • MMS | Live Visualization Dashboard</div>
        </div>
        
        <div class="controls">
            <button class="btn btn-start" onclick="startDemo()">▶ Start Demo</button>
            <button class="btn btn-stop" onclick="stopDemo()">⏹ Stop</button>
            <button class="btn btn-heat" onclick="triggerScenario('heat_spike')">🔥 Heat Spike</button>
            <button class="btn btn-cool" onclick="triggerScenario('overcooled')">❄️ Overcooled</button>
            <button class="btn btn-clear" onclick="clearScenario()">Clear Scenario</button>
        </div>
        
        <div class="main-grid">
            <!-- LEFT PANEL -->
            <div class="left-panel">
                <!-- FOSS Heat Map -->
                <div class="card">
                    <div class="card-title">🗺️ FOSS Heat Map - Datacenter Rack Grid (72 Racks)</div>
                    <div class="heatmap-controls">
                        <button id="view-inlet" class="active" onclick="changeHeatmapView('inlet')">Inlet Temp</button>
                        <button id="view-outlet" onclick="changeHeatmapView('outlet')">Outlet Temp</button>
                        <button id="view-delta" onclick="changeHeatmapView('delta')">ΔT</button>
                        <button id="view-power" onclick="changeHeatmapView('power')">Power</button>
                    </div>
                    <div id="heatmap" style="height: 450px;"></div>
                </div>
                
                <!-- Timeline Graphs -->
                <div class="card">
                    <div class="card-title">📊 Real-Time Metrics Timeline</div>
                    <div id="timeline" style="height: 500px;"></div>
                </div>
            </div>
            
            <!-- RIGHT PANEL -->
            <div class="right-panel">
                <!-- IMS Deviation Gauge -->
                <div class="card">
                    <div class="card-title">🎯 IMS Deviation Gauge</div>
                    <div class="gauge-container">
                        <div id="ims-gauge"></div>
                        <div id="ims-details" style="padding: 20px;">
                            <div style="margin-bottom: 10px;">
                                <strong>Current D(x):</strong> <span id="dx-value">--</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>τ_fast:</strong> <span id="tau-fast">--</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>τ_persist:</strong> <span id="tau-persist">--</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>MMS State:</strong> 
                                <span id="mms-state-badge" class="mms-badge mms-nominal">NOMINAL</span>
                            </div>
                            <div>
                                <strong>Hot Spots:</strong> 
                                <span id="hotspot-count">0</span> racks
                                <span class="hotspot-indicator hotspot-none"></span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Optimizer Loop Panel -->
                <div class="card">
                    <div class="card-title">⚙️ Optimizer Loop - Policy Controls</div>
                    <div class="policy-grid">
                        <div class="policy-item" id="policy-routing">
                            <span>Thermal Routing</span>
                            <div class="toggle active" onclick="togglePolicy('routing')">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                        <div class="policy-item" id="policy-batch">
                            <span>Batch Window</span>
                            <div class="toggle active" onclick="togglePolicy('batch_window')">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                        <div class="policy-item" id="policy-admission">
                            <span>Admission Control</span>
                            <div class="toggle active" onclick="togglePolicy('admission_control')">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                        <div class="policy-item" id="policy-setpoint">
                            <span>Setpoint Nudge</span>
                            <div class="toggle active" onclick="togglePolicy('setpoint_nudge')">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                        <div class="policy-item" id="policy-rpm">
                            <span>RPM Nudge (VFD)</span>
                            <div class="toggle active" onclick="togglePolicy('rpm_nudge')">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Action Queue & Audit -->
                <div class="card">
                    <div class="card-title">📋 Action Queue & Audit Trail</div>
                    <div class="action-queue" id="action-queue">
                        <div style="text-align: center; padding: 20px; color: #6b7280;">
                            No actions yet - start demo to see optimizer in action
                        </div>
                    </div>
                </div>
                
                <!-- Savings Attribution -->
                <div class="card">
                    <div class="card-title">💰 Savings Attribution (% Energy Saved)</div>
                    <div class="savings-bar" id="savings-bar">
                        <div class="savings-segment savings-batching" style="width: 25%;">25%</div>
                        <div class="savings-segment savings-routing" style="width: 25%;">25%</div>
                        <div class="savings-segment savings-vfd" style="width: 25%;">25%</div>
                        <div class="savings-segment savings-temp" style="width: 25%;">25%</div>
                    </div>
                    <div class="savings-legend">
                        <div class="savings-legend-item">
                            <div class="savings-legend-color savings-batching"></div>
                            <span id="savings-batch-text">Batching</span>
                        </div>
                        <div class="savings-legend-item">
                            <div class="savings-legend-color savings-routing"></div>
                            <span id="savings-routing-text">Routing</span>
                        </div>
                        <div class="savings-legend-item">
                            <div class="savings-legend-color savings-vfd"></div>
                            <span id="savings-vfd-text">VFD Control</span>
                        </div>
                        <div class="savings-legend-item">
                            <div class="savings-legend-color savings-temp"></div>
                            <span id="savings-temp-text">Supply Temp</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="status-bar" id="status">
            Status: Ready - Click "Start Demo" to begin visualization
        </div>
        
        <script>
            let updateInterval = null;
            let currentView = 'inlet';
            
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/dashboard_data');
                    const data = await response.json();
                    
                    // Update heatmap
                    if (data.heatmap) {
                        Plotly.newPlot('heatmap', data.heatmap.data, data.heatmap.layout, {responsive: true});
                    }
                    
                    // Update timeline
                    if (data.timeline) {
                        Plotly.newPlot('timeline', data.timeline.data, data.timeline.layout, {responsive: true});
                    }
                    
                    // Update IMS gauge
                    if (data.ims_gauge) {
                        Plotly.newPlot('ims-gauge', data.ims_gauge.data, data.ims_gauge.layout, {responsive: true});
                        
                        // Update IMS details
                        document.getElementById('dx-value').textContent = data.ims_details.dx.toFixed(3);
                        document.getElementById('tau-fast').textContent = data.ims_details.tau_fast.toFixed(3);
                        document.getElementById('tau-persist').textContent = data.ims_details.tau_persist.toFixed(3);
                        
                        // Update MMS badge
                        const badge = document.getElementById('mms-state-badge');
                        badge.textContent = data.ims_details.mms_state.toUpperCase();
                        badge.className = 'mms-badge mms-' + data.ims_details.mms_state;
                        
                        // Update hotspot count
                        document.getElementById('hotspot-count').textContent = data.ims_details.hotspot_count;
                    }
                    
                    // Update action queue
                    if (data.actions && data.actions.length > 0) {
                        const queueHtml = data.actions.map(action => `
                            <div class="action-item">
                                <div class="action-header">
                                    <span>${action.action_type}</span>
                                    <span style="color: #60a5fa;">${action.time}</span>
                                </div>
                                <div class="action-details">
                                    ${action.reason}<br>
                                    Predicted ΔJ/prompt: ${action.delta_j}J
                                </div>
                            </div>
                        `).join('');
                        document.getElementById('action-queue').innerHTML = queueHtml;
                    }
                    
                    // Update savings bar
                    if (data.savings) {
                        const total = Object.values(data.savings).reduce((a, b) => a + b, 0);
                        if (total > 0) {
                            const batching = (data.savings.batching / total * 100);
                            const routing = (data.savings.routing / total * 100);
                            const vfd = (data.savings.vfd / total * 100);
                            const temp = (data.savings.supply_temp / total * 100);
                            
                            document.querySelector('.savings-batching').style.width = batching + '%';
                            document.querySelector('.savings-batching').textContent = batching.toFixed(0) + '%';
                            
                            document.querySelector('.savings-routing').style.width = routing + '%';
                            document.querySelector('.savings-routing').textContent = routing.toFixed(0) + '%';
                            
                            document.querySelector('.savings-vfd').style.width = vfd + '%';
                            document.querySelector('.savings-vfd').textContent = vfd.toFixed(0) + '%';
                            
                            document.querySelector('.savings-temp').style.width = temp + '%';
                            document.querySelector('.savings-temp').textContent = temp.toFixed(0) + '%';
                            
                            document.getElementById('savings-batch-text').textContent = 'Batching (' + data.savings.batching.toFixed(1) + 'J)';
                            document.getElementById('savings-routing-text').textContent = 'Routing (' + data.savings.routing.toFixed(1) + 'J)';
                            document.getElementById('savings-vfd-text').textContent = 'VFD (' + data.savings.vfd.toFixed(1) + 'J)';
                            document.getElementById('savings-temp-text').textContent = 'Temp (' + data.savings.supply_temp.toFixed(1) + 'J)';
                        }
                    }
                    
                } catch (e) {
                    console.error('Failed to update dashboard:', e);
                }
            }
            
            async function startDemo() {
                const response = await fetch('/api/start', {method: 'POST'});
                const data = await response.json();
                document.getElementById('status').textContent = 'Status: ' + data.status;
                
                if (!updateInterval) {
                    updateInterval = setInterval(updateDashboard, 1000);
                }
            }
            
            async function stopDemo() {
                const response = await fetch('/api/stop', {method: 'POST'});
                const data = await response.json();
                document.getElementById('status').textContent = 'Status: ' + data.status;
                
                if (updateInterval) {
                    clearInterval(updateInterval);
                    updateInterval = null;
                }
            }
            
            async function triggerScenario(scenario) {
                await fetch('/api/scenario/' + scenario, {method: 'POST'});
                document.getElementById('status').textContent = 'Status: ' + scenario + ' scenario active';
            }
            
            async function clearScenario() {
                await fetch('/api/scenario/clear', {method: 'POST'});
                document.getElementById('status').textContent = 'Status: Scenario cleared - normal operation';
            }
            
            async function changeHeatmapView(view) {
                currentView = view;
                
                // Update active button
                document.querySelectorAll('.heatmap-controls button').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.getElementById('view-' + view).classList.add('active');
                
                // Fetch new data
                await fetch('/api/heatmap_view/' + view, {method: 'POST'});
                updateDashboard();
            }
            
            async function togglePolicy(policy) {
                const response = await fetch('/api/policy/' + policy, {method: 'POST'});
                const data = await response.json();
                
                const element = document.getElementById('policy-' + policy.replace('_', '-'));
                const toggle = element.querySelector('.toggle');
                
                if (data.enabled) {
                    toggle.classList.add('active');
                    element.classList.remove('disabled');
                } else {
                    toggle.classList.remove('active');
                    element.classList.add('disabled');
                }
            }
            
            // Initial load
            updateDashboard();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def create_foss_heatmap(view: str = 'inlet') -> go.Figure:
    """Create FOSS heatmap with rack-by-rack grid."""
    if not state.telemetry_history:
        return go.Figure()
    
    # Get latest telemetry for each rack
    latest = {}
    for sample in reversed(state.telemetry_history):
        rack_id = sample['rack_id']
        if rack_id not in latest:
            latest[rack_id] = sample
    
    rows = ['A', 'B', 'C', 'D', 'E', 'F']
    positions = list(range(1, 13))
    
    # Build matrix based on view
    data_matrix = []
    hover_texts = []
    
    for row in rows:
        row_data = []
        row_hover = []
        
        for pos in positions:
            rack_id = f"R-{row}-{pos:02d}"
            if rack_id in latest:
                sample = latest[rack_id]
                
                # Select metric based on view
                if view == 'inlet':
                    value = sample.get('inlet_c', 0)
                    unit = '°C'
                elif view == 'outlet':
                    value = sample.get('outlet_c', 0)
                    unit = '°C'
                elif view == 'delta':
                    value = sample.get('outlet_c', 0) - sample.get('inlet_c', 0)
                    unit = '°C'
                elif view == 'power':
                    value = sample.get('pdu_kw', 0)
                    unit = 'kW'
                else:
                    value = 0
                    unit = ''
                
                row_data.append(value)
                
                # Detailed hover text
                delta_t = sample.get('outlet_c', 0) - sample.get('inlet_c', 0)
                
                # Get IMS score
                ims_score = 0
                for score in reversed(state.ims_scores):
                    if score['rack_id'] == rack_id:
                        ims_score = score['deviation']
                        break
                
                # Get MMS state
                mms_state = state.mms_states.get(rack_id, {}).get('state', 'nominal')
                
                hover_text = (
                    f"<b>{rack_id}</b><br>"
                    f"Inlet: {sample.get('inlet_c', 0):.1f}°C<br>"
                    f"Outlet: {sample.get('outlet_c', 0):.1f}°C<br>"
                    f"ΔT: {delta_t:.1f}°C<br>"
                    f"Power: {sample.get('pdu_kw', 0):.1f} kW<br>"
                    f"Tokens/s: {sample.get('tokens_ps', 0):.0f}<br>"
                    f"Latency: {sample.get('latency_p95_ms', 0):.0f} ms<br>"
                    f"IMS D(x): {ims_score:.2f}<br>"
                    f"MMS: {mms_state}"
                )
                row_hover.append(hover_text)
            else:
                row_data.append(0)
                row_hover.append("No data")
        
        data_matrix.append(row_data)
        hover_texts.append(row_hover)
    
    # Colorscale based on view
    if view in ['inlet', 'outlet']:
        colorscale = 'RdYlBu_r'
        zmin, zmax = 18, 32
    elif view == 'delta':
        colorscale = 'YlOrRd'
        zmin, zmax = 8, 20
    elif view == 'power':
        colorscale = 'Viridis'
        zmin, zmax = 0, 15
    else:
        colorscale = 'Viridis'
        zmin, zmax = 0, 100
    
    fig = go.Figure(data=go.Heatmap(
        z=data_matrix,
        x=[f"{p:02d}" for p in positions],
        y=[f"Row {r}" for r in rows],
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            title=view.replace('_', ' ').title(),
            len=0.9
        )
    ))
    
    fig.update_layout(
        title=f"FOSS Heatmap - {view.replace('_', ' ').title()} View",
        xaxis_title="Rack Position",
        yaxis_title="Row",
        height=400,
        plot_bgcolor='#0f1729',
        paper_bgcolor='#1a1f3a',
        font=dict(color='#e0e0e0')
    )
    
    return fig


def create_timeline_graphs() -> go.Figure:
    """Create timeline with multiple metrics."""
    if not state.telemetry_history:
        return go.Figure()
    
    df = pd.DataFrame(state.telemetry_history)
    df['ts'] = pd.to_datetime(df['ts'])
    
    agg = df.groupby('ts').agg({
        'inlet_c': 'mean',
        'outlet_c': 'mean',
        'pdu_kw': 'mean',
        'tokens_ps': 'mean',
        'latency_p95_ms': 'mean'
    }).reset_index()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Inlet Temperature', 'Power Consumption', 'Throughput', 'Latency (p95)'),
        specs=[[{'secondary_y': False}, {'secondary_y': False}],
               [{'secondary_y': False}, {'secondary_y': False}]]
    )
    
    # Inlet temp
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['inlet_c'], mode='lines', name='Inlet',
                   line=dict(color='#3b82f6', width=2), fill='tozeroy'),
        row=1, col=1
    )
    fig.add_hline(y=28, line_dash="dash", line_color="red", row=1, col=1)
    
    # Power
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['pdu_kw'], mode='lines', name='Power',
                   line=dict(color='#10b981', width=2), fill='tozeroy'),
        row=1, col=2
    )
    
    # Throughput
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['tokens_ps'], mode='lines', name='Tokens/s',
                   line=dict(color='#8b5cf6', width=2), fill='tozeroy'),
        row=2, col=1
    )
    
    # Latency
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['latency_p95_ms'], mode='lines', name='Latency',
                   line=dict(color='#f59e0b', width=2), fill='tozeroy'),
        row=2, col=2
    )
    fig.add_hline(y=250, line_dash="dash", line_color="red", row=2, col=2)
    
    fig.update_layout(
        height=450,
        showlegend=False,
        plot_bgcolor='#0f1729',
        paper_bgcolor='#1a1f3a',
        font=dict(color='#e0e0e0')
    )
    
    return fig


def create_ims_gauge() -> go.Figure:
    """Create IMS deviation gauge."""
    # Get latest average deviation
    current_dx = 0
    if state.ims_scores:
        recent = state.ims_scores[-10:]
        current_dx = np.mean([s['deviation'] for s in recent])
    
    tau_fast = state.ims_trainer.tau_fast if state.ims_trainer else 2.0
    tau_persist = state.ims_trainer.tau_persist if state.ims_trainer else 2.5
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_dx,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "D(x)"},
        gauge={
            'axis': {'range': [None, 4]},
            'bar': {'color': "#3b82f6"},
            'steps': [
                {'range': [0, tau_fast], 'color': "#10b981"},
                {'range': [tau_fast, tau_persist], 'color': "#fbbf24"},
                {'range': [tau_persist, 4], 'color': "#ef4444"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': tau_persist
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        plot_bgcolor='#0f1729',
        paper_bgcolor='#1a1f3a',
        font=dict(color='#e0e0e0')
    )
    
    return fig


@app.get("/api/dashboard_data")
async def get_dashboard_data():
    """Get all dashboard data."""
    heatmap = create_foss_heatmap(state.heatmap_view)
    timeline = create_timeline_graphs()
    ims_gauge = create_ims_gauge()
    
    # IMS details
    current_dx = 0
    mms_state = 'nominal'
    if state.ims_scores:
        recent = state.ims_scores[-10:]
        current_dx = np.mean([s['deviation'] for s in recent])
        
        # Count persistent states
        persistent_count = sum(1 for v in state.mms_states.values() if v.get('state') == 'persistent')
        if persistent_count > 5:
            mms_state = 'persistent'
        elif current_dx > (state.ims_trainer.tau_fast if state.ims_trainer else 2.0):
            mms_state = 'transient'
    
    # Count hotspots
    hotspot_count = 0
    if state.telemetry_history:
        latest = {}
        for sample in reversed(state.telemetry_history):
            if sample['rack_id'] not in latest:
                latest[sample['rack_id']] = sample
        hotspot_count = sum(1 for s in latest.values() if s.get('inlet_c', 0) > 27)
    
    # Format actions
    actions = []
    for action in state.actions_taken[-10:]:
        actions.append({
            'action_type': action.get('action_type', 'unknown'),
            'reason': action.get('reason', ''),
            'time': action.get('ts', '')[:19],
            'delta_j': np.random.uniform(-5, -15)
        })
    
    return {
        'heatmap': heatmap.to_dict(),
        'timeline': timeline.to_dict(),
        'ims_gauge': ims_gauge.to_dict(),
        'ims_details': {
            'dx': current_dx,
            'tau_fast': state.ims_trainer.tau_fast if state.ims_trainer else 2.0,
            'tau_persist': state.ims_trainer.tau_persist if state.ims_trainer else 2.5,
            'mms_state': mms_state,
            'hotspot_count': hotspot_count
        },
        'actions': actions,
        'savings': state.savings_data
    }


# Control endpoints
demo_task = None

async def demo_loop():
    """Demo data generation loop."""
    logger.info("Starting comprehensive demo loop...")
    
    while state.demo_running:
        try:
            now = datetime.utcnow()
            
            for row in ['A', 'B', 'C', 'D', 'E', 'F']:
                for pos in range(1, 13):
                    rack_id = f"R-{row}-{pos:02d}"
                    
                    profile = 'nominal'
                    if state.scenario == 'heat_spike' and row == 'C':
                        profile = 'thermal_event'
                    elif state.scenario == 'overcooled' and row == 'E':
                        profile = 'overcooled'
                    
                    sample = generator.generate_sample(rack_id, now, profile=profile)
                    state.add_telemetry(sample)
                    
                    if state.ims_scorer:
                        deviation = state.ims_scorer.score_sample(sample)
                        level = 'nominal'
                        if deviation >= state.ims_trainer.tau_persist:
                            level = 'critical'
                        elif deviation >= state.ims_trainer.tau_fast:
                            level = 'warning'
                        
                        state.add_ims_score(rack_id, deviation, level)
                        
                        mms_filter = state.mms_filters.get(rack_id)
                        if mms_filter:
                            mms_state = mms_filter.update(deviation)
                            state.update_mms_state(rack_id, mms_state, mms_filter.persist_count)
                            
                            # Generate actions
                            if mms_state == 'persistent' and deviation >= state.ims_trainer.tau_fast:
                                if np.random.random() < 0.1:  # 10% chance per tick
                                    action_types = ['fan_rpm', 'supply_temp', 'traffic_shift', 'batch_window']
                                    action_type = np.random.choice(action_types)
                                    
                                    state.add_action({
                                        'ts': now.isoformat(),
                                        'rack_id': rack_id,
                                        'action_type': action_type,
                                        'reason': f'{level} deviation D(x)={deviation:.2f}',
                                        'dx': deviation
                                    })
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in demo loop: {e}")
            await asyncio.sleep(1)


@app.post("/api/start")
async def start_demo():
    """Start demo."""
    global demo_task
    if not state.demo_running:
        state.demo_running = True
        demo_task = asyncio.create_task(demo_loop())
        return {"status": "Demo started - generating live data"}
    return {"status": "Demo already running"}


@app.post("/api/stop")
async def stop_demo():
    """Stop demo."""
    state.demo_running = False
    state.scenario = None
    return {"status": "Demo stopped"}


@app.post("/api/scenario/{scenario_name}")
async def trigger_scenario(scenario_name: str):
    """Trigger scenario."""
    if scenario_name == 'clear':
        state.scenario = None
        return {"status": "Scenario cleared"}
    state.scenario = scenario_name
    return {"status": f"Triggered {scenario_name}"}


@app.post("/api/heatmap_view/{view}")
async def change_heatmap_view(view: str):
    """Change heatmap view."""
    state.heatmap_view = view
    return {"status": f"View changed to {view}"}


@app.post("/api/policy/{policy_name}")
async def toggle_policy(policy_name: str):
    """Toggle policy."""
    state.policy_flags[policy_name] = not state.policy_flags.get(policy_name, False)
    return {"enabled": state.policy_flags[policy_name]}


if __name__ == "__main__":
    logger.info("Starting Comprehensive Skadi Dashboard...")
    logger.info("Open browser to: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
