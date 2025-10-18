"""Mock action executors for demo."""
from typing import Dict, Any, Optional
from datetime import datetime
from core.logging import logger
from core.config import settings


class SchedulerExecutor:
    """Mock executor for scheduling actions (routing, batching, admission)."""
    
    def __init__(self):
        """Initialize scheduler executor."""
        self.current_batch_window_ms = 180
        self.traffic_distribution = {}  # rack_id -> traffic_pct
        self.paused_jobs = []
    
    async def increase_batch_window(self, delta_ms: float) -> Dict[str, Any]:
        """Increase batch processing window.
        
        Args:
            delta_ms: Milliseconds to add to batch window
            
        Returns:
            Execution result
        """
        old_value = self.current_batch_window_ms
        self.current_batch_window_ms += delta_ms
        
        logger.info(f"[MOCK] Increased batch window: {old_value}ms -> {self.current_batch_window_ms}ms")
        
        return {
            'status': 'applied',
            'old_value': old_value,
            'new_value': self.current_batch_window_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def shift_traffic(self, traffic_pct: float, target_racks: list) -> Dict[str, Any]:
        """Shift traffic to specified racks.
        
        Args:
            traffic_pct: Percentage of traffic to shift
            target_racks: Target rack IDs
            
        Returns:
            Execution result
        """
        logger.info(f"[MOCK] Shifting {traffic_pct}% traffic to racks: {target_racks}")
        
        # Update distribution (simplified)
        for rack_id in target_racks:
            self.traffic_distribution[rack_id] = self.traffic_distribution.get(rack_id, 0) + traffic_pct / len(target_racks)
        
        return {
            'status': 'applied',
            'traffic_pct': traffic_pct,
            'target_racks': target_racks,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def pause_jobs(self, priority_threshold: int, max_pause_pct: float) -> Dict[str, Any]:
        """Pause low-priority jobs.
        
        Args:
            priority_threshold: Pause jobs with priority >= this
            max_pause_pct: Maximum percentage of jobs to pause
            
        Returns:
            Execution result
        """
        logger.info(f"[MOCK] Pausing jobs with priority>={priority_threshold} (max {max_pause_pct}%)")
        
        # Mock: track paused count
        paused_count = int(100 * max_pause_pct / 100)  # Assume 100 jobs
        self.paused_jobs.extend([f"job_{i}" for i in range(paused_count)])
        
        return {
            'status': 'applied',
            'priority_threshold': priority_threshold,
            'paused_count': paused_count,
            'timestamp': datetime.utcnow().isoformat()
        }


class BMSExecutor:
    """Mock executor for BMS actions (CRAC, CDU, fans, pumps)."""
    
    def __init__(self):
        """Initialize BMS executor."""
        self.supply_temp_c = 18.0
        self.fan_rpm_pct = 65.0
        self.pump_rpm_pct = 58.0
        self.last_write = {}  # Track last write per device
    
    def _check_rate_limit(self, device: str) -> bool:
        """Check if write is rate-limited.
        
        Args:
            device: Device identifier
            
        Returns:
            True if write is allowed
        """
        if device in self.last_write:
            elapsed = (datetime.utcnow() - self.last_write[device]).total_seconds()
            if elapsed < settings.write_rate_limit_s:
                logger.warning(f"[MOCK] BMS write rate-limited for {device} ({elapsed:.0f}s < {settings.write_rate_limit_s}s)")
                return False
        return True
    
    async def set_supply_temp(self, delta_c: float) -> Dict[str, Any]:
        """Adjust CRAC supply temperature.
        
        Args:
            delta_c: Temperature change in Celsius
            
        Returns:
            Execution result
        """
        if not self._check_rate_limit('crac_supply'):
            return {'status': 'rate_limited', 'device': 'crac_supply'}
        
        old_value = self.supply_temp_c
        self.supply_temp_c += delta_c
        self.last_write['crac_supply'] = datetime.utcnow()
        
        logger.info(f"[MOCK] CRAC supply temp: {old_value}°C -> {self.supply_temp_c}°C")
        
        return {
            'status': 'applied',
            'device': 'crac_supply',
            'old_value': old_value,
            'new_value': self.supply_temp_c,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def set_fan_rpm(self, delta_pct: float) -> Dict[str, Any]:
        """Adjust fan speed.
        
        Args:
            delta_pct: RPM percentage change
            
        Returns:
            Execution result
        """
        if not self._check_rate_limit('fan_rpm'):
            return {'status': 'rate_limited', 'device': 'fan_rpm'}
        
        old_value = self.fan_rpm_pct
        self.fan_rpm_pct = max(45, min(100, self.fan_rpm_pct + delta_pct))
        self.last_write['fan_rpm'] = datetime.utcnow()
        
        logger.info(f"[MOCK] Fan RPM: {old_value}% -> {self.fan_rpm_pct}%")
        
        return {
            'status': 'applied',
            'device': 'fan_rpm',
            'old_value': old_value,
            'new_value': self.fan_rpm_pct,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def set_pump_rpm(self, delta_pct: float) -> Dict[str, Any]:
        """Adjust pump speed.
        
        Args:
            delta_pct: RPM percentage change
            
        Returns:
            Execution result
        """
        if not self._check_rate_limit('cdu_pump'):
            return {'status': 'rate_limited', 'device': 'cdu_pump'}
        
        old_value = self.pump_rpm_pct
        self.pump_rpm_pct = max(40, min(85, self.pump_rpm_pct + delta_pct))
        self.last_write['cdu_pump'] = datetime.utcnow()
        
        logger.info(f"[MOCK] Pump RPM: {old_value}% -> {self.pump_rpm_pct}%")
        
        return {
            'status': 'applied',
            'device': 'cdu_pump',
            'old_value': old_value,
            'new_value': self.pump_rpm_pct,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global executor instances
scheduler_executor = SchedulerExecutor()
bms_executor = BMSExecutor()
