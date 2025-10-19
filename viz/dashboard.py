d"""Dashboard application with live visualizations for Skadi demo.

This creates a comprehensive web dashboard showing:
- FOSS Heatmap: Rack-by-rack grid with per-U temps, ΔT histogram, hot-spot tracking
- IMS Deviation Gauge: Real-time D(x) scores with MMS badges
- Optimizer Loop Panel: Policy flags, action queue, audit trail
- Savings Attribution: % breakdown by strategy (batching, routing, VFD, temp)
- Timeline graphs: All key metrics over time
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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ingestors.mock_generators import MockDataGenerator
from ims.train import IMSTrainer
from ims.score import IMSScorer
from mms.filter import MMSFilter
from optimizer.policies import ActionPolicy
from core.logging import logger


class DashboardState:
    """Maintains state for dashboard visualizations."""
    
    def __init__(self):
        self.telemetry_history: List[Dict] = []
        self.ims_scores: List[Dict] = []
        self.mms_states: Dict[str, str] = {}  # rack_id -> state
        self.actions_taken: List[Dict] = []
        self.max_history = 300  # 5 minutes at 1s intervals
        
        # Load IMS model
        self.ims_trainer = None
        self.ims_scorer = None
        self.mms_filters: Dict[str, MMSFilter] = {}
        
        # Active scenario
        self.scenario = None
        self.scenario_start = None
        
    def add_telemetry(self, sample: Dict):
        """Add telemetry sample to history."""
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
    
    def update_mms_state(self, rack_id: str, state: str):
        """Update MMS state for rack."""
        self.mms_states[rack_id] = state
    
    def add_action(self, action: Dict):
        """Add optimizer action."""
        self.actions_taken.append(action)
        if len(self.actions_taken) > 50:
            self.actions_taken.pop(0)


# Global state
state = DashboardState()
generator = MockDataGenerator()

# Try to load IMS model
try:
    import glob
    model_files = glob.glob('artifacts/ims_*.pkl')
    if model_files:
        latest_model = sorted(model_files)[-1]
        state.ims_trainer = IMSTrainer.load(latest_model)
        state.ims_scorer = IMSScorer(state.ims_trainer)
        logger.info(f"Loaded IMS model: {latest_model}")
except Exception as e:
    logger.warning(f"Could not load IMS model: {e}")


app = FastAPI(title="Skadi Visualization Dashboard")


def create_heatmap_figure() -> go.Figure:
    """Create datacenter heatmap visualization."""
    if not state.telemetry_history:
        return go.Figure()
    
    # Get latest telemetry for each rack
    latest = {}
    for sample in reversed(state.telemetry_history):
        rack_id = sample['rack_id']
        if rack_id not in latest:
            latest[rack_id] = sample
    
    # Organize by row and position
    rows = ['A', 'B', 'C', 'D', 'E', 'F']
    positions = list(range(1, 13))  # 1-12
    
    # Create matrices for different metrics
    inlet_temps = []
    power_draw = []
    ims_deviations = []
    
    for row in rows:
        inlet_row = []
        power_row = []
        ims_row = []
        
        for pos in positions:
            rack_id = f"R-{row}-{pos:02d}"
            if rack_id in latest:
                sample = latest[rack_id]
                inlet_row.append(sample.get('inlet_c', 0))
                power_row.append(sample.get('pdu_kw', 0))
                
                # Get IMS deviation
                deviation = 0
                for score in reversed(state.ims_scores):
                    if score['rack_id'] == rack_id:
                        deviation = score['deviation']
                        break
                ims_row.append(deviation)
            else:
                inlet_row.append(0)
                power_row.append(0)
                ims_row.append(0)
        
        inlet_temps.append(inlet_row)
        power_draw.append(power_row)
        ims_deviations.append(ims_row)
    
    # Create subplots
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=('Inlet Temperature (°C)', 'Power Draw (kW)', 'IMS Deviation Score'),
        specs=[[{'type': 'heatmap'}, {'type': 'heatmap'}, {'type': 'heatmap'}]]
    )
    
    # Inlet temperature heatmap
    fig.add_trace(
        go.Heatmap(
            z=inlet_temps,
            x=[f"Pos-{p}" for p in positions],
            y=[f"Row {r}" for r in rows],
            colorscale='RdYlBu_r',
            zmin=18, zmax=32,
            colorbar=dict(x=0.3, len=0.9),
            hovertemplate='Row %{y}<br>%{x}<br>Inlet: %{z:.1f}°C<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Power heatmap
    fig.add_trace(
        go.Heatmap(
            z=power_draw,
            x=[f"Pos-{p}" for p in positions],
            y=[f"Row {r}" for r in rows],
            colorscale='YlOrRd',
            zmin=0, zmax=15,
            colorbar=dict(x=0.64, len=0.9),
            hovertemplate='Row %{y}<br>%{x}<br>Power: %{z:.1f} kW<extra></extra>'
        ),
        row=1, col=2
    )
    
    # IMS deviation heatmap
    fig.add_trace(
        go.Heatmap(
            z=ims_deviations,
            x=[f"Pos-{p}" for p in positions],
            y=[f"Row {r}" for r in rows],
            colorscale='Viridis',
            zmin=0, zmax=4,
            colorbar=dict(x=1.0, len=0.9),
            hovertemplate='Row %{y}<br>%{x}<br>D(x): %{z:.2f}<extra></extra>'
        ),
        row=1, col=3
    )
    
    fig.update_layout(
        height=400,
        title_text="Datacenter Rack Heatmaps (72 Racks)",
        showlegend=False
    )
    
    return fig


def create_timeseries_figure() -> go.Figure:
    """Create time series graphs for key metrics."""
    if not state.telemetry_history:
        return go.Figure()
    
    df = pd.DataFrame(state.telemetry_history)
    df['ts'] = pd.to_datetime(df['ts'])
    
    # Aggregate by timestamp
    agg = df.groupby('ts').agg({
        'inlet_c': 'mean',
        'outlet_c': 'mean',
        'pdu_kw': 'mean',
        'tokens_ps': 'mean',
        'latency_p95_ms': 'mean'
    }).reset_index()
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'Average Inlet Temperature',
            'Average Outlet Temperature',
            'Average Power Consumption',
            'Average Throughput',
            'Average Latency (p95)',
            'IMS Deviation Scores'
        ),
        specs=[
            [{'type': 'scatter'}, {'type': 'scatter'}],
            [{'type': 'scatter'}, {'type': 'scatter'}],
            [{'type': 'scatter'}, {'type': 'scatter'}]
        ],
        vertical_spacing=0.12
    )
    
    # Inlet temperature
    fig.add_trace(
        go.Scatter(
            x=agg['ts'], y=agg['inlet_c'],
            mode='lines',
            name='Inlet Temp',
            line=dict(color='blue', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,100,255,0.1)'
        ),
        row=1, col=1
    )
    fig.add_hline(y=28, line_dash="dash", line_color="red", row=1, col=1,
                  annotation_text="SLA Limit", annotation_position="right")
    
    # Outlet temperature
    fig.add_trace(
        go.Scatter(
            x=agg['ts'], y=agg['outlet_c'],
            mode='lines',
            name='Outlet Temp',
            line=dict(color='orange', width=2),
            fill='tozeroy',
            fillcolor='rgba(255,165,0,0.1)'
        ),
        row=1, col=2
    )
    
    # Power
    fig.add_trace(
        go.Scatter(
            x=agg['ts'], y=agg['pdu_kw'],
            mode='lines',
            name='Power',
            line=dict(color='green', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,255,0,0.1)'
        ),
        row=2, col=1
    )
    
    # Throughput
    fig.add_trace(
        go.Scatter(
            x=agg['ts'], y=agg['tokens_ps'],
            mode='lines',
            name='Tokens/s',
            line=dict(color='purple', width=2),
            fill='tozeroy',
            fillcolor='rgba(128,0,128,0.1)'
        ),
        row=2, col=2
    )
    
    # Latency
    fig.add_trace(
        go.Scatter(
            x=agg['ts'], y=agg['latency_p95_ms'],
            mode='lines',
            name='Latency',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255,0,0,0.1)'
        ),
        row=3, col=1
    )
    fig.add_hline(y=250, line_dash="dash", line_color="red", row=3, col=1,
                  annotation_text="SLA Limit", annotation_position="right")
    
    # IMS scores
    if state.ims_scores:
        ims_df = pd.DataFrame(state.ims_scores)
        ims_df['ts'] = pd.to_datetime(ims_df['ts'])
        ims_agg = ims_df.groupby('ts')['deviation'].mean().reset_index()
        
        fig.add_trace(
            go.Scatter(
                x=ims_agg['ts'], y=ims_agg['deviation'],
                mode='lines+markers',
                name='D(x)',
                line=dict(color='darkred', width=2),
                marker=dict(size=4)
            ),
            row=3, col=2
        )
        
        # Add threshold lines
        if state.ims_trainer:
            fig.add_hline(y=state.ims_trainer.tau_fast, line_dash="dash",
                         line_color="orange", row=3, col=2,
                         annotation_text="τ_fast", annotation_position="right")
            fig.add_hline(y=state.ims_trainer.tau_persist, line_dash="dash",
                         line_color="red", row=3, col=2,
                         annotation_text="τ_persist", annotation_position="right")
    
    # Update axes
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="°C", row=1, col=2)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_yaxes(title_text="tokens/s", row=2, col=2)
    fig.update_yaxes(title_text="ms", row=3, col=1)
    fig.update_yaxes(title_text="D(x)", row=3, col=2)
    
    fig.update_layout(
        height=900,
        title_text="Real-Time Metrics Time Series",
        showlegend=False
    )
    
    return fig


def create_actions_timeline() -> go.Figure:
    """Create timeline of optimizer actions."""
    if not state.actions_taken:
        return go.Figure()
    
    df = pd.DataFrame(state.actions_taken)
    df['ts'] = pd.to_datetime(df['ts'])
    
    # Create scatter plot with action types
    fig = go.Figure()
    
    colors = {
        'fan_rpm': 'blue',
        'pump_rpm': 'cyan',
        'supply_temp': 'orange',
        'batch_window': 'green',
        'traffic_shift': 'purple',
        'pause_jobs': 'red'
    }
    
    for action_type in df['action_type'].unique():
        subset = df[df['action_type'] == action_type]
        fig.add_trace(go.Scatter(
            x=subset['ts'],
            y=[action_type] * len(subset),
            mode='markers',
            name=action_type,
            marker=dict(
                size=12,
                color=colors.get(action_type, 'gray'),
                symbol='diamond'
            ),
            text=subset['reason'],
            hovertemplate='%{x}<br>%{y}<br>%{text}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Optimizer Actions Timeline",
        xaxis_title="Time",
        yaxis_title="Action Type",
        height=300,
        showlegend=True
    )
    
    return fig


def create_energy_efficiency_gauge() -> go.Figure:
    """Create gauge showing energy per prompt."""
    if not state.telemetry_history:
        return go.Figure()
    
    # Calculate J/prompt from recent data
    recent = state.telemetry_history[-60:]  # Last minute
    if not recent:
        return go.Figure()
    
    df = pd.DataFrame(recent)
    avg_power_kw = df['pdu_kw'].mean()
    avg_tokens_ps = df['tokens_ps'].mean()
    
    if avg_tokens_ps > 0:
        # Assume 100 tokens per prompt
        prompts_per_second = avg_tokens_ps / 100
        joules_per_second = avg_power_kw * 1000  # kW to W
        joules_per_prompt = joules_per_second / prompts_per_second if prompts_per_second > 0 else 0
    else:
        joules_per_prompt = 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=joules_per_prompt,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Energy Efficiency (J/prompt)"},
        delta={'reference': 120},  # Target efficiency
        gauge={
            'axis': {'range': [None, 300]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 100], 'color': "lightgreen"},
                {'range': [100, 150], 'color': "yellow"},
                {'range': [150, 300], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 120
            }
        }
    ))
    
    fig.update_layout(height=300)
    
    return fig


def create_mms_state_chart() -> go.Figure:
    """Create chart showing MMS state distribution."""
    if not state.mms_states:
        return go.Figure()
    
    # Count states
    state_counts = {'transient': 0, 'persistent': 0, 'nominal': 0}
    for rack_state in state.mms_states.values():
        state_counts[rack_state] = state_counts.get(rack_state, 0) + 1
    
    fig = go.Figure(data=[
        go.Pie(
            labels=list(state_counts.keys()),
            values=list(state_counts.values()),
            hole=0.4,
            marker=dict(colors=['lightgreen', 'orange', 'lightblue'])
        )
    ])
    
    fig.update_layout(
        title="MMS State Distribution (Current)",
        height=300
    )
    
    return fig


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Skadi - AI Datacenter Energy Optimizer</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 48px;
                margin: 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .header p {
                font-size: 18px;
                margin: 10px 0;
                opacity: 0.9;
            }
            .controls {
                text-align: center;
                margin: 20px 0;
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            .controls button {
                margin: 0 10px;
                padding: 12px 30px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: bold;
            }
            .controls button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            }
            .btn-start { background: #4CAF50; color: white; }
            .btn-stop { background: #f44336; color: white; }
            .btn-heat { background: #ff9800; color: white; }
            .btn-cool { background: #2196F3; color: white; }
            .status {
                text-align: center;
                font-size: 18px;
                margin: 10px 0;
                padding: 10px;
                background: rgba(255,255,255,0.1);
                border-radius: 5px;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            .chart-container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .metrics-row {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
            }
            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .kpi-card {
                background: rgba(255,255,255,0.15);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                backdrop-filter: blur(10px);
            }
            .kpi-value {
                font-size: 36px;
                font-weight: bold;
                margin: 10px 0;
            }
            .kpi-label {
                font-size: 14px;
                opacity: 0.8;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌡️ SKADI</h1>
            <p>AI Datacenter Energy Optimizer - Live Dashboard</p>
            <p style="font-size: 14px;">Measure → Decide → Act | FOSS • IMS • MMS</p>
        </div>
        
        <div class="controls">
            <button class="btn-start" onclick="startDemo()">▶ Start Demo</button>
            <button class="btn-stop" onclick="stopDemo()">⏹ Stop Demo</button>
            <button class="btn-heat" onclick="triggerHeatSpike()">🔥 Heat Spike</button>
            <button class="btn-cool" onclick="triggerOvercooled()">❄️ Overcooled</button>
        </div>
        
        <div class="status" id="status">Status: Initializing...</div>
        
        <div class="kpi-grid" id="kpis">
            <div class="kpi-card">
                <div class="kpi-label">Avg Inlet Temp</div>
                <div class="kpi-value" id="kpi-inlet">--</div>
                <div class="kpi-label">°C</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Avg Power</div>
                <div class="kpi-value" id="kpi-power">--</div>
                <div class="kpi-label">kW</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Throughput</div>
                <div class="kpi-value" id="kpi-tokens">--</div>
                <div class="kpi-label">tokens/s</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Latency (p95)</div>
                <div class="kpi-value" id="kpi-latency">--</div>
                <div class="kpi-label">ms</div>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="chart-container">
                <div id="heatmap"></div>
            </div>
            
            <div class="chart-container">
                <div id="timeseries"></div>
            </div>
            
            <div class="metrics-row">
                <div class="chart-container">
                    <div id="actions"></div>
                </div>
                <div class="chart-container">
                    <div id="mms-states"></div>
                </div>
            </div>
            
            <div class="chart-container">
                <div id="energy-gauge"></div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let updateInterval = null;
            
            async function updateCharts() {
                try {
                    const response = await fetch('/api/charts');
                    const data = await response.json();
                    
                    if (data.heatmap) {
                        Plotly.newPlot('heatmap', data.heatmap.data, data.heatmap.layout);
                    }
                    if (data.timeseries) {
                        Plotly.newPlot('timeseries', data.timeseries.data, data.timeseries.layout);
                    }
                    if (data.actions) {
                        Plotly.newPlot('actions', data.actions.data, data.actions.layout);
                    }
                    if (data.mms_states) {
                        Plotly.newPlot('mms-states', data.mms_states.data, data.mms_states.layout);
                    }
                    if (data.energy_gauge) {
                        Plotly.newPlot('energy-gauge', data.energy_gauge.data, data.energy_gauge.layout);
                    }
                    
                    // Update KPIs
                    if (data.kpis) {
                        document.getElementById('kpi-inlet').textContent = data.kpis.inlet_c.toFixed(1);
                        document.getElementById('kpi-power').textContent = data.kpis.power_kw.toFixed(1);
                        document.getElementById('kpi-tokens').textContent = Math.round(data.kpis.tokens_ps);
                        document.getElementById('kpi-latency').textContent = Math.round(data.kpis.latency_ms);
                    }
                } catch (e) {
                    console.error('Failed to update charts:', e);
                }
            }
            
            async function startDemo() {
                const response = await fetch('/api/start', {method: 'POST'});
                const data = await response.json();
                document.getElementById('status').textContent = 'Status: ' + data.status;
                
                if (!updateInterval) {
                    updateInterval = setInterval(updateCharts, 1000);
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
            
            async function triggerHeatSpike() {
                await fetch('/api/scenario/heat_spike', {method: 'POST'});
                document.getElementById('status').textContent = 'Status: Heat Spike Scenario Active 🔥';
            }
            
            async function triggerOvercooled() {
                await fetch('/api/scenario/overcooled', {method: 'POST'});
                document.getElementById('status').textContent = 'Status: Overcooled Scenario Active ❄️';
            }
            
            // Initial load
            updateCharts();
            document.getElementById('status').textContent = 'Status: Ready - Click Start Demo';
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/charts")
async def get_charts():
    """Get all chart data."""
    heatmap_fig = create_heatmap_figure()
    timeseries_fig = create_timeseries_figure()
    actions_fig = create_actions_timeline()
    mms_fig = create_mms_state_chart()
    energy_fig = create_energy_efficiency_gauge()
    
    # Calculate KPIs
    kpis = {'inlet_c': 0, 'power_kw': 0, 'tokens_ps': 0, 'latency_ms': 0}
    if state.telemetry_history:
        recent = state.telemetry_history[-10:]
        df = pd.DataFrame(recent)
        kpis = {
            'inlet_c': df['inlet_c'].mean(),
            'power_kw': df['pdu_kw'].mean(),
            'tokens_ps': df['tokens_ps'].mean(),
            'latency_ms': df['latency_p95_ms'].mean()
        }
    
    return {
        'heatmap': heatmap_fig.to_dict() if heatmap_fig.data else None,
        'timeseries': timeseries_fig.to_dict() if timeseries_fig.data else None,
        'actions': actions_fig.to_dict() if actions_fig.data else None,
        'mms_states': mms_fig.to_dict() if mms_fig.data else None,
        'energy_gauge': energy_fig.to_dict() if energy_fig.data else None,
        'kpis': kpis
    }


# Demo control endpoints
demo_task = None
demo_running = False


async def demo_loop():
    """Main demo loop generating synthetic data."""
    global demo_running
    
    logger.info("Starting demo loop...")
    
    # Initialize MMS filters for all racks
    for row in ['A', 'B', 'C', 'D', 'E', 'F']:
        for pos in range(1, 13):
            rack_id = f"R-{row}-{pos:02d}"
            state.mms_filters[rack_id] = MMSFilter()
    
    while demo_running:
        try:
            # Generate telemetry for all racks
            now = datetime.utcnow()
            
            for row in ['A', 'B', 'C', 'D', 'E', 'F']:
                for pos in range(1, 13):
                    rack_id = f"R-{row}-{pos:02d}"
                    
                    # Determine profile based on scenario
                    profile = 'nominal'
                    if state.scenario == 'heat_spike' and row == 'C':
                        profile = 'thermal_event'
                    elif state.scenario == 'overcooled' and row == 'E':
                        profile = 'overcooled'
                    
                    # Generate sample
                    sample = generator.generate_sample(rack_id, now, profile=profile)
                    state.add_telemetry(sample)
                    
                    # Score with IMS
                    if state.ims_scorer:
                        try:
                            deviation = state.ims_scorer.score_sample(sample)
                            level = 'nominal'
                            if deviation >= state.ims_trainer.tau_persist:
                                level = 'critical'
                            elif deviation >= state.ims_trainer.tau_fast:
                                level = 'warning'
                            
                            state.add_ims_score(rack_id, deviation, level)
                            
                            # Update MMS
                            mms_filter = state.mms_filters.get(rack_id)
                            if mms_filter:
                                mms_state = mms_filter.update(deviation)
                                state.update_mms_state(rack_id, mms_state)
                                
                                # Generate actions if persistent anomaly
                                if mms_state == 'persistent' and deviation >= state.ims_trainer.tau_fast:
                                    # Simple action generation
                                    if level == 'critical':
                                        state.add_action({
                                            'ts': now.isoformat(),
                                            'rack_id': rack_id,
                                            'action_type': 'fan_rpm',
                                            'params': {'delta_pct': 10},
                                            'reason': f'Critical deviation D(x)={deviation:.2f}'
                                        })
                        except Exception as e:
                            logger.error(f"Error scoring sample: {e}")
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in demo loop: {e}")
            await asyncio.sleep(1)
    
    logger.info("Demo loop stopped")


@app.post("/api/start")
async def start_demo():
    """Start the demo."""
    global demo_task, demo_running
    
    if not demo_running:
        demo_running = True
        demo_task = asyncio.create_task(demo_loop())
        return {"status": "Demo started"}
    return {"status": "Demo already running"}


@app.post("/api/stop")
async def stop_demo():
    """Stop the demo."""
    global demo_running
    
    demo_running = False
    state.scenario = None
    return {"status": "Demo stopped"}


@app.post("/api/scenario/{scenario_name}")
async def trigger_scenario(scenario_name: str):
    """Trigger a demo scenario."""
    if scenario_name in ['heat_spike', 'overcooled']:
        state.scenario = scenario_name
        state.scenario_start = datetime.utcnow()
        return {"status": f"Triggered {scenario_name} scenario"}
    return {"status": "Unknown scenario"}


if __name__ == "__main__":
    logger.info("Starting Skadi Visualization Dashboard...")
    logger.info("Open browser to: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
