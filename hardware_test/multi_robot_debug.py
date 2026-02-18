"""
Multi-Robot Debug Module for Physical AGI Hardware Testing

This module provides centralized control, monitoring, and analysis for multi-robot systems
using MQTT for communication.
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import paho.mqtt.client as mqtt


class RobotStatus(Enum):
    """Robot status enumeration."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    BUSY = "busy"


class HealthLevel(Enum):
    """Health level enumeration."""
    CRITICAL = "critical"
    WARNING = "warning"
    HEALTHY = "healthy"


@dataclass
class RobotInfo:
    """Robot information container."""
    id: str
    port: int
    status: RobotStatus = RobotStatus.UNKNOWN
    health: HealthLevel = HealthLevel.HEALTHY
    last_heartbeat: float = 0.0
    battery_level: float = 100.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    position: Dict[str, float] = field(default_factory=dict)
    task_queue: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['health'] = self.health.value
        return data


# MQTT Topic Definitions
class MQTTTopics:
    """MQTT topic definitions for multi-robot communication."""
    
    # Base topic for all robot communications
    BASE_TOPIC = "physical_agi/robots"
    
    # Individual robot topics
    ROBOT_STATUS = f"{BASE_TOPIC}/{{robot_id}}/status"
    ROBOT_HEALTH = f"{BASE_TOPIC}/{{robot_id}}/health"
    ROBOT_COMMAND = f"{BASE_TOPIC}/{{robot_id}}/command"
    ROBOT_TELEMETRY = f"{BASE_TOPIC}/{{robot_id}}/telemetry"
    ROBOT_POSITION = f"{BASE_TOPIC}/{{robot_id}}/position"
    
    # Broadcast topics
    BROADCAST_COMMAND = f"{BASE_TOPIC}/broadcast/command"
    SYSTEM_STATUS = f"{BASE_TOPIC}/system/status"
    
    # Control topics
    SYSTEM_CONTROL = f"{BASE_TOPIC}/system/control"
    DISCOVERY = f"{BASE_TOPIC}/discovery"
    
    @classmethod
    def robot_status(cls, robot_id: str) -> str:
        return f"{cls.BASE_TOPIC}/{robot_id}/status"
    
    @classmethod
    def robot_health(cls, robot_id: str) -> str:
        return f"{cls.BASE_TOPIC}/{robot_id}/health"
    
    @classmethod
    def robot_command(cls, robot_id: str) -> str:
        return f"{cls.BASE_TOPIC}/{robot_id}/command"
    
    @classmethod
    def robot_telemetry(cls, robot_id: str) -> str:
        return f"{cls.BASE_TOPIC}/{robot_id}/telemetry"
    
    @classmethod
    def robot_position(cls, robot_id: str) -> str:
        return f"{cls.BASE_TOPIC}/{robot_id}/position"


