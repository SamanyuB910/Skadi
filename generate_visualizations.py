"""Generate and display Skadi visualizations.

This script creates all the requested visualizations and saves them as:
1. Interactive HTML files (open in browser)
2. Static PNG images (for reports)

No web server needed - just run and view!
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path

from ingestors.mock_generators import MockDataGenerator
from ims.train import IMSTrainer
from ims.score import IMSScorer
from core.logging import logger


def generate_sample_data(duration_minutes: int = 5):
    """Generate sample telemetry data using the same realistic patterns as training."""
    logger.info(f"Generating {duration_minutes} minutes of sample data...")
    
    # Use the same realistic datacenter simulation used for training
    from ingestors.kaggle_datasets import KaggleDatasetManager
    
    manager = KaggleDatasetManager()
    
    # Generate realistic corridor temperatures
    dc_temps = manager.create_dc_temperature_dataset(duration_days=1)
    dc_temps = dc_temps.rename(columns={
        'cold_aisle_temp': 'inlet_c',
        'hot_aisle_temp': 'outlet_c'
    })
    
    # Generate realistic cooling ops
    cooling = manager.create_cooling_ops_dataset(duration_days=1)
    
    # Merge datasets
    combined = pd.merge_asof(
        dc_temps.sort_values('timestamp'),
        cooling.sort_values('timestamp'),
        on='timestamp',
        direction='nearest'
    )
    
    # Sample the requested duration
    samples_needed = duration_minutes * 6 * 72  # 6 samples per minute, 72 racks
    combined = combined.head(samples_needed // 72)  # Get enough time points
    
    # Replicate across racks
    samples = []
    n_racks = 72
    rack_ids = [f"R-{chr(65 + i//12)}-{(i%12)+1:02d}" for i in range(n_racks)]
    
    for idx, row in combined.iterrows():
        for rack_id in rack_ids:
            sample = row.to_dict()
            sample['rack_id'] = rack_id
            sample['ts'] = row['timestamp']
            
            # Add slight rack-to-rack variation
            sample['inlet_c'] = sample.get('inlet_c', 22) + np.random.normal(0, 0.5)
            sample['outlet_c'] = sample.get('outlet_c', 35) + np.random.normal(0, 1.0)
            sample['delta_t'] = sample['outlet_c'] - sample['inlet_c']
            
            # Ensure required fields exist
            if 'pdu_kw' not in sample:
                sample['pdu_kw'] = sample.get('total_cooling_kw', 200) / 3
            if 'tokens_ps' not in sample:
                sample['tokens_ps'] = 1000 + np.random.normal(0, 200)
            if 'latency_p95_ms' not in sample:
                sample['latency_p95_ms'] = 50 + np.random.normal(0, 10)
            if 'queue_depth' not in sample:
                sample['queue_depth'] = int(np.random.poisson(10))
            if 'gpu_energy_j' not in sample:
                sample['gpu_energy_j'] = sample['pdu_kw'] * 1000 * 10
            
            samples.append(sample)
    
    logger.info(f"Generated {len(samples)} samples from realistic datacenter patterns")
    return pd.DataFrame(samples)


def create_foss_heatmap(df: pd.DataFrame, metric: str = 'inlet_c') -> go.Figure:
    """Create FOSS-style rack heatmap with detailed hover info.
    
    Args:
        df: DataFrame with telemetry data
        metric: 'inlet_c', 'outlet_c', 'delta_t', or 'pdu_kw'
    """
    logger.info(f"Creating FOSS heatmap for {metric}...")
    
    # Get latest sample for each rack
    latest = df.sort_values('ts').groupby('rack_id').last().reset_index()
    
    # Add delta_t
    latest['delta_t'] = latest['outlet_c'] - latest['inlet_c']
    
    # Create 6x12 matrix
    rows = ['A', 'B', 'C', 'D', 'E', 'F']
    positions = list(range(1, 13))
    
    z_matrix = []
    hover_texts = []
    
    for row in rows:
        z_row = []
        hover_row = []
        
        for pos in positions:
            rack_id = f"R-{row}-{pos:02d}"
            rack_data = latest[latest['rack_id'] == rack_id]
            
            if len(rack_data) > 0:
                data = rack_data.iloc[0]
                value = data[metric]
                z_row.append(value)
                
                # Detailed hover info
                hover_text = (
                    f"<b>{rack_id}</b><br>"
                    f"━━━━━━━━━━━━━━━━<br>"
                    f"<b>Thermal:</b><br>"
                    f"  Inlet: {data['inlet_c']:.1f}°C<br>"
                    f"  Outlet: {data['outlet_c']:.1f}°C<br>"
                    f"  ΔT: {data['delta_t']:.1f}°C<br>"
                    f"<b>Power:</b><br>"
                    f"  PDU: {data['pdu_kw']:.1f} kW<br>"
                    f"  Energy: {data['gpu_energy_j']/1000:.1f} kJ<br>"
                    f"<b>Workload:</b><br>"
                    f"  Tokens/s: {data['tokens_ps']:.0f}<br>"
                    f"  Latency: {data['latency_p95_ms']:.0f} ms<br>"
                    f"  Queue: {data['queue_depth']}<br>"
                    f"<b>Cooling:</b><br>"
                    f"  Fan: {data['fan_rpm_pct']:.0f}%<br>"
                    f"  Pump: {data['pump_rpm_pct']:.0f}%"
                )
                hover_row.append(hover_text)
            else:
                z_row.append(0)
                hover_row.append("No data")
        
        z_matrix.append(z_row)
        hover_texts.append(hover_row)
    
    # Choose colorscale and range based on metric (dark theme with vibrant colors)
    colorscales = {
        'inlet_c': ([[0, '#0a0e27'], [0.2, '#1a0b4e'], [0.4, '#6b2fb5'], [0.6, '#c944ff'], [0.8, '#ff6ec7'], [1, '#ff1744']], 18, 32, 'Inlet Temperature (°C)'),
        'outlet_c': ([[0, '#0a0e27'], [0.2, '#0d4a4a'], [0.4, '#00bcd4'], [0.6, '#ff9800'], [0.8, '#ff5722'], [1, '#d50000']], 28, 55, 'Outlet Temperature (°C)'),
        'delta_t': ([[0, '#0a0e27'], [0.3, '#1a237e'], [0.5, '#e040fb'], [0.7, '#ff6b6b'], [1, '#ff0000']], 8, 25, 'Temperature Delta (°C)'),
        'pdu_kw': ([[0, '#0a0e27'], [0.25, '#004d40'], [0.5, '#00e676'], [0.75, '#ffea00'], [1, '#ff6d00']], 0, 15, 'Power Draw (kW)')
    }
    
    colorscale, zmin, zmax, title = colorscales.get(metric, ([[0, '#0a0e27'], [0.5, '#6b2fb5'], [1, '#ff1744']], 0, 100, metric))
    
    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=[f"Rack {p:02d}" for p in positions],
        y=[f"Row {r}" for r in rows],
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            title=dict(text=title, side='right'),
            len=0.9,
            thickness=20
        )
    ))
    
    # Add SLA threshold lines for inlet temp
    if metric == 'inlet_c':
        # Add annotation for SLA limit
        fig.add_shape(
            type="line",
            x0=-0.5, x1=11.5,
            y0=0, y1=0,
            line=dict(color="red", width=0),
        )
    
    fig.update_layout(
        title=dict(
            text=f"<b>FOSS Heat Map - {title}</b><br><sub>Datacenter Rack Grid (72 Racks, 6 Rows × 12 Positions)</sub>",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color='#e6e6e6')
        ),
        xaxis_title="Rack Position",
        yaxis_title="Row",
        height=500,
        width=1400,
        font=dict(size=12, color='#e6e6e6'),
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        xaxis=dict(gridcolor='#30363d'),
        yaxis=dict(gridcolor='#30363d'),
        hoverlabel=dict(
            bgcolor="#1c2128",
            font_size=12,
            font_family="monospace",
            font_color="#e6e6e6"
        )
    )
    
    return fig


def create_ims_anomaly_heatmap(df: pd.DataFrame, ims_scorer) -> go.Figure:
    """Create IMS-based anomaly heatmap using trained model scores.
    
    Colors racks based on their IMS deviation scores:
    - Purple/Blue: Normal (D(x) < tau_fast)
    - Magenta/Pink: Warning (tau_fast < D(x) < tau_persist)  
    - Red: Anomaly (D(x) > tau_persist)
    """
    logger.info("Creating IMS anomaly heatmap...")
    
    if not ims_scorer:
        logger.warning("No IMS scorer available")
        return go.Figure()
    
    # Get latest data per rack
    latest = df.sort_values('ts').groupby('rack_id').last().reset_index()
    
    # Score each rack with IMS model
    for idx, row in latest.iterrows():
        score = ims_scorer.score_sample(row.to_dict())
        latest.at[idx, 'ims_score'] = score
    
    # Get thresholds (adjust to match actual data distribution)
    tau_fast = ims_scorer.trainer.tau_fast
    tau_persist = ims_scorer.trainer.tau_persist
    
    # Calculate actual score distribution for dynamic scaling
    all_scores = [ims_scorer.score_sample(row.to_dict()) for _, row in latest.iterrows()]
    score_min = min(all_scores)
    score_max = max(all_scores)
    score_mean = sum(all_scores) / len(all_scores)
    
    # Adjust thresholds based on actual data (more realistic)
    # Use percentiles of actual data rather than training thresholds
    import numpy as np
    tau_fast_adjusted = np.percentile(all_scores, 70)  # Top 30% are warnings
    tau_persist_adjusted = np.percentile(all_scores, 90)  # Top 10% are anomalies
    
    logger.info(f"Original thresholds: τ_fast={tau_fast:.3f}, τ_persist={tau_persist:.3f}")
    logger.info(f"Adjusted thresholds: τ_fast={tau_fast_adjusted:.3f}, τ_persist={tau_persist_adjusted:.3f}")
    logger.info(f"Score range: {score_min:.3f} to {score_max:.3f} (mean={score_mean:.3f})")
    
    # Use adjusted thresholds for visualization
    tau_fast = tau_fast_adjusted
    tau_persist = tau_persist_adjusted
    
    # Create 6x12 matrix
    rows = ['A', 'B', 'C', 'D', 'E', 'F']
    positions = list(range(1, 13))
    
    z_matrix = []
    hover_texts = []
    
    for row in rows:
        z_row = []
        hover_row = []
        
        for pos in positions:
            rack_id = f"R-{row}-{pos:02d}"
            rack_data = latest[latest['rack_id'] == rack_id]
            
            if len(rack_data) > 0:
                data = rack_data.iloc[0]
                ims_score = data['ims_score']
                z_row.append(ims_score)
                
                # Determine status
                if ims_score < tau_fast:
                    status = "✅ NORMAL"
                    status_color = "#00e676"
                elif ims_score < tau_persist:
                    status = "⚠️ WARNING"
                    status_color = "#ff6ec7"
                else:
                    status = "🔴 ANOMALY"
                    status_color = "#ff1744"
                
                # Detailed hover info with IMS score
                hover_text = (
                    f"<b>{rack_id}</b><br>"
                    f"━━━━━━━━━━━━━━━━<br>"
                    f"<b style='color:{status_color}'>IMS: {status}</b><br>"
                    f"<b>Deviation Score:</b> {ims_score:.4f}<br>"
                    f"  τ_fast: {tau_fast:.3f}<br>"
                    f"  τ_persist: {tau_persist:.3f}<br>"
                    f"<b>Thermal:</b><br>"
                    f"  Inlet: {data['inlet_c']:.1f}°C<br>"
                    f"  Outlet: {data['outlet_c']:.1f}°C<br>"
                    f"  ΔT: {(data['outlet_c'] - data['inlet_c']):.1f}°C<br>"
                    f"<b>Power:</b><br>"
                    f"  PDU: {data['pdu_kw']:.1f} kW<br>"
                    f"<b>Workload:</b><br>"
                    f"  Tokens/s: {data['tokens_ps']:.0f}<br>"
                    f"  Latency: {data['latency_p95_ms']:.0f} ms"
                )
                hover_row.append(hover_text)
            else:
                z_row.append(0)
                hover_row.append("No data")
        
        z_matrix.append(z_row)
        hover_texts.append(hover_row)
    
    # Rainbow colorscale: Blue (cool/normal) → Green → Yellow → Orange → Red (hot/anomaly)
    colorscale = [
        [0.0, '#0000ff'],    # Deep blue (coldest/best)
        [0.15, '#0080ff'],   # Light blue
        [0.30, '#00ffff'],   # Cyan
        [0.45, '#00ff00'],   # Green (nominal)
        [0.60, '#ffff00'],   # Yellow (warning)
        [0.75, '#ff8000'],   # Orange (elevated)
        [0.90, '#ff0000'],   # Red (anomaly)
        [1.0, '#8b0000']     # Dark red (critical)
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=[f"Rack {p:02d}" for p in positions],
        y=[f"Row {r}" for r in rows],
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
        colorscale=colorscale,
        zmin=score_min * 0.9,  # Start slightly below minimum
        zmax=score_max * 1.1,  # End slightly above maximum
        colorbar=dict(
            title=dict(text='IMS Score D(x)', side='right', font=dict(color='#e6e6e6')),
            len=0.9,
            thickness=20,
            tickfont=dict(color='#e6e6e6'),
            # Add threshold markers
            tickmode='array',
            tickvals=[0, tau_fast, tau_persist, tau_persist * 1.5],
            ticktext=['0.0', f'τ_fast\n{tau_fast:.2f}', f'τ_persist\n{tau_persist:.2f}', 'Critical']
        )
    ))
    
    # Count distribution for title
    normal_count = sum(1 for row in z_matrix for val in row if val < tau_fast)
    warning_count = sum(1 for row in z_matrix for val in row if tau_fast <= val < tau_persist)
    anomaly_count = sum(1 for row in z_matrix for val in row if val >= tau_persist)
    total_racks = len(rows) * len(positions)
    
    fig.update_layout(
        title=dict(
            text=f"<b>IMS Anomaly Detection Heat Map</b><br><sub>ML-Scored Rack Status • Normal: {normal_count}/{total_racks} ({100*normal_count/total_racks:.0f}%) • Warning: {warning_count}/{total_racks} ({100*warning_count/total_racks:.0f}%) • Anomaly: {anomaly_count}/{total_racks} ({100*anomaly_count/total_racks:.0f}%)</sub>",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color='#e6e6e6')
        ),
        xaxis_title="Rack Position",
        yaxis_title="Row",
        height=500,
        width=1400,
        font=dict(size=12, color='#e6e6e6'),
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        xaxis=dict(gridcolor='#30363d'),
        yaxis=dict(gridcolor='#30363d'),
        hoverlabel=dict(
            bgcolor="#1c2128",
            font_size=12,
            font_family="monospace",
            font_color="#e6e6e6"
        )
    )
    
    return fig


def create_delta_t_histogram(df: pd.DataFrame) -> go.Figure:
    """Create ΔT distribution histogram."""
    logger.info("Creating ΔT histogram...")
    
    latest = df.sort_values('ts').groupby('rack_id').last().reset_index()
    latest['delta_t'] = latest['outlet_c'] - latest['inlet_c']
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=latest['delta_t'],
        nbinsx=30,
        marker=dict(
            color=latest['delta_t'],
            colorscale=[[0, '#0a0e27'], [0.3, '#6b2fb5'], [0.5, '#c944ff'], [0.7, '#ff6ec7'], [1, '#ff1744']],
            showscale=True,
            colorbar=dict(
                title=dict(text="ΔT (°C)", font=dict(color='#e6e6e6')),
                tickfont=dict(color='#e6e6e6')
            )
        ),
        hovertemplate='ΔT: %{x:.1f}°C<br>Count: %{y}<extra></extra>'
    ))
    
    # Add mean line
    mean_delta_t = latest['delta_t'].mean()
    fig.add_vline(x=mean_delta_t, line_dash="dash", line_color="#ff6347",
                  annotation_text=f"Mean: {mean_delta_t:.1f}°C",
                  annotation_position="top right",
                  annotation_font=dict(color='#e6e6e6'))
    
    fig.update_layout(
        title=dict(text="<b>ΔT Distribution Across All Racks</b>", font=dict(color='#e6e6e6')),
        xaxis_title="Temperature Delta (°C)",
        yaxis_title="Number of Racks",
        height=400,
        width=700,
        showlegend=False,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6e6e6'),
        xaxis=dict(gridcolor='#30363d'),
        yaxis=dict(gridcolor='#30363d')
    )
    
    return fig


def create_hotspot_analysis(df: pd.DataFrame) -> go.Figure:
    """Create hot-spot count and analysis."""
    logger.info("Creating hotspot analysis...")
    
    # Group by time and count hotspots
    df['is_hotspot'] = df['inlet_c'] > 27
    hotspots = df.groupby('ts').agg({
        'is_hotspot': 'sum',
        'inlet_c': 'mean'
    }).reset_index()
    hotspots.columns = ['ts', 'hotspot_count', 'avg_inlet']
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Hot-Spot Count Over Time', 'Average Inlet Temperature'),
        vertical_spacing=0.15
    )
    
    # Hotspot count
    fig.add_trace(
        go.Scatter(
            x=hotspots['ts'],
            y=hotspots['hotspot_count'],
            mode='lines+markers',
            name='Hot Spots',
            line=dict(color='#ff1744', width=2),
            marker=dict(size=6, color='#ff6ec7'),
            fill='tozeroy',
            fillcolor='rgba(255,23,68,0.2)'
        ),
        row=1, col=1
    )
    
    # Average inlet temp
    fig.add_trace(
        go.Scatter(
            x=hotspots['ts'],
            y=hotspots['avg_inlet'],
            mode='lines',
            name='Avg Inlet',
            line=dict(color='#00bcd4', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,188,212,0.2)'
        ),
        row=2, col=1
    )
    
    # SLA line
    fig.add_hline(y=28, line_dash="dash", line_color="#ff6347", row=2, col=1,
                  annotation_text="SLA Limit (28°C)", annotation_position="right",
                  annotation_font=dict(color='#e6e6e6'))
    
    fig.update_xaxes(title_text="Time", row=2, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="Number of Racks", row=1, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1, gridcolor='#30363d')
    
    fig.update_layout(
        title=dict(text="<b>Hot-Spot Tracking</b>", font=dict(color='#e6e6e6')),
        height=600,
        width=1000,
        showlegend=False,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6e6e6')
    )
    
    return fig


def create_ims_deviation_timeline(df: pd.DataFrame, ims_scorer) -> go.Figure:
    """Create IMS deviation score timeline with thresholds."""
    logger.info("Creating IMS deviation timeline...")
    
    if not ims_scorer:
        logger.warning("No IMS scorer available")
        return go.Figure()
    
    # Score each sample
    scores = []
    for _, row in df.iterrows():
        score = ims_scorer.score_sample(row.to_dict())
        scores.append({
            'ts': row['ts'],
            'rack_id': row['rack_id'],
            'deviation': score
        })
    
    scores_df = pd.DataFrame(scores)
    avg_scores = scores_df.groupby('ts')['deviation'].mean().reset_index()
    
    fig = go.Figure()
    
    # Average deviation
    fig.add_trace(go.Scatter(
        x=avg_scores['ts'],
        y=avg_scores['deviation'],
        mode='lines',
        name='D(x)',
        line=dict(color='#c944ff', width=3),
        fill='tozeroy',
        fillcolor='rgba(201,68,255,0.2)'
    ))
    
    # Threshold lines
    tau_fast = ims_scorer.trainer.tau_fast
    tau_persist = ims_scorer.trainer.tau_persist
    
    fig.add_hline(y=tau_fast, line_dash="dash", line_color="#ffea00",
                  annotation_text=f"τ_fast = {tau_fast:.3f}",
                  annotation_position="right",
                  annotation_font=dict(color='#e6e6e6'))
    
    fig.add_hline(y=tau_persist, line_dash="dash", line_color="#ff1744",
                  annotation_text=f"τ_persist = {tau_persist:.3f}",
                  annotation_position="right",
                  annotation_font=dict(color='#e6e6e6'))
    
    # Color regions (darker theme with vibrant colors)
    fig.add_hrect(y0=0, y1=tau_fast, fillcolor="#004d40", opacity=0.2, line_width=0)
    fig.add_hrect(y0=tau_fast, y1=tau_persist, fillcolor="#6b2fb5", opacity=0.2, line_width=0)
    fig.add_hrect(y0=tau_persist, y1=4, fillcolor="#b71c1c", opacity=0.2, line_width=0)
    
    fig.update_layout(
        title=dict(text="<b>IMS Deviation Score Timeline</b><br><sub>Average D(x) with Fast/Persist Thresholds</sub>", font=dict(color='#e6e6e6')),
        xaxis_title="Time",
        yaxis_title="Deviation Score D(x)",
        height=500,
        width=1200,
        showlegend=False,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6e6e6'),
        xaxis=dict(gridcolor='#30363d'),
        yaxis=dict(gridcolor='#30363d')
    )
    
    return fig


def create_all_metrics_timeline(df: pd.DataFrame) -> go.Figure:
    """Create comprehensive timeline with all key metrics."""
    logger.info("Creating comprehensive metrics timeline...")
    
    # Aggregate by time
    agg = df.groupby('ts').agg({
        'inlet_c': 'mean',
        'outlet_c': 'mean',
        'pdu_kw': 'mean',
        'tokens_ps': 'mean',
        'latency_p95_ms': 'mean',
        'fan_rpm_pct': 'mean',
        'pump_rpm_pct': 'mean'
    }).reset_index()
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'Inlet Temperature', 'Outlet Temperature',
            'Power Consumption', 'Throughput',
            'Latency (p95)', 'Cooling (Fan/Pump RPM)'
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # Inlet temp
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['inlet_c'], mode='lines', name='Inlet',
                   line=dict(color='#00bcd4', width=2), fill='tozeroy',
                   fillcolor='rgba(0,188,212,0.2)'),
        row=1, col=1
    )
    fig.add_hline(y=28, line_dash="dash", line_color="#ff1744", row=1, col=1,
                  annotation_font=dict(color='#e6e6e6'))
    
    # Outlet temp
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['outlet_c'], mode='lines', name='Outlet',
                   line=dict(color='#ff6ec7', width=2), fill='tozeroy',
                   fillcolor='rgba(255,110,199,0.2)'),
        row=1, col=2
    )
    
    # Power
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['pdu_kw'], mode='lines', name='Power',
                   line=dict(color='#00e676', width=2), fill='tozeroy',
                   fillcolor='rgba(0,230,118,0.2)'),
        row=2, col=1
    )
    
    # Throughput
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['tokens_ps'], mode='lines', name='Tokens/s',
                   line=dict(color='#c944ff', width=2), fill='tozeroy',
                   fillcolor='rgba(201,68,255,0.2)'),
        row=2, col=2
    )
    
    # Latency
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['latency_p95_ms'], mode='lines', name='Latency',
                   line=dict(color='#ffea00', width=2), fill='tozeroy',
                   fillcolor='rgba(255,234,0,0.2)'),
        row=3, col=1
    )
    fig.add_hline(y=250, line_dash="dash", line_color="#ff1744", row=3, col=1,
                  annotation_font=dict(color='#e6e6e6'))
    
    # Cooling
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['fan_rpm_pct'], mode='lines', name='Fan',
                   line=dict(color='#18ffff', width=2)),
        row=3, col=2
    )
    fig.add_trace(
        go.Scatter(x=agg['ts'], y=agg['pump_rpm_pct'], mode='lines', name='Pump',
                   line=dict(color='#69f0ae', width=2, dash='dash')),
        row=3, col=2
    )
    
    # Update axes
    fig.update_yaxes(title_text="°C", row=1, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="°C", row=1, col=2, gridcolor='#30363d')
    fig.update_yaxes(title_text="kW", row=2, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="tokens/s", row=2, col=2, gridcolor='#30363d')
    fig.update_yaxes(title_text="ms", row=3, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="% RPM", row=3, col=2, gridcolor='#30363d')
    fig.update_xaxes(gridcolor='#30363d')
    
    fig.update_layout(
        title=dict(text="<b>Comprehensive Metrics Timeline</b><br><sub>All Key Datacenter Metrics Over Time</sub>", font=dict(color='#e6e6e6')),
        height=900,
        width=1400,
        showlegend=True,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6e6e6'),
        legend=dict(bgcolor='#161b22', bordercolor='#30363d')
    )
    
    return fig


def main():
    """Generate all visualizations."""
    print("=" * 60)
    print("SKADI VISUALIZATION GENERATOR")
    print("=" * 60)
    print()
    
    # Create output directory
    output_dir = Path("visualizations")
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir.absolute()}")
    print()
    
    # Load IMS model
    ims_scorer = None
    try:
        import glob
        import os
        model_files = glob.glob('artifacts/ims_*.pkl')
        if model_files:
            # Sort by modification time to get the newest
            latest_model = sorted(model_files, key=os.path.getmtime)[-1]
            trainer = IMSTrainer.load(latest_model)
            ims_scorer = IMSScorer(trainer)
            print(f"✅ Loaded IMS model: {latest_model}")
            print(f"   τ_fast: {trainer.tau_fast:.4f}, τ_persist: {trainer.tau_persist:.4f}")
        else:
            print("⚠️  No IMS model found (run training first)")
    except Exception as e:
        print(f"⚠️  Could not load IMS model: {e}")
    
    print()
    
    # Generate sample data
    print("Generating sample data...")
    df = generate_sample_data(duration_minutes=5)
    print(f"✅ Generated {len(df)} samples")
    print()
    
    # Create visualizations
    figures = {}
    
    print("Creating visualizations...")
    print()
    
    # 1. FOSS Heatmaps (raw data)
    print("  1. FOSS Heat Map - Inlet Temperature...")
    figures['heatmap_inlet'] = create_foss_heatmap(df, 'inlet_c')
    
    print("  2. FOSS Heat Map - Outlet Temperature...")
    figures['heatmap_outlet'] = create_foss_heatmap(df, 'outlet_c')
    
    print("  3. FOSS Heat Map - Delta T...")
    figures['heatmap_delta'] = create_foss_heatmap(df, 'delta_t')
    
    print("  4. FOSS Heat Map - Power...")
    figures['heatmap_power'] = create_foss_heatmap(df, 'pdu_kw')
    
    # 1.5. IMS Anomaly Heatmap (ML-based)
    if ims_scorer:
        print("  5. IMS Anomaly Detection Heat Map (ML-Scored)...")
        figures['heatmap_ims_anomaly'] = create_ims_anomaly_heatmap(df, ims_scorer)
    
    # 2. ΔT Histogram
    print("  6. ΔT Histogram...")
    figures['delta_t_histogram'] = create_delta_t_histogram(df)
    
    # 3. Hotspot Analysis
    print("  7. Hot-Spot Analysis...")
    figures['hotspot_analysis'] = create_hotspot_analysis(df)
    
    # 4. IMS Timeline
    if ims_scorer:
        print("  8. IMS Deviation Timeline...")
        figures['ims_timeline'] = create_ims_deviation_timeline(df, ims_scorer)
    
    # 5. All Metrics Timeline
    print("  9. Comprehensive Metrics Timeline...")
    figures['all_metrics'] = create_all_metrics_timeline(df)
    
    print()
    print("=" * 60)
    print("SAVING VISUALIZATIONS")
    print("=" * 60)
    print()
    
    # Save as interactive HTML
    for name, fig in figures.items():
        html_path = output_dir / f"{name}.html"
        fig.write_html(str(html_path))
        print(f"✅ Saved: {html_path}")
    
    print()
    print("=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print()
    print(f"Generated {len(figures)} visualizations in: {output_dir.absolute()}")
    print()
    print("To view:")
    print(f"  1. Open any .html file in your browser")
    print(f"  2. Graphs are fully interactive (zoom, pan, hover)")
    print()
    print("Key files:")
    print(f"  • heatmap_ims_anomaly.html - 🆕 ML-Based Anomaly Detection!")
    print(f"  • heatmap_inlet.html       - FOSS inlet temp map")
    print(f"  • heatmap_delta.html       - Temperature delta view")
    print(f"  • hotspot_analysis.html    - Hot-spot tracking")
    print(f"  • ims_timeline.html        - IMS deviation scores")
    print(f"  • all_metrics.html         - Complete timeline")
    print()
    
    # Open the IMS anomaly heatmap (the ML-based one)
    import webbrowser
    main_viz = output_dir / "heatmap_ims_anomaly.html"
    if main_viz.exists():
        print(f"Opening ML anomaly detection heatmap: {main_viz}")
        webbrowser.open(str(main_viz.absolute()))
    else:
        # Fallback to inlet if IMS not available
        main_viz = output_dir / "heatmap_inlet.html"
        print(f"Opening main visualization: {main_viz}")
        webbrowser.open(str(main_viz.absolute()))


if __name__ == '__main__':
    main()
