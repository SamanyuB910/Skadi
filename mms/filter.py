"""MMS (Meta Monitoring System) filter for deviation interpretation."""
from typing import Dict, Any, Literal
from collections import deque
from core.config import settings
from core.logging import logger


MMSState = Literal["transient", "persistent"]


class MMSFilter:
    """EMA + hysteresis filter to classify deviations as transient or persistent."""
    
    def __init__(
        self,
        alpha: float = None,
        persist_ticks: int = None,
        tau_fast: float = None,
        tau_persist: float = None
    ):
        """Initialize MMS filter.
        
        Args:
            alpha: EMA smoothing factor (default from config)
            persist_ticks: Consecutive ticks above tau_persist to flip to persistent
            tau_fast: Fast deviation threshold
            tau_persist: Persistent deviation threshold
        """
        self.alpha = alpha or settings.mms_ema_alpha
        self.persist_ticks = persist_ticks or settings.mms_persist_ticks
        self.tau_fast = tau_fast
        self.tau_persist = tau_persist
        
        self.ema = 0.0
        self.state: MMSState = "transient"
        self.consecutive_high = 0
        self.consecutive_low = 0
        self.history = deque(maxlen=100)  # Keep recent history
    
    def update_thresholds(self, tau_fast: float, tau_persist: float):
        """Update threshold values.
        
        Args:
            tau_fast: New fast threshold
            tau_persist: New persistent threshold
        """
        self.tau_fast = tau_fast
        self.tau_persist = tau_persist
        logger.info(f"MMS thresholds updated: tau_fast={tau_fast:.3f}, tau_persist={tau_persist:.3f}")
    
    def update(self, deviation: float) -> Dict[str, Any]:
        """Update filter with new deviation score.
        
        Args:
            deviation: Current deviation score D(x)
            
        Returns:
            Dictionary with ema, state, and metadata
        """
        if self.tau_fast is None or self.tau_persist is None:
            logger.warning("MMS thresholds not set, using deviation as-is")
            return {
                'ema': deviation,
                'state': 'transient',
                'raw_deviation': deviation
            }
        
        # Update EMA
        if self.ema == 0.0:
            self.ema = deviation
        else:
            self.ema = self.alpha * deviation + (1 - self.alpha) * self.ema
        
        # Track consecutive ticks above/below thresholds
        if self.ema > self.tau_persist:
            self.consecutive_high += 1
            self.consecutive_low = 0
        else:
            self.consecutive_high = 0
            if self.ema < self.tau_fast:
                self.consecutive_low += 1
            else:
                self.consecutive_low = 0
        
        # State transition logic with hysteresis
        if self.state == "transient":
            # Flip to persistent only if EMA > tau_persist for N consecutive ticks
            if self.consecutive_high >= self.persist_ticks:
                self.state = "persistent"
                logger.warning(f"MMS state changed to PERSISTENT (ema={self.ema:.3f})")
        else:  # state == "persistent"
            # Flip back to transient if EMA drops below tau_fast for N consecutive ticks
            if self.consecutive_low >= self.persist_ticks:
                self.state = "transient"
                logger.info(f"MMS state recovered to TRANSIENT (ema={self.ema:.3f})")
        
        # Store in history
        result = {
            'ema': self.ema,
            'state': self.state,
            'raw_deviation': deviation,
            'consecutive_high': self.consecutive_high,
            'consecutive_low': self.consecutive_low
        }
        self.history.append(result)
        
        return result
    
    def reset(self):
        """Reset filter state."""
        self.ema = 0.0
        self.state = "transient"
        self.consecutive_high = 0
        self.consecutive_low = 0
        self.history.clear()
        logger.info("MMS filter reset")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current filter state.
        
        Returns:
            Dictionary with current state information
        """
        return {
            'ema': self.ema,
            'state': self.state,
            'consecutive_high': self.consecutive_high,
            'consecutive_low': self.consecutive_low,
            'history_length': len(self.history)
        }
