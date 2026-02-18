"""
ESP32 OTA Wireless Update Module

This module provides OTA (Over-The-Air) firmware update capabilities for ESP32
via WiFi with MQTT status reporting, version management, and rollback support.
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Try to import required libraries, provide fallbacks if not available
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    import requests
except ImportError:
    requests = None

try:
    import wifi
except ImportError:
    wifi = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UpdateState(Enum):
    """OTA update state enumeration."""
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    UPDATING = "updating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class FirmwareInfo:
    """Firmware metadata container."""
    version: str
    url: str
    checksum: str
    size: int
    description: str = ""
    release_date: str = ""
    hardware_compatible: list = field(default_factory=list)


@dataclass
class UpdateStatus:
    """Current OTA update status."""
    state: UpdateState = UpdateState.IDLE
    progress: float = 0.0
    current_version: str = ""
    available_version: str = ""
    bytes_downloaded: int = 0
    total_bytes: int = 0
    error_message: str = ""
    rollback_available: bool = False


# MQTT Topics Definition
class MQTTTopics:
    """MQTT topic templates for OTA updates."""
    
    # Base topic namespace
    BASE = "esp32/ota"
    
    # Status reporting topics
    STATUS = f"{BASE}/status"           # Current device status
    PROGRESS = f"{BASE}/progress"        # Update progress (0-100)
    VERSION = f"{BASE}/version"          # Current firmware version
    UPDATE_AVAILABLE = f"{BASE}/update/available"  # New version available
    UPDATE_RESULT = f"{BASE}/update/result"        # Update success/failure
    
    # Command topics (subscribe to these)
    COMMAND = f"{BASE}/command"          # General commands
    CHECK_UPDATE = f"{BASE}/command/check"         # Trigger update check
    START_UPDATE = f"{BASE}/command/update"        # Start update with URL
    CANCEL_UPDATE = f"{BASE}/command/cancel"       # Cancel ongoing update
    ROLLBACK = f"{BASE}/command/rollback"           # Trigger rollback
    
    # Firmware distribution topics
    FIRMWARE_LIST = f"{BASE}/firmware/list"         # Available firmware versions
    FIRMWARE_METADATA = f"{BASE}/firmware/{{version}}/meta"  # Per-version metadata
    
    @classmethod
    def get_command_topic(cls, command: str) -> str:
        """Get specific command topic."""
        return f"{cls.COMMAND}/{command}"
    
    @classmethod
    def get_firmware_metadata_topic(cls, version: str) -> str:
        """Get firmware metadata topic for specific version."""
        return cls.FIRMWARE_METADATA.format(version=version)


class OTAUpdater:
    """
    ESP32 OTA Wireless Update Module
    
    Provides WiFi-based firmware updates for ESP32 with MQTT status reporting,
    version management, rollback capability, and progress callbacks.
    
    Example:
        >>> updater = OTAUpdater(
        ...     mqtt_broker="mqtt://192.168.1.100",
        ...     wifi_ssid="MyNetwork",
        ...     wifi_password="password123"
        ... )
        >>> updater.on_progress(lambda p: print(f"Progress: {p}%"))
        >>> updater.on_complete(lambda v: print(f"Updated to {v}"))
        >>> updater.connect_wifi()
        >>> updater.start_update("http://server/firmware/v2.0.0.bin")
    """
    
    # Default MQTT topics
    TOPICS = MQTTTopics
    
    def __init__(
        self,
        mqtt_broker: str,
        wifi_ssid: str,
        wifi_password: str,
        device_id: str = "esp32_default",
        current_version: str = "1.0.0",
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        firmware_dir: str = "./firmware"
    ):
        """
        Initialize OTA Updater.
        
        Args:
            mqtt_broker: MQTT broker URL or IP address
            wifi_ssid: WiFi network SSID
            wifi_password: WiFi network password
            device_id: Unique identifier for this device
            current_version: Current firmware version string
            mqtt_port: MQTT broker port (default: 1883)
            mqtt_username: Optional MQTT username
            mqtt_password: Optional MQTT password
            firmware_dir: Local directory for firmware storage
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.device_id = device_id
        self.current_version = current_version
        self.firmware_dir = Path(firmware_dir)
        self.firmware_dir.mkdir(parents=True, exist_ok=True)
        
        # MQTT client
        self._mqtt_client: Optional[Any] = None
        self._mqtt_connected = False
        
        # Callbacks
        self._progress_callback: Optional[Callable[[float], None]] = None
        self._complete_callback: Optional[Callable[[str], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        self._rollback_handler: Optional[Callable[[], bool]] = None
        
        # Update state
        self._status = UpdateStatus(
            state=UpdateState.IDLE,
            current_version=current_version,
            rollback_available=False
        )
        
        # Version tracking
        self._available_version: str = ""
        self._firmware_cache: Dict[str, FirmwareInfo] = {}
        self._backup_version: str = ""
        
        # Update control
        self._update_cancelled = False
        self._update_in_progress = False
        
        logger.info(f"OTAUpdater initialized for device {device_id}")
    
    # ==================== WiFi Connection ====================
    
    def connect_wifi(self) -> bool:
        """
        Connect to WiFi network.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        logger.info(f"Connecting to WiFi: {self.wifi_ssid}")
        
        if wifi is None:
            # Simulate WiFi connection for testing
            logger.warning("WiFi library not available, simulating connection")
            self._simulate_wifi_connection()
            return True
        
        try:
            # Attempt WiFi connection
            # This is a simplified version - actual implementation
            # would use network.WLAN or similar
            wlan = wifi.WLAN(wifi.STA_IF)
            wlan.active(True)
            wlan.connect(self.wifi_ssid, self.wifi_password)
            
            # Wait for connection
            max_attempts = 30
            for _ in range(max_attempts):
                if wlan.isconnected():
                    logger.info(f"WiFi connected: {wlan.ifconfig()}")
                    self._publish_status()
                    return True
                time.sleep(1)
            
            logger.error("WiFi connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"WiFi connection failed: {e}")
            self._on_error(f"WiFi connection failed: {e}")
            return False
    
    def _simulate_wifi_connection(self):
        """Simulate WiFi connection for testing purposes."""
        self._status.state = UpdateState.IDLE
        logger.info("WiFi connection simulated")
    
    def disconnect_wifi(self):
        """Disconnect from WiFi network."""
        if wifi is not None:
            try:
                wlan = wifi.WLAN(wifi.STA_IF)
                wlan.disconnect()
                wlan.active(False)
                logger.info("WiFi disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting WiFi: {e}")
    
    def is_wifi_connected(self) -> bool:
        """Check if WiFi is connected."""
        if wifi is None:
            return True  # Simulated
        try:
            wlan = wifi.WLAN(wifi.STA_IF)
            return wlan.isconnected()
        except:
            return False
    
    # ==================== MQTT Connection ====================
    
    def _setup_mqtt(self):
        """Setup MQTT client and callbacks."""
        if mqtt is None:
            logger.warning("paho-mqtt not available, MQTT disabled")
            return
        
        self._mqtt_client = mqtt.Client(client_id=f"ota_{self.device_id}")
        
        if self.mqtt_username and self.mqtt_password:
            self._mqtt_client.username_pw_set(
                self.mqtt_username, 
                self.mqtt_password
            )
        
        # Callbacks
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self._mqtt_client.on_message = self._on_mqtt_message
        self._mqtt_client.on_publish = self._on_mqtt_publish
    
    def connect_mqtt(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            bool: True if connection successful
        """
        if mqtt is None:
            logger.warning("MQTT library not available")
            return False
        
        self._setup_mqtt()
        
        try:
            logger.info(f"Connecting to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
            self._mqtt_client.connect(
                self.mqtt_broker, 
                self.mqtt_port, 
                keepalive=60
            )
            self._mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect_mqtt(self):
        """Disconnect from MQTT broker."""
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
                logger.info("MQTT disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting MQTT: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            logger.info("MQTT connected")
            self._mqtt_connected = True
            self._publish_status()
            self._subscribe_topics()
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self._mqtt_connected = False
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        logger.warning(f"MQTT disconnected (rc: {rc})")
        self._mqtt_connected = False
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"MQTT message on {topic}: {payload}")
            
            # Handle command topics
            if topic == self.TOPICS.CHECK_UPDATE:
                self.check_version()
            elif topic == self.TOPICS.START_UPDATE:
                self._handle_start_update_command(payload)
            elif topic == self.TOPICS.CANCEL_UPDATE:
                self.cancel_update()
            elif topic == self.TOPICS.ROLLBACK:
                self.rollback()
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
    def _on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback."""
        logger.debug(f"Message {mid} published")
    
    def _subscribe_topics(self):
        """Subscribe to command topics."""
        if not self._mqtt_client or not self._mqtt_connected:
            return
        
        topics = [
            (self.TOPICS.CHECK_UPDATE, 0),
            (self.TOPICS.START_UPDATE, 0),
            (self.TOPICS.CANCEL_UPDATE, 0),
            (self.TOPICS.ROLLBACK, 0),
        ]
        
        try:
            self._mqtt_client.subscribe(topics)
            logger.info("Subscribed to command topics")
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {e}")
    
    # ==================== MQTT Publishing ====================
    
    def _publish(self, topic: str, payload: str, qos: int = 0):
        """Publish message to MQTT topic."""
        if self._mqtt_client and self._mqtt_connected:
            try:
                self._mqtt_client.publish(topic, payload, qos)
            except Exception as e:
                logger.error(f"Failed to publish to {topic}: {e}")
    
    def _publish_status(self):
        """Publish current status to MQTT."""
        status = {
            "device_id": self.device_id,
            "state": self._status.state.value,
            "current_version": self.current_version,
            "available_version": self._available_version,
            "progress": self._status.progress,
            "rollback_available": self._status.rollback_available
        }
        self._publish(self.TOPICS.STATUS, json.dumps(status))
    
    def _publish_progress(self, progress: float):
        """Publish update progress."""
        self._publish(
            self.TOPICS.PROGRESS, 
            json.dumps({
                "device_id": self.device_id,
                "progress": progress,
                "bytes_downloaded": self._status.bytes_downloaded,
                "total_bytes": self._status.total_bytes
            })
        )
    
    def _publish_version(self):
        """Publish current version."""
        self._publish(
            self.TOPICS.VERSION,
            json.dumps({
                "device_id": self.device_id,
                "version": self.current_version
            })
        )
    
    def _publish_update_available(self, version: str, info: FirmwareInfo):
        """Publish update available notification."""
        self._publish(
            self.TOPICS.UPDATE_AVAILABLE,
            json.dumps({
                "device_id": self.device_id,
                "version": version,
                "size": info.size,
                "checksum": info.checksum,
                "description": info.description
            })
        )
    
    def _publish_update_result(self, success: bool, message: str):
        """Publish update result."""
        self._publish(
            self.TOPICS.UPDATE_RESULT,
            json.dumps({
                "device_id": self.device_id,
                "success": success,
                "message": message,
                "version": self.current_version
            })
        )
    
    # ==================== Firmware Management ====================
    
    def publish_firmware(self, firmware_path: str) -> bool:
        """
        Publish firmware file to MQTT topic for distribution.
        
        Args:
            firmware_path: Path to firmware binary file
            
        Returns:
            bool: True if successful
        """
        path = Path(firmware_path)
        if not path.exists():
            logger.error(f"Firmware file not found: {firmware_path}")
            return False
        
        try:
            # Read firmware file
            with open(path, 'rb') as f:
                firmware_data = f.read()
            
            # Calculate checksum
            checksum = hashlib.sha256(firmware_data).hexdigest()
            size = len(firmware_data)
            
            # Extract version from filename or use placeholder
            version = path.stem.replace('firmware_', '').replace('esp32_', '')
            
            # Publish metadata
            metadata = {
                "version": version,
                "size": size,
                "checksum": checksum,
                "filename": path.name,
                "url": f"firmware/{path.name}"  # Would be actual URL in production
            }
            self._publish(
                self.TOPICS.get_firmware_metadata_topic(version),
                json.dumps(metadata)
            )
            
            # Publish firmware list update
            self._update_firmware_list(version, metadata)
            
            logger.info(f"Firmware published: {version} ({size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish firmware: {e}")
            return False
    
    def _update_firmware_list(self, version: str, metadata: dict):
        """Update the list of available firmware versions."""
        # In production, this would be stored on server
        # For now, just publish the update
        self._publish(
            self.TOPICS.FIRMWARE_LIST,
            json.dumps({
                "latest_version": version,
                "versions": [version]
            })
        )
    
    # ==================== Update Commands ====================
    
    def subscribe_update_command(self, topic: str):
        """
        Subscribe to a custom update command topic.
        
        Args:
            topic: MQTT topic to subscribe to
        """
        if self._mqtt_client and self._mqtt_connected:
            self._mqtt_client.subscribe(topic, 0)
            logger.info(f"Subscribed to custom update topic: {topic}")
    
    def _handle_start_update_command(self, payload: str):
        """Handle incoming start update command."""
        try:
            data = json.loads(payload)
            firmware_url = data.get("url")
            version = data.get("version", "unknown")
            
            if firmware_url:
                logger.info(f"Starting update from command: {version}")
                self.start_update(firmware_url)
            else:
                logger.error("No firmware URL in update command")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in update command")
    
    # ==================== Version Management ====================
    
    def check_version(self) -> str:
        """
        Check for available firmware updates.
        
        Returns:
            str: Available firmware version or empty string if none
        """
        logger.info("Checking for firmware updates...")
        self._status.state = UpdateState.CHECKING
        self._publish_status()
        
        # In production, this would query a server
        # For now, simulate version check
        try:
            # Try to get version from MQTT firmware list
            # This is a simplified version
            self._available_version = self._simulate_version_check()
            
            if self._available_version > self.current_version:
                logger.info(f"Update available: {self._available_version}")
                self._status.available_version = self._available_version
                self._publish_status()
                
                # Publish update available
                info = FirmwareInfo(
                    version=self._available_version,
                    url="",
                    checksum="",
                    size=0
                )
                self._publish_update_available(self._available_version, info)
                
                return self._available_version
            else:
                logger.info("No updates available")
                return ""
                
        except Exception as e:
            logger.error(f"Version check failed: {e}")
            self._on_error(f"Version check failed: {e}")
            return ""
    
    def _simulate_version_check(self) -> str:
        """Simulate version check for testing."""
        # In real implementation, query server
        return "1.0.0"  # Placeholder
    
    def update_available(self) -> bool:
        """
        Check if firmware update is available.
        
        Returns:
            bool: True if update is available
        """
        available = self.check_version()
        return bool(available and available > self.current_version)
    
    def get_current_version(self) -> str:
        """Get current firmware version."""
        return self.current_version
    
    # ==================== Update Process ====================
    
    def start_update(self, firmware_url: str) -> bool:
        """
        Start firmware update process.
        
        Args:
            firmware_url: URL to download firmware from
            
        Returns:
            bool: True if update started successfully
        """
        if self._update_in_progress:
            logger.warning("Update already in progress")
            return False
        
        logger.info(f"Starting firmware update from: {firmware_url}")
        self._update_in_progress = True
        self._update_cancelled = False
        self._status.state = UpdateState.DOWNLOADING
        self._status.progress = 0.0
        self._status.error_message = ""
        self._publish_status()
        
        try:
            # Create backup of current firmware
            self._create_backup()
            
            # Download firmware
            success = self._download_firmware(firmware_url)
            
            if not success:
                raise Exception("Firmware download failed")
            
            # Verify firmware
            self._status.state = UpdateState.VERIFYING
            self._publish_status()
            
            if not self._verify_firmware():
                raise Exception("Firmware verification failed")
            
            # Apply firmware update
            self._status.state = UpdateState.UPDATING
            self._publish_status()
            
            success = self._apply_firmware()
            
            if success:
                self._status.state = UpdateState.COMPLETED
                self._status.progress = 100.0
                self._status.rollback_available = True
                self._publish_update_result(True, "Update completed successfully")
                self._on_complete(self.current_version)
            else:
                raise Exception("Firmware application failed")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self._status.state = UpdateState.FAILED
            self._status.error_message = str(e)
            self._publish_update_result(False, str(e))
            self._on_error(str(e))
            
            # Attempt rollback
            if self._rollback_handler or self._backup_version:
                logger.info("Attempting automatic rollback...")
                self.rollback()
            
            return False
        
        finally:
            self._update_in_progress = False
            self._publish_status()
        
        return True
    
    def _download_firmware(self, url: str) -> bool:
        """Download firmware from URL."""
        if requests is None:
            return self._simulate_download(url)
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            self._status.total_bytes = total_size
            
            firmware_file = self.firmware_dir / "update.bin"
            downloaded = 0
            
            with open(firmware_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._update_cancelled:
                        logger.info("Download cancelled")
                        return False
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._status.bytes_downloaded = downloaded
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        self._status.progress = progress
                        self._publish_progress(progress)
                        self._on_progress(progress)
            
            logger.info(f"Firmware downloaded: {downloaded} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def _simulate_download(self, url: str) -> bool:
        """Simulate firmware download for testing."""
        logger.info(f"Simulating download from: {url}")
        
        for i in range(0, 101, 10):
            if self._update_cancelled:
                return False
            
            self._status.progress = float(i)
            self._on_progress(float(i))
            time.sleep(0.1)
        
        # Create dummy firmware file
        firmware_file = self.firmware_dir / "update.bin"
        firmware_file.write_bytes(b"DUMMY_FIRMWARE_CONTENT")
        
        return True
    
    def _verify_firmware(self) -> bool:
        """Verify downloaded firmware integrity."""
        firmware_file = self.firmware_dir / "update.bin"
        
        if not firmware_file.exists():
            return False
        
        # In production, verify checksum
        # For now, just check file exists and has content
        return firmware_file.stat().st_size > 0
    
    def _apply_firmware(self) -> bool:
        """Apply firmware update to ESP32."""
        # In production, this would use esptool or similar
        # to flash the firmware to ESP32
        logger.info("Applying firmware update to ESP32...")
        
        # Simulate flashing process
        for i in range(0, 101, 20):
            if self._update_cancelled:
                return False
            self._on_progress(i)
            time.sleep(0.1)
        
        # Update version (in production, this would come from firmware)
        self.current_version = self._status.available_version or "1.0.0"
        logger.info(f"Firmware applied. New version: {self.current_version}")
        
        return True
    
    def cancel_update(self):
        """Cancel ongoing update."""
        if self._update_in_progress:
            logger.info("Cancelling update...")
            self._update_cancelled = True
            self._status.state = UpdateState.IDLE
            self._publish_status()
    
    # ==================== Rollback ====================
    
    def _create_backup(self):
        """Create backup of current firmware."""
        self._backup_version = self.current_version
        self._status.rollback_available = True
        logger.info(f"Created backup of version {self._backup_version}")
    
    def set_rollback_handler(self, handler: Callable[[], bool]):
        """
        Set custom rollback handler function.
        
        Args:
            handler: Callback function that performs rollback and returns success
        """
        self._rollback_handler = handler
        logger.info("Custom rollback handler set")
    
    def rollback(self) -> bool:
        """
        Rollback to previous firmware version.
        
        Returns:
            bool: True if rollback successful
        """
        logger.info("Starting rollback...")
        self._status.state = UpdateState.ROLLING_BACK
        self._publish_status()
        
        try:
            # Try custom rollback handler first
            if self._rollback_handler:
                success = self._rollback_handler()
                if success:
                    self._complete_rollback()
                    return True
            
            # Default rollback behavior
            if not self._backup_version:
                logger.error("No backup version available")
                return False
            
            # In production, flash backup firmware
            logger.info(f"Rolling back to version: {self._backup_version}")
            self.current_version = self._backup_version
            
            self._complete_rollback()
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            self._status.state = UpdateState.FAILED
            self._on_error(f"Rollback failed: {e}")
            return False
    
    def _complete_rollback(self):
        """Complete rollback process."""
        self._status.state = UpdateState.ROLLED_BACK
        self._publish_update_result(True, "Rollback completed")
        self._on_complete(self.current_version)
        self._publish_status()
        logger.info("Rollback completed successfully")
    
    # ==================== Status ====================
    
    def get_status(self) -> dict:
        """
        Get current OTA update status.
        
        Returns:
            dict: Status information
        """
        return {
            "state": self._status.state.value,
            "progress": self._status.progress,
            "current_version": self.current_version,
            "available_version": self._status.available_version,
            "bytes_downloaded": self._status.bytes_downloaded,
            "total_bytes": self._status.total_bytes,
            "error_message": self._status.error_message,
            "rollback_available": self._status.rollback_available,
            "update_in_progress": self._update_in_progress
        }
    
    # ==================== Callbacks ====================
    
    def on_progress(self, callback: Callable[[float], None]):
        """
        Set progress callback.
        
        Args:
            callback: Function called with progress percentage (0-100)
        """
        self._progress_callback = callback
        logger.info("Progress callback set")
    
    def on_complete(self, callback: Callable[[str], None]):
        """
        Set completion callback.
        
        Args:
            callback: Function called with new version string when update completes
        """
        self._complete_callback = callback
        logger.info("Complete callback set")
    
    def on_error(self, callback: Callable[[str], None]):
        """
        Set error callback.
        
        Args:
            callback: Function called with error message on failure
        """
        self._error_callback = callback
        logger.info("Error callback set")
    
    def _on_progress(self, progress: float):
        """Internal progress handler."""
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _on_complete(self, version: str):
        """Internal completion handler."""
        if self._complete_callback:
            try:
                self._complete_callback(version)
            except Exception as e:
                logger.error(f"Complete callback error: {e}")
    
    def _on_error(self, message: str):
        """Internal error handler."""
        if self._error_callback:
            try:
                self._error_callback(message)
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    # ==================== Cleanup ====================
    
    def cleanup(self):
        """Cleanup resources."""
        self.disconnect_mqtt()
        self.disconnect_wifi()
        logger.info("OTAUpdater cleanup complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# ==================== Usage Example ====================

def example_usage():
    """Example usage of OTAUpdater."""
    
    # Create updater instance
    updater = OTAUpdater(
        mqtt_broker="192.168.1.100",
        wifi_ssid="MyWiFiNetwork",
        wifi_password="MyWiFiPassword",
        device_id="esp32_sensor_01",
        current_version="1.0.0"
    )
    
    # Set up callbacks
    updater.on_progress(lambda p: print(f"📥 Progress: {p:.1f}%"))
    updater.on_complete(lambda v: print(f"✅ Updated to version: {v}"))
    updater.on_error(lambda e: print(f"❌ Error: {e}"))
    
    # Connect to WiFi
    if updater.connect_wifi():
        print("✅ WiFi connected")
    else:
        print("❌ WiFi connection failed")
        return
    
    # Connect to MQTT (optional)
    if updater.connect_mqtt():
        print("✅ MQTT connected")
    
    # Check for updates
    print("\n--- Checking for updates ---")
    available = updater.check_version()
    if available:
        print(f"📦 Update available: {available}")
    else:
        print("📦 No updates available")
    
    # Get status
    print("\n--- Current Status ---")
    status = updater.get_status()
    print(json.dumps(status, indent=2))
    
    # Start update (example URL)
    # updater.start_update("http://192.168.1.50/firmware/esp32_v2.0.0.bin")
    
    # Publish firmware to MQTT
    # updater.publish_firmware("./firmware/esp32_v1.0.1.bin")
    
    # Cleanup
    updater.cleanup()
    print("\n👋 Done!")


def example_mqtt_topics():
    """Print MQTT topics definition."""
    print("=== MQTT Topics ===")
    print(f"Base:              {MQTTTopics.BASE}")
    print(f"Status:            {MQTTTopics.STATUS}")
    print(f"Progress:          {MQTTTopics.PROGRESS}")
    print(f"Version:           {MQTTTopics.VERSION}")
    print(f"Update Available:  {MQTTTopics.UPDATE_AVAILABLE}")
    print(f"Update Result:     {MQTTTopics.UPDATE_RESULT}")
    print(f"Check Update:      {MQTTTopics.CHECK_UPDATE}")
    print(f"Start Update:      {MQTTTopics.START_UPDATE}")
    print(f"Cancel Update:     {MQTTTopics.CANCEL_UPDATE}")
    print(f"Rollback:          {MQTTTopics.ROLLBACK}")


if __name__ == "__main__":
    # Print topics
    example_mqtt_topics()
    
    print("\n" + "="*50 + "\n")
    
    # Run example (commented out to avoid actual connections)
    # example_usage()
    
    print("Run example_usage() to test (requires MQTT/WiFi)")
