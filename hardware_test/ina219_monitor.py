"""
INA219 Current Monitor Module

I2C-based current, voltage, and power monitoring with:
- Real-time power consumption display
- Overcurrent protection trigger
- Data logging to CSV
"""

import smbus2
import time
import threading
import csv
import os
from datetime import datetime
from typing import Callable, Optional, Dict, List


class INA219Monitor:
    """INA219 I2C Current/Voltage/Power Monitor"""
    
    # I2C Addresses (default or alternative)
    DEFAULT_ADDRESS = 0x40
    
    # Register addresses
    REG_CONFIG = 0x00
    REG_SHUNT_VOLTAGE = 0x01
    REG_BUS_VOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05
    
    # Configuration bits
    RESET_BIT = 15
    BUS_VOLTAGE_RANGE_MASK = 0x2000
    GAIN_MASK = 0x1800
    BUS_ADC_MASK = 0x0780
    SHUNT_ADC_MASK = 0x0078
    MODE_MASK = 0x0007
    
    # Default calibration values
    R_SHUNT = 0.1  # Shunt resistor value in ohms (100mΩ)
    V_BUS_MAX = 32  # Maximum bus voltage (32V)
    V_SHUNT_MAX = 0.32  # Maximum shunt voltage (320mV)
    I_MAX_EXPECTED = 2.0  # Maximum expected current (2A)
    
    def __init__(self, i2c_addr: int = DEFAULT_ADDRESS, bus: int = 1):
        """
        Initialize INA219 monitor.
        
        Args:
            i2c_addr: I2C address (default 0x40)
            bus: I2C bus number (default 1)
        """
        self.i2c_addr = i2c_addr
        self.bus = bus
        self._i2c = smbus2.SMBus(bus)
        self._calibration_value = self._calculate_calibration()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._interval_ms = 1000
        self._overcurrent_callback: Optional[Callable[[], None]] = None
        self._overcurrent_threshold = float('inf')
        self._data_buffer: List[Dict] = []
        self._csv_path: Optional[str] = None
        self._csv_file = None
        self._csv_writer = None
        
        # Statistics
        self._stats = {
            'samples': 0,
            'current_min': float('inf'),
            'current_max': 0,
            'current_avg': 0,
            'voltage_min': float('inf'),
            'voltage_max': 0,
            'voltage_avg': 0,
            'power_min': float('inf'),
            'power_max': 0,
            'power_avg': 0,
            'overcurrent_events': 0,
            'start_time': None,
            'end_time': None
        }
        
        self._configure()
    
    def _calculate_calibration(self) -> int:
        """Calculate calibration value for INA219."""
        # Formula: Cal = 0.04096 / (Current_LSB * R_Shunt)
        # Where Current_LSB = Max_Expected_Current / 2^15
        current_lsb = self.I_MAX_EXPECTED / 32768
        cal = int(0.04096 / (current_lsb * self.R_SHUNT))
        return cal
    
    def _configure(self):
        """Configure INA219 with calculated calibration."""
        # Write calibration value
        self._i2c.write_word_data(self.i2c_addr, self.REG_CALIBRATION, self._calibration_value)
        
        # Configure: 32V range, gain 1/8, 12-bit ADC, continuous mode
        config = 0x399F  # 0b0011100110011111
        self._i2c.write_word_data(self.i2c_addr, self.REG_CONFIG, config)
    
    def _read_register(self, reg: int) -> int:
        """Read a 16-bit register from INA219."""
        data = self._i2c.read_word_data(self.i2c_addr, reg)
        # Swap bytes (INA219 is big-endian)
        return ((data & 0xFF) << 8) | ((data >> 8) & 0xFF)
    
    def read_current(self) -> float:
        """
        Read current in milliamperes (mA).
        
        Returns:
            Current in mA
        """
        raw_current = self._read_register(self.REG_CURRENT)
        
        # Convert to signed 16-bit
        if raw_current > 32767:
            raw_current -= 65536
        
        # Current_LSB = Max_Expected_Current / 2^15
        current_lsb = self.I_MAX_EXPECTED / 32768
        
        # Current = Raw * Current_LSB
        current_ma = raw_current * current_lsb * 1000  # Convert to mA
        return round(current_ma, 2)
    
    def read_voltage(self) -> float:
        """
        Read bus voltage in volts (V).
        
        Returns:
            Voltage in V
        """
        raw_voltage = self._read_register(self.REG_BUS_VOLTAGE)
        
        # Extract voltage value (bits 3-15)
        voltage_register = (raw_voltage >> 3) & 0xFFF
        
        # LSB = 4mV
        voltage_v = voltage_register * 0.004
        
        # Check if overflow occurred
        overflow = (raw_voltage >> 1) & 0x01
        
        return round(voltage_v, 3)
    
    def read_power(self) -> float:
        """
        Read power in milliwatts (mW).
        
        Returns:
            Power in mW
        """
        raw_power = self._read_register(self.REG_POWER)
        
        # Power_LSB = 20 * Current_LSB
        current_lsb = self.I_MAX_EXPECTED / 32768
        power_lsb = 20 * current_lsb
        
        # Power = Raw * Power_LSB
        power_mw = raw_power * power_lsb * 1000  # Convert to mW
        
        return round(power_mw, 2)
    
    def is_overcurrent(self) -> bool:
        """
        Check if current exceeds overcurrent threshold.
        
        Returns:
            True if overcurrent detected
        """
        current = self.read_current()
        return current > self._overcurrent_threshold
    
    def set_overcurrent_threshold(self, threshold_ma: float, callback: Optional[Callable[[], None]] = None):
        """
        Set overcurrent threshold and optional callback.
        
        Args:
            threshold_ma: Current threshold in mA
            callback: Function to call when overcurrent detected
        """
        self._overcurrent_threshold = threshold_ma
        self._overcurrent_callback = callback
    
    def start_monitoring(self, interval_ms: int = 1000, csv_path: Optional[str] = None):
        """
        Start real-time monitoring in a background thread.
        
        Args:
            interval_ms: Sampling interval in milliseconds
            csv_path: Optional path for CSV logging
        """
        if self._monitoring:
            return
        
        self._interval_ms = interval_ms
        self._monitoring = True
        self._stats['start_time'] = datetime.now()
        self._data_buffer = []
        
        # Setup CSV logging
        if csv_path:
            self._csv_path = csv_path
            self._csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(['timestamp', 'current_ma', 'voltage_v', 'power_mw'])
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_loop(self):
        """Internal monitoring loop."""
        interval_sec = self._interval_ms / 1000.0
        
        while self._monitoring:
            timestamp = datetime.now()
            current = self.read_current()
            voltage = self.read_voltage()
            power = self.read_power()
            
            # Update statistics
            self._update_stats(current, voltage, power)
            
            # Log to CSV
            if self._csv_writer:
                self._csv_writer.writerow([
                    timestamp.isoformat(),
                    f'{current:.2f}',
                    f'{voltage:.3f}',
                    f'{power:.2f}'
                ])
                self._csv_file.flush()
            
            # Check overcurrent
            if current > self._overcurrent_threshold:
                self._stats['overcurrent_events'] += 1
                if self._overcurrent_callback:
                    self._overcurrent_callback()
            
            # Store in buffer (keep last 1000 samples)
            self._data_buffer.append({
                'timestamp': timestamp,
                'current': current,
                'voltage': voltage,
                'power': power
            })
            if len(self._data_buffer) > 1000:
                self._data_buffer.pop(0)
            
            time.sleep(interval_sec)
    
    def _update_stats(self, current: float, voltage: float, power: float):
        """Update running statistics."""
        stats = self._stats
        stats['samples'] += 1
        stats['current_min'] = min(stats['current_min'], current)
        stats['current_max'] = max(stats['current_max'], current)
        stats['current_avg'] = ((stats['current_avg'] * (stats['samples'] - 1)) + current) / stats['samples']
        
        stats['voltage_min'] = min(stats['voltage_min'], voltage)
        stats['voltage_max'] = max(stats['voltage_max'], voltage)
        stats['voltage_avg'] = ((stats['voltage_avg'] * (stats['samples'] - 1)) + voltage) / stats['samples']
        
        stats['power_min'] = min(stats['power_min'], power)
        stats['power_max'] = max(stats['power_max'], power)
        stats['power_avg'] = ((stats['power_avg'] * (stats['samples'] - 1)) + power) / stats['samples']
    
    def stop_monitoring(self):
        """Stop monitoring and close CSV file."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        self._stats['end_time'] = datetime.now()
        
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None
    
    def get_stats(self) -> Dict:
        """
        Get monitoring statistics.
        
        Returns:
            Dictionary containing all statistics
        """
        return {
            'samples': self._stats['samples'],
            'current': {
                'min_ma': round(self._stats['current_min'], 2) if self._stats['current_min'] != float('inf') else 0,
                'max_ma': round(self._stats['current_max'], 2),
                'avg_ma': round(self._stats['current_avg'], 2)
            },
            'voltage': {
                'min_v': round(self._stats['voltage_min'], 3) if self._stats['voltage_min'] != float('inf') else 0,
                'max_v': round(self._stats['voltage_max'], 3),
                'avg_v': round(self._stats['voltage_avg'], 3)
            },
            'power': {
                'min_mw': round(self._stats['power_min'], 2) if self._stats['power_min'] != float('inf') else 0,
                'max_mw': round(self._stats['power_max'], 2),
                'avg_mw': round(self._stats['power_avg'], 2)
            },
            'overcurrent_events': self._stats['overcurrent_events'],
            'start_time': self._stats['start_time'].isoformat() if self._stats['start_time'] else None,
            'end_time': self._stats['end_time'].isoformat() if self._stats['end_time'] else None,
            'duration_seconds': (
                (self._stats['end_time'] - self._stats['start_time']).total_seconds()
                if self._stats['end_time'] and self._stats['start_time'] else None
            )
        }
    
    def get_recent_data(self, count: int = 10) -> List[Dict]:
        """
        Get recent data samples.
        
        Args:
            count: Number of recent samples to return
            
        Returns:
            List of recent data dictionaries
        """
        return self._data_buffer[-count:]
    
    def reset_stats(self):
        """Reset all statistics."""
        self._stats = {
            'samples': 0,
            'current_min': float('inf'),
            'current_max': 0,
            'current_avg': 0,
            'voltage_min': float('inf'),
            'voltage_max': 0,
            'voltage_avg': 0,
            'power_min': float('inf'),
            'power_max': 0,
            'power_avg': 0,
            'overcurrent_events': 0,
            'start_time': None,
            'end_time': None
        }
        self._data_buffer = []
    
    def close(self):
        """Close I2C bus and monitoring."""
        self.stop_monitoring()
        self._i2c.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def overcurrent_handler():
    """Example overcurrent protection callback."""
    print("⚠️  OVERCURRENT DETECTED! Shutting down system...")
    # Add your protection logic here (e.g., GPIO relay control)


# Usage Example
if __name__ == "__main__":
    print("=" * 60)
    print("INA219 Current Monitor - Usage Example")
    print("=" * 60)
    
    # Create monitor instance
    monitor = INA219Monitor(i2c_addr=0x40, bus=1)
    
    # Set overcurrent protection (e.g., 1.5A threshold)
    monitor.set_overcurrent_threshold(1500.0, callback=overcurrent_handler)
    
    print("\n📊 Single Readings:")
    print(f"   Current: {monitor.read_current():.2f} mA")
    print(f"   Voltage: {monitor.read_voltage():.3f} V")
    print(f"   Power:   {monitor.read_power():.2f} mW")
    
    print("\n📈 Starting Real-time Monitoring...")
    print("   (Press Ctrl+C to stop)")
    print("-" * 60)
    
    # Start monitoring with CSV logging
    csv_path = "ina219_readings.csv"
    monitor.start_monitoring(interval_ms=500, csv_path=csv_path)
    
    try:
        while True:
            # Display real-time values
            current = monitor.read_current()
            voltage = monitor.read_voltage()
            power = monitor.read_power()
            
            # Status indicator
            status = "⚠️ OVERCURRENT!" if current > 1500 else "✓ OK"
            
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Current: {current:7.2f} mA | "
                  f"Voltage: {voltage:5.3f} V | "
                  f"Power: {power:8.2f} mW | "
                  f"{status}", end="", flush=True)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        print("\n📊 Final Statistics:")
        print("=" * 60)
        
        stats = monitor.get_stats()
        
        print(f"   Total Samples:        {stats['samples']}")
        print(f"\n   Current (mA):")
        print(f"      Min:   {stats['current']['min_ma']:.2f}")
        print(f"      Max:   {stats['current']['max_ma']:.2f}")
        print(f"      Avg:   {stats['current']['avg_ma']:.2f}")
        print(f"\n   Voltage (V):")
        print(f"      Min:   {stats['voltage']['min_v']:.3f}")
        print(f"      Max:   {stats['voltage']['max_v']:.3f}")
        print(f"      Avg:   {stats['voltage']['avg_v']:.3f}")
        print(f"\n   Power (mW):")
        print(f"      Min:   {stats['power']['min_mw']:.2f}")
        print(f"      Max:   {stats['power']['max_mw']:.2f}")
        print(f"      Avg:   {stats['power']['avg_mw']:.2f}")
        print(f"\n   Overcurrent Events:  {stats['overcurrent_events']}")
        print(f"   Duration:             {stats['duration_seconds']:.1f} seconds")
        
        if csv_path and os.path.exists(csv_path):
            print(f"\n📁 Data logged to: {csv_path}")
        
        # Clean up
        monitor.close()
        print("\n✅ Monitoring stopped.")