class MultiRobotDebugger:
    """
    Centralized debugger for multi-robot systems.
    
    Provides:
    - Multi-robot status aggregation
    - Centralized command distribution
    - Health monitoring per robot
    - Collective behavior analysis
    """
    
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883, 
                 client_id: Optional[str] = None):
        """
        Initialize the multi-robot debugger.
        
        Args:
            mqtt_broker: MQTT broker address
            mqtt_port: MQTT broker port
            client_id: Optional client ID for MQTT connection
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.client_id = client_id or f"multi_robot_debugger_{uuid.uuid4().hex[:8]}"
        
        # Robot registry
        self.robots: Dict[str, RobotInfo] = {}
        
        # Command history
        self.command_history: List[Dict] = []
        
        # Behavior analysis cache
        self._behavior_cache: Dict = {}
        self._last_analysis_time: float = 0.0
        
        # Initialize MQTT client
        self._mqtt_client = mqtt.Client(client_id=self.client_id)
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        
        # Connection status
        self._connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self._connected = True
            print(f"[MultiRobotDebugger] Connected to MQTT broker at {self.mqtt_broker}")
            # Subscribe to all robot topics
            self._subscribe_all_topics()
        else:
            print(f"[MultiRobotDebugger] Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Extract robot ID from topic
            if "/robots/" in topic:
                parts = topic.split("/")
                if len(parts) >= 4:
                    robot_id = parts[2]
                    self._handle_robot_message(robot_id, topic, payload)
        except Exception as e:
            print(f"[MultiRobotDebugger] Error processing message: {e}")
    
    def _handle_robot_message(self, robot_id: str, topic: str, payload: dict):
        """Handle incoming robot messages."""
        if robot_id not in self.robots:
            return
            
        robot = self.robots[robot_id]
        robot.last_heartbeat = time.time()
        
        if "status" in topic:
            status_str = payload.get("status", "unknown")
            robot.status = RobotStatus(status_str)
        elif "health" in topic:
            health_str = payload.get("health", "healthy")
            robot.health = HealthLevel(health_str)
            robot.battery_level = payload.get("battery", 100.0)
            robot.cpu_usage = payload.get("cpu", 0.0)
            robot.memory_usage = payload.get("memory", 0.0)
        elif "telemetry" in topic:
            robot.battery_level = payload.get("battery", robot.battery_level)
            robot.cpu_usage = payload.get("cpu", robot.cpu_usage)
            robot.memory_usage = payload.get("memory", robot.memory_usage)
        elif "position" in topic:
            robot.position = {
                "x": payload.get("x", 0.0),
                "y": payload.get("y", 0.0),
                "z": payload.get("z", 0.0)
            }
    
    def _subscribe_all_topics(self):
        """Subscribe to all relevant MQTT topics."""
        topics = [
            (MQTTTopics.SYSTEM_STATUS, 0),
            (MQTTTopics.DISCOVERY, 0),
        ]
        
        # Add robot-specific topics
        for robot_id in self.robots:
            topics.append((MQTTTopics.robot_status(robot_id), 0))
            topics.append((MQTTTopics.robot_health(robot_id), 0))
            topics.append((MQTTTopics.robot_telemetry(robot_id), 0))
            topics.append((MQTTTopics.robot_position(robot_id), 0))
        
        if topics:
            self._mqtt_client.subscribe(topics)
    
    def connect(self) -> bool:
        """
        Connect to the MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self._mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"[MultiRobotDebugger] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MQTT broker."""
        self._mqtt_client.loop_stop()
        self._mqtt_client.disconnect()
        self._connected = False
    
    def add_robot(self, robot_id: str, port: int, metadata: Optional[Dict] = None) -> bool:
        """
        Add a robot to the system.
        
        Args:
            robot_id: Unique robot identifier
            port: Communication port for the robot
            metadata: Optional robot metadata
            
        Returns:
            True if robot added successfully, False if already exists
        """
        if robot_id in self.robots:
            print(f"[MultiRobotDebugger] Robot {robot_id} already exists")
            return False
        
        robot = RobotInfo(id=robot_id, port=port, metadata=metadata or {})
        self.robots[robot_id] = robot
        
        # Subscribe to this robot's topics
        if self._connected:
            topics = [
                (MQTTTopics.robot_status(robot_id), 0),
                (MQTTTopics.robot_health(robot_id), 0),
                (MQTTTopics.robot_telemetry(robot_id), 0),
                (MQTTTopics.robot_position(robot_id), 0),
            ]
            self._mqtt_client.subscribe(topics)
        
        print(f"[MultiRobotDebugger] Added robot {robot_id} on port {port}")
        return True
    
    def remove_robot(self, robot_id: str) -> bool:
        """
        Remove a robot from the system.
        
        Args:
            robot_id: Robot identifier to remove
            
        Returns:
            True if robot removed, False if not found
        """
        if robot_id not in self.robots:
            return False
        
        # Unsubscribe from robot topics
        if self._connected:
            topics = [
                MQTTTopics.robot_status(robot_id),
                MQTTTopics.robot_health(robot_id),
                MQTTTopics.robot_telemetry(robot_id),
                MQTTTopics.robot_position(robot_id),
            ]
            self._mqtt_client.unsubscribe(topics)
        
        del self.robots[robot_id]
        print(f"[MultiRobotDebugger] Removed robot {robot_id}")
        return True
    
    def get_robot(self, robot_id: str) -> Optional[dict]:
        """
        Get status and information for a specific robot.
        
        Args:
            robot_id: Robot identifier
            
        Returns:
            Robot information as dictionary, or None if not found
        """
        if robot_id not in self.robots:
            return None
        return self.robots[robot_id].to_dict()
    
    def get_all_status(self) -> dict:
        """
        Get status of all robots.
        
        Returns:
            Dictionary with robot IDs as keys and status as values
        """
        status = {}
        for robot_id, robot in self.robots.items():
            status[robot_id] = {
                "status": robot.status.value,
                "health": robot.health.value,
                "port": robot.port,
                "battery": robot.battery_level,
                "cpu": robot.cpu_usage,
                "memory": robot.memory_usage,
                "last_heartbeat": robot.last_heartbeat,
                "position": robot.position
            }
        return status
    
    def get_summary(self) -> dict:
        """
        Get a summary of the multi-robot system.
        
        Returns:
            Summary dictionary with system overview
        """
        total = len(self.robots)
        online = sum(1 for r in self.robots.values() if r.status == RobotStatus.ONLINE)
        healthy = sum(1 for r in self.robots.values() if r.health == HealthLevel.HEALTHY)
        failed = sum(1 for r in self.robots.values() if r.status in [RobotStatus.ERROR, RobotStatus.OFFLINE])
        
        avg_battery = 0.0
        avg_cpu = 0.0
        if total > 0:
            avg_battery = sum(r.battery_level for r in self.robots.values()) / total
            avg_cpu = sum(r.cpu_usage for r in self.robots.values()) / total
        
        return {
            "total_robots": total,
            "online_robots": online,
            "healthy_robots": healthy,
            "failed_robots": failed,
            "system_health": "healthy" if failed == 0 else "degraded",
            "average_battery": round(avg_battery, 2),
            "average_cpu_usage": round(avg_cpu, 2),
            "connected": self._connected,
            "timestamp": time.time()
        }
    
    def is_all_healthy(self) -> bool:
        """
        Check if all robots are healthy.
        
        Returns:
            True if all robots are healthy, False otherwise
        """
        return all(r.health == HealthLevel.HEALTHY for r in self.robots.values())
    
    def get_failed_robots(self) -> List[dict]:
        """
        Get list of failed robots with their error details.
        
        Returns:
            List of dictionaries containing failed robot information
        """
        failed = []
        for robot_id, robot in self.robots.items():
            if robot.status in [RobotStatus.ERROR, RobotStatus.OFFLINE] or robot.health == HealthLevel.CRITICAL:
                failed.append({
                    "id": robot_id,
                    "port": robot.port,
                    "status": robot.status.value,
                    "health": robot.health.value,
                    "error_message": robot.error_message,
                    "last_heartbeat": robot.last_heartbeat
                })
        return failed
    
    def broadcast_command(self, command: str, params: Optional[Dict] = None) -> List[str]:
        """
        Send a command to all robots.
        
        Args:
            command: Command string to send
            params: Optional command parameters
            
        Returns:
            List of robot IDs that received the command
        """
        if not self._connected:
            print("[MultiRobotDebugger] Not connected to MQTT broker")
            return []
        
        payload = {
            "command": command,
            "params": params or {},
            "timestamp": time.time(),
            "debugger_id": self.client_id
        }
        
        published_to = []
        for robot_id in self.robots:
            topic = MQTTTopics.robot_command(robot_id)
            self._mqtt_client.publish(topic, json.dumps(payload))
            published_to.append(robot_id)
        
        # Also broadcast to all
        self._mqtt_client.publish(
            MQTTTopics.BROADCAST_COMMAND, 
            json.dumps({**payload, "target": "all"})
        )
        
        # Log command
        self.command_history.append({
            "command": command,
            "params": params,
            "timestamp": time.time(),
            "target_count": len(published_to)
        })
        
        print(f"[MultiRobotDebugger] Broadcast command '{command}' to {len(published_to)} robots")
        return published_to
    
    def send_command_to_robot(self, robot_id: str, command: str, 
                              params: Optional[Dict] = None) -> bool:
        """
        Send a command to a specific robot.
        
        Args:
            robot_id: Target robot identifier
            command: Command string
            params: Optional command parameters
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if robot_id not in self.robots:
            print(f"[MultiRobotDebugger] Robot {robot_id} not found")
            return False
        
        if not self._connected:
            print("[MultiRobotDebugger] Not connected to MQTT broker")
            return False
        
        payload = {
            "command": command,
            "params": params or {},
            "timestamp": time.time(),
            "debugger_id": self.client_id
        }
        
        topic = MQTTTopics.robot_command(robot_id)
        self._mqtt_client.publish(topic, json.dumps(payload))
        
        self.command_history.append({
            "command": command,
            "params": params,
            "timestamp": time.time(),
            "target": robot_id
        })
        
        return True
    
    def analyze_collective_behavior(self) -> dict:
        """
        Analyze collective behavior of the robot swarm.
        
        Returns:
            Dictionary containing behavior analysis results
        """
        current_time = time.time()
        
        # Cache analysis for 5 seconds to avoid excessive computation
        if current_time - self._last_analysis_time < 5:
            return self._behavior_cache
        
        if not self.robots:
            self._behavior_cache = {
                "coordination": 0.0,
                "efficiency": 0.0,
                "divergence": 0.0,
                "patterns": [],
                "recommendations": ["No robots in system to analyze"]
            }
            return self._behavior_cache
        
        # Calculate coordination (how well robots are positioned relative to each other)
        positions = [r.position for r in self.robots.values() if r.position]
        coordination = self._calculate_coordination(positions)
        
        # Calculate efficiency (based on task completion and resource usage)
        efficiency = self._calculate_efficiency()
        
        # Calculate divergence (how spread out the robots are)
        divergence = self._calculate_divergence(positions)
        
        # Detect patterns
        patterns = self._detect_patterns()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        analysis = {
            "coordination": round(coordination, 3),
            "efficiency": round(efficiency, 3),
            "divergence": round(divergence, 3),
            "patterns": patterns,
            "recommendations": recommendations,
            "timestamp": current_time,
            "analyzed_robots": len(self.robots)
        }
        
        self._behavior_cache = analysis
        self._last_analysis_time = current_time
        
        return analysis
    
    def _calculate_coordination(self, positions: List[Dict]) -> float:
        """Calculate coordination score based on robot positions."""
        if len(positions) < 2:
            return 1.0
        
        # Simple metric: closer positions indicate better coordination
        # In practice, this would use more sophisticated algorithms
        return 0.8  # Placeholder
    
    def _calculate_efficiency(self) -> float:
        """Calculate system efficiency."""
        if not self.robots:
            return 0.0
        
        avg_health = sum(
            1.0 if r.health == HealthLevel.HEALTHY else 
            0.5 if r.health == HealthLevel.WARNING else 0.0
            for r in self.robots.values()
        ) / len(self.robots)
        
        return avg_health
    
    def _calculate_divergence(self, positions: List[Dict]) -> float:
        """Calculate position divergence."""
        if len(positions) < 2:
            return 0.0
        return 0.3  # Placeholder
    
    def _detect_patterns(self) -> List[Dict]:
        """Detect behavioral patterns."""
        patterns = []
        
        # Check for synchronized movement
        online_count = sum(1 for r in self.robots.values() if r.status == RobotStatus.ONLINE)
        if online_count == len(self.robots) and len(self.robots) > 1:
            patterns.append({
                "type": "synchronized",
                "description": "All robots are online and potentially coordinated",
                "confidence": 0.7
            })
        
        # Check for idle state
        if all(r.cpu_usage < 10 for r in self.robots.values() if self.robots):
            patterns.append({
                "type": "idle",
                "description": "All robots appear to be idle",
                "confidence": 0.9
            })
        
        return patterns
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current state."""
        recommendations = []
        
        failed = self.get_failed_robots()
        if failed:
            recommendations.append(f"Attention required: {len(failed)} robot(s) in failed state")
        
        low_battery = [r.id for r in self.robots.values() if r.battery_level < 20]
        if low_battery:
            recommendations.append(f"Charge recommended for: {', '.join(low_battery)}")
        
        high_cpu = [r.id for r in self.robots.values() if r.cpu_usage > 80]
        if high_cpu:
            recommendations.append(f"High CPU usage detected for: {', '.join(high_cpu)}")
        
        if not recommendations:
            recommendations.append("System is operating normally")
        
        return recommendations
    
    def save_state(self, filepath: str) -> bool:
        """
        Save current system state to a file.
        
        Args:
            filepath: Path to save the state file
            
        Returns:
            True if state saved successfully
        """
        try:
            state = {
                "debugger_id": self.client_id,
                "mqtt_broker": self.mqtt_broker,
                "timestamp": time.time(),
                "robots": {rid: robot.to_dict() for rid, robot in self.robots.items()},
                "summary": self.get_summary(),
                "command_history": self.command_history[-100:],  # Last 100 commands
                "behavior_analysis": self._behavior_cache
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"[MultiRobotDebugger] State saved to {filepath}")
            return True
        except Exception as e:
            print(f"[MultiRobotDebugger] Error saving state: {e}")
            return False
    
    def load_state(self, filepath: str) -> bool:
        """
        Load system state from a file.
        
        Args:
            filepath: Path to the state file
            
        Returns:
            True if state loaded successfully
        """
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Restore robots
            for rid, robot_data in state.get("robots", {}).items():
                self.robots[rid] = RobotInfo(
                    id=robot_data["id"],
                    port=robot_data["port"],
                    status=RobotStatus(robot_data["status"]),
                    health=HealthLevel(robot_data["health"]),
                    last_heartbeat=robot_data.get("last_heartbeat", 0),
                    battery_level=robot_data.get("battery_level", 100),
                    cpu_usage=robot_data.get("cpu_usage", 0),
                    memory_usage=robot_data.get("memory_usage", 0),
                    position=robot_data.get("position", {}),
                    metadata=robot_data.get("metadata", {})
                )
            
            print(f"[MultiRobotDebugger] State loaded from {filepath}")
            return True
        except Exception as e:
            print(f"[MultiRobotDebugger] Error loading state: {e}")
            return False


