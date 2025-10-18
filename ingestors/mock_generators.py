"""Mock data generators for demo and testing purposes."""
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
from core.config import settings
from core.logging import logger


class MockDataGenerator:
    """Generate realistic telemetry data for demo scenarios."""
    
    # Rack layout: Rows A-F, 12 racks per row
    ROWS = ['A', 'B', 'C', 'D', 'E', 'F']
    RACKS_PER_ROW = 12
    
    def __init__(self, seed: int = 42):
        """Initialize mock generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        np.random.seed(seed)
        
        # Baseline operating conditions (nominal)
        self.baseline = {
            'inlet_c': 22.0,  # Cold aisle temperature
            'outlet_c': 35.0,  # Hot aisle temperature
            'pdu_kw': 8.5,  # Power draw
            'gpu_energy_j': 42000,  # GPU energy per tick (cumulative-like)
            'tokens_ps': 8500,  # Tokens per second
            'latency_p95_ms': 180,  # P95 latency
            'queue_depth': 35,  # Request queue depth
            'fan_rpm_pct': 65,  # Cooling fan speed
            'pump_rpm_pct': 58,  # Coolant pump speed
        }
        
        # Per-row variations (simulate aisle layout)
        self.row_modifiers = {
            'A': {'inlet_offset': -0.5, 'load_factor': 0.95},
            'B': {'inlet_offset': 0.0, 'load_factor': 1.0},
            'C': {'inlet_offset': 0.3, 'load_factor': 1.05},  # Slightly warmer
            'D': {'inlet_offset': -0.2, 'load_factor': 0.98},
            'E': {'inlet_offset': -1.5, 'load_factor': 0.85},  # Over-cooled
            'F': {'inlet_offset': 0.5, 'load_factor': 1.02},
        }
        
        # Scenario state
        self.active_scenarios: Dict[str, Dict[str, Any]] = {}
        self.cumulative_energy = {}  # Track cumulative energy per rack
        
        logger.info("Mock data generator initialized")
    
    def get_rack_ids(self) -> List[str]:
        """Get list of all rack IDs.
        
        Returns:
            List of rack ID strings
        """
        racks = []
        for row in self.ROWS:
            for i in range(1, self.RACKS_PER_ROW + 1):
                racks.append(f"R-{row}-{i:02d}")
        return racks
    
    def generate_sample(self, rack_id: str, ts: datetime) -> Dict[str, Any]:
        """Generate one telemetry sample for a rack.
        
        Args:
            rack_id: Rack identifier
            ts: Timestamp
            
        Returns:
            Telemetry dictionary
        """
        # Extract row from rack_id (e.g., "R-C-07" -> "C")
        row = rack_id.split('-')[1]
        row_mod = self.row_modifiers.get(row, {'inlet_offset': 0.0, 'load_factor': 1.0})
        
        # Apply row-specific modifiers
        inlet_c = self.baseline['inlet_c'] + row_mod['inlet_offset']
        load_factor = row_mod['load_factor']
        
        # Add random noise
        inlet_c += np.random.normal(0, 0.3)
        pdu_kw = self.baseline['pdu_kw'] * load_factor * (1 + np.random.normal(0, 0.05))
        tokens_ps = self.baseline['tokens_ps'] * load_factor * (1 + np.random.normal(0, 0.1))
        latency_p95_ms = self.baseline['latency_p95_ms'] * (1 + np.random.normal(0, 0.08))
        
        # Delta T scales with load
        delta_t = (self.baseline['outlet_c'] - self.baseline['inlet_c']) * load_factor
        outlet_c = inlet_c + delta_t + np.random.normal(0, 0.5)
        
        # GPU energy (simulate cumulative behavior with tick increments)
        if rack_id not in self.cumulative_energy:
            self.cumulative_energy[rack_id] = 0.0
        
        # Energy increment per tick (based on power and tick duration)
        tick_energy = pdu_kw * 0.7 * settings.mock_data_tick_s  # 70% GPU, rest aux
        self.cumulative_energy[rack_id] += tick_energy * 1000  # kJ -> J
        gpu_energy_j = self.cumulative_energy[rack_id]
        
        # Queue and cooling
        queue_depth = max(1, int(self.baseline['queue_depth'] * load_factor * (1 + np.random.normal(0, 0.15))))
        fan_rpm_pct = self.baseline['fan_rpm_pct'] * (1 + np.random.normal(0, 0.05))
        pump_rpm_pct = self.baseline['pump_rpm_pct'] * (1 + np.random.normal(0, 0.05))
        
        # Apply active scenarios
        sample = {
            'ts': ts.isoformat(),
            'rack_id': rack_id,
            'inlet_c': round(inlet_c, 2),
            'outlet_c': round(outlet_c, 2),
            'pdu_kw': round(pdu_kw, 2),
            'gpu_energy_j': round(gpu_energy_j, 1),
            'tokens_ps': round(tokens_ps, 1),
            'latency_p95_ms': round(latency_p95_ms, 1),
            'queue_depth': queue_depth,
            'fan_rpm_pct': round(fan_rpm_pct, 1),
            'pump_rpm_pct': round(pump_rpm_pct, 1),
        }
        
        # Apply scenario modifiers
        sample = self._apply_scenarios(sample, rack_id, ts)
        
        return sample
    
    def _apply_scenarios(self, sample: Dict[str, Any], rack_id: str, ts: datetime) -> Dict[str, Any]:
        """Apply active scenario effects to a sample.
        
        Args:
            sample: Base telemetry sample
            rack_id: Rack identifier
            ts: Current timestamp
            
        Returns:
            Modified sample
        """
        for scenario_id, scenario in self.active_scenarios.items():
            if not scenario.get('active', False):
                continue
            
            scenario_type = scenario['type']
            
            if scenario_type == 'add_ai_nodes_row_c':
                # Heat spike in Row C
                row = rack_id.split('-')[1]
                if row == 'C':
                    # Increase temperatures and power
                    sample['inlet_c'] += 2.5
                    sample['outlet_c'] += 4.5
                    sample['pdu_kw'] *= 1.25
                    sample['tokens_ps'] *= 1.3
                    sample['latency_p95_ms'] *= 1.15  # Slight latency increase
            
            elif scenario_type == 'overcooled_row_e':
                # Over-cooled Row E
                row = rack_id.split('-')[1]
                if row == 'E':
                    # Lower inlet, high fan RPM
                    sample['inlet_c'] -= 3.0
                    sample['fan_rpm_pct'] = min(100, sample['fan_rpm_pct'] * 1.3)
        
        return sample
    
    def start_scenario(self, scenario_type: str, duration_s: int = 300) -> str:
        """Start a demo scenario.
        
        Args:
            scenario_type: Type of scenario
            duration_s: Duration in seconds
            
        Returns:
            Scenario ID
        """
        scenario_id = f"{scenario_type}_{datetime.utcnow().timestamp()}"
        
        self.active_scenarios[scenario_id] = {
            'type': scenario_type,
            'active': True,
            'start_ts': datetime.utcnow(),
            'duration_s': duration_s
        }
        
        logger.info(f"Started scenario: {scenario_type} (id={scenario_id}, duration={duration_s}s)")
        
        return scenario_id
    
    def stop_scenario(self, scenario_id: str):
        """Stop a scenario.
        
        Args:
            scenario_id: Scenario identifier
        """
        if scenario_id in self.active_scenarios:
            self.active_scenarios[scenario_id]['active'] = False
            logger.info(f"Stopped scenario: {scenario_id}")
    
    def get_active_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Get list of active scenarios.
        
        Returns:
            Dictionary of active scenarios
        """
        return {
            sid: s for sid, s in self.active_scenarios.items()
            if s.get('active', False)
        }
    
    def generate_batch(self, ts: datetime, rack_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate telemetry for multiple racks.
        
        Args:
            ts: Timestamp
            rack_ids: Optional list of specific racks (defaults to all)
            
        Returns:
            List of telemetry samples
        """
        if rack_ids is None:
            rack_ids = self.get_rack_ids()
        
        return [self.generate_sample(rack_id, ts) for rack_id in rack_ids]