# ============== USAGE EXAMPLE ==============

if __name__ == "__main__":
    """
    Example usage of MultiRobotDebugger
    """
    
    # Create debugger instance
    debugger = MultiRobotDebugger(mqtt_broker="localhost", mqtt_port=1883)
    
    # Connect to MQTT broker
    print("Connecting to MQTT broker...")
    if debugger.connect():
        print("Connected successfully!")
    else:
        print("Failed to connect. Running in offline mode...")
    
    # Add robots to the system
    print("\nAdding robots...")
    debugger.add_robot("robot_001", port=8001, metadata={"type": "manipulator", "location": "lab_a"})
    debugger.add_robot("robot_002", port=8002, metadata={"type": "mobile", "location": "lab_a"})
    debugger.add_robot("robot_003", port=8003, metadata={"type": "mobile", "location": "lab_b"})
    
    # Get all robot status
    print("\nAll robot status:")
    print(json.dumps(debugger.get_all_status(), indent=2))
    
    # Get system summary
    print("\nSystem summary:")
    print(json.dumps(debugger.get_summary(), indent=2))
    
    # Check health
    print(f"\nAll robots healthy: {debugger.is_all_healthy()}")
    
    # Get failed robots
    print(f"Failed robots: {debugger.get_failed_robots()}")
    
    # Broadcast command to all robots
    print("\nBroadcasting 'status_check' command...")
    debugger.broadcast_command("status_check", {"verbose": True})
    
    # Send command to specific robot
    debugger.send_command_to_robot("robot_001", "move_to", {"x": 1.0, "y": 2.0})
    
    # Analyze collective behavior
    print("\nCollective behavior analysis:")
    print(json.dumps(debugger.analyze_collective_behavior(), indent=2))
    
    # Save state
    debugger.save_state("multi_robot_state.json")
    
    # Simulate some robot updates (in real scenario, these come via MQTT)
    print("\nSimulating robot updates...")
    debugger.robots["robot_001"].status = RobotStatus.ONLINE
    debugger.robots["robot_001"].health = HealthLevel.HEALTHY
    debugger.robots["robot_001"].battery_level = 85.0
    debugger.robots["robot_001"].position = {"x": 1.0, "y": 2.0, "z": 0.0}
    
    debugger.robots["robot_002"].status = RobotStatus.ONLINE
    debugger.robots["robot_002"].health = HealthLevel.WARNING
    debugger.robots["robot_002"].battery_level = 15.0
    
    # Final status check
    print("\nFinal system summary:")
    print(json.dumps(debugger.get_summary(), indent=2))
    
    # Final behavior analysis
    print("\nFinal collective behavior analysis:")
    print(json.dumps(debugger.analyze_collective_behavior(), indent=2))
    
    # Cleanup
    debugger.disconnect()
    print("\nDisconnected from MQTT broker.")
