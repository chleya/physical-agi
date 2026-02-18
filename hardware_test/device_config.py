#!/usr/bin/env python3
"""
通用硬件设备配置框架
=====================
让所有调试工具适配不同设备

使用:
    from device_config import DeviceConfig, register_device
    register_device("my_robot", config)
    
    # 所有工具自动适配
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class DeviceType(Enum):
    """设备类型"""
    ROBOT = "robot"
    SENSOR = "sensor"
    CONTROLLER = "controller"
    ACTUATOR = "actuator"
    CUSTOM = "custom"


class Protocol(Enum):
    """通信协议"""
    UART = "uart"
    I2C = "i2c"
    SPI = "spi"
    CAN = "can"
    BLE = "ble"
    WIFI = "wifi"
    CUSTOM = "custom"


@dataclass
class PinConfig:
    """引脚配置"""
    name: str
    pin: int
    mode: str  # input, output, analog, pwm
    function: str
    voltage: float = 3.3


@dataclass
class ComponentConfig:
    """组件配置"""
    name: str
    type: str  # imu, motor, battery, etc.
    protocol: Protocol
    address: Optional[str] = None
    pins: List[PinConfig] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceConfig:
    """设备配置"""
    name: str
    type: DeviceType
    description: str = ""
    version: str = "1.0"
    
    # 通信配置
    serial_port: Optional[str] = None
    baud_rate: int = 115200
    protocol: Protocol = Protocol.UART
    
    # 组件
    components: List[ComponentConfig] = field(default_factory=list)
    
    # 限制
    max_current_ma: float = 1000
    voltage_range: tuple = (3.0, 4.2)
    temp_limit_c: float = 80.0
    
    # 自定义
    custom_params: Dict[str, Any] = field(default_factory=dict)


class DeviceRegistry:
    """设备注册表"""
    
    _devices: Dict[str, DeviceConfig] = {}
    _current_device: Optional[str] = None
    
    @classmethod
    def register(cls, config: DeviceConfig) -> bool:
        """注册设备"""
        cls._devices[config.name] = config
        return True
    
    @classmethod
    def get(cls, name: str) -> Optional[DeviceConfig]:
        """获取设备配置"""
        return cls._devices.get(name)
    
    @classmethod
    def set_current(cls, name: str) -> bool:
        """设置当前设备"""
        if name in cls._devices:
            cls._current_device = name
            return True
        return False
    
    @classmethod
    def get_current(cls) -> Optional[DeviceConfig]:
        """获取当前设备"""
        if cls._current_device:
            return cls._devices.get(cls._current_device)
        return None
    
    @classmethod
    def list_devices(cls) -> List[str]:
        """列出所有设备"""
        return list(cls._devices.keys())
    
    @classmethod
    def from_file(cls, path: str) -> DeviceConfig:
        """从文件加载"""
        with open(path, 'r') as f:
            if path.endswith('.json'):
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        return cls._parse_dict(data)
    
    @classmethod
    def _parse_dict(cls, data: Dict) -> DeviceConfig:
        """解析字典为DeviceConfig"""
        return DeviceConfig(
            name=data['name'],
            type=DeviceType(data.get('type', 'custom')),
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            serial_port=data.get('serial_port'),
            baud_rate=data.get('baud_rate', 115200),
            protocol=Protocol(data.get('protocol', 'uart')),
            max_current_ma=data.get('max_current_ma', 1000),
            voltage_range=tuple(data.get('voltage_range', [3.0, 4.2])),
            temp_limit_c=data.get('temp_limit_c', 80.0),
        )
    
    @classmethod
    def save(cls, name: str, path: str) -> bool:
        """保存设备配置"""
        config = cls.get(name)
        if not config:
            return False
        
        data = {
            'name': config.name,
            'type': config.type.value,
            'description': config.description,
            'version': config.version,
            'serial_port': config.serial_port,
            'baud_rate': config.baud_rate,
            'protocol': config.protocol.value,
            'max_current_ma': config.max_current_ma,
            'voltage_range': list(config.voltage_range),
            'temp_limit_c': config.temp_limit_c,
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True


# ============ 内置设备模板 ============

def register_v5_robot():
    """注册 v5 机器人 (默认)"""
    config = DeviceConfig(
        name="v5_robot",
        type=DeviceType.ROBOT,
        description="NCA-Mesh v5 机器人 (STM32 + ESP32 + 2电机 + MPU6050)",
        serial_port="COM3",
        baud_rate=115200,
        components=[
            ComponentConfig(
                name="stm32",
                type="controller",
                protocol=Protocol.UART,
                address=None
            ),
            ComponentConfig(
                name="esp32",
                type="wifi_module",
                protocol=Protocol.UART,
                address=None
            ),
            ComponentConfig(
                name="mpu6050",
                type="imu",
                protocol=Protocol.I2C,
                address="0x68"
            ),
            ComponentConfig(
                name="motor_left",
                type="motor",
                protocol=Protocol.PWM,
                pins=[PinConfig("IN1", 0, "output", "PWM")]
            ),
            ComponentConfig(
                name="motor_right",
                type="motor",
                protocol=Protocol.PWM,
                pins=[PinConfig("IN1", 2, "output", "PWM")]
            ),
            ComponentConfig(
                name="battery",
                type="battery",
                protocol=Protocol.CUSTOM,
                params={"capacity_mah": 1500}
            ),
        ],
        max_current_ma=2000,
        voltage_range=(3.0, 4.2),
        temp_limit_c=70.0
    )
    DeviceRegistry.register(config)
    return config


def register_generic_robot(name: str, **kwargs):
    """注册通用机器人"""
    config = DeviceConfig(
        name=name,
        type=DeviceType.ROBOT,
        description=kwargs.get('description', f'Generic robot: {name}'),
        serial_port=kwargs.get('serial_port', 'COM3'),
        baud_rate=kwargs.get('baud_rate', 115200),
        max_current_ma=kwargs.get('max_current_ma', 2000),
        voltage_range=kwargs.get('voltage_range', (3.0, 4.2)),
        temp_limit_c=kwargs.get('temp_limit_c', 80.0),
    )
    DeviceRegistry.register(config)
    return config


def register_esp32_devkit():
    """注册 ESP32 DevKit"""
    config = DeviceConfig(
        name="esp32_devkit",
        type=DeviceType.CONTROLLER,
        description="ESP32 DevKit V1",
        serial_port="COM4",
        baud_rate=115200,
        protocol=Protocol.UART,
        max_current_ma=500,
        voltage_range=(3.0, 5.5),
        temp_limit_c=85.0
    )
    DeviceRegistry.register(config)
    return config


def register_stm32_nucleo():
    """注册 STM32 Nucleo"""
    config = DeviceConfig(
        name="stm32_nucleo",
        type=DeviceType.CONTROLLER,
        description="STM32 Nucleo F401RE",
        serial_port="COM5",
        baud_rate=115200,
        max_current_ma=300,
        voltage_range=(2.0, 3.6),
        temp_limit_c=85.0
    )
    DeviceRegistry.register(config)
    return config


# ============ 设备适配器 ============

class DeviceAdapter:
    """设备适配器 - 让工具适配不同设备"""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
    
    def get_serial_port(self) -> str:
        """获取串口"""
        return self.config.serial_port or "COM3"
    
    def get_baud_rate(self) -> int:
        """获取波特率"""
        return self.config.baud_rate
    
    def get_components(self) -> List[ComponentConfig]:
        """获取组件"""
        return self.config.components
    
    def find_component(self, type_name: str) -> Optional[ComponentConfig]:
        """查找组件"""
        for comp in self.config.components:
            if comp.type == type_name:
                return comp
        return None
    
    def get_motor_pins(self) -> List[PinConfig]:
        """获取电机引脚"""
        pins = []
        for comp in self.config.components:
            if comp.type == "motor":
                pins.extend(comp.pins)
        return pins
    
    def get_imu_config(self) -> Optional[ComponentConfig]:
        """获取IMU配置"""
        return self.find_component("imu")
    
    def get_battery_config(self) -> Optional[ComponentConfig]:
        """获取电池配置"""
        return self.find_component("battery")
    
    def get_limits(self) -> Dict:
        """获取限制"""
        return {
            'max_current_ma': self.config.max_current_ma,
            'voltage_min': self.config.voltage_range[0],
            'voltage_max': self.config.voltage_range[1],
            'temp_limit_c': self.config.temp_limit_c,
        }
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.config.name,
            'type': self.config.type.value,
            'serial_port': self.config.serial_port,
            'baud_rate': self.config.baud_rate,
            'components': [c.name for c in self.config.components],
            'limits': self.get_limits()
        }


# ============ 工具适配层 ============

class ToolAdapter:
    """工具适配器 - 让工具自动适配当前设备"""
    
    @staticmethod
    def adapt_wire_check(config: DeviceConfig) -> Dict:
        """适配连线检测工具"""
        adapter = DeviceAdapter(config)
        return {
            'port': adapter.get_serial_port(),
            'baud': adapter.get_baud_rate(),
            'components': [c.name for c in adapter.get_components()],
            'checks': {
                'imu': adapter.get_imu_config() is not None,
                'motors': len(adapter.get_motor_pins()) > 0,
                'battery': adapter.get_battery_config() is not None,
            }
        }
    
    @staticmethod
    def adapt_vision(config: DeviceConfig) -> Dict:
        """适配视觉检测工具"""
        adapter = DeviceAdapter(config)
        return {
            'components': [c.name for c in adapter.get_components()],
            'detection_targets': {
                'led': True,
                'motor': len(adapter.get_motor_pins()) > 0,
                'display': adapter.find_component("display") is not None,
            }
        }
    
    @staticmethod
    def adapt_ina219(config: DeviceConfig) -> Dict:
        """适配电流监控工具"""
        adapter = DeviceAdapter(config)
        limits = adapter.get_limits()
        return {
            'max_current_ma': limits['max_current_ma'],
            'voltage_range': (limits['voltage_min'], limits['voltage_max']),
        }
    
    @staticmethod
    def adapt_monitor(config: DeviceConfig) -> Dict:
        """适配监控工具"""
        adapter = DeviceAdapter(config)
        return {
            'port': adapter.get_serial_port(),
            'baud': adapter.get_baud_rate(),
            'channels': [c.name for c in adapter.get_components()],
            'channels_to_monitor': {
                'imu': adapter.get_imu_config() is not None,
                'motors': len(adapter.get_motor_pins()) > 0,
                'battery': adapter.get_battery_config() is not None,
            }
        }


# ============ 主接口 ============

def init_devices():
    """初始化内置设备模板"""
    register_v5_robot()
    register_esp32_devkit()
    register_stm32_nucleo()


def use_device(name: str) -> DeviceAdapter:
    """使用指定设备"""
    DeviceRegistry.set_current(name)
    config = DeviceRegistry.get(name)
    if config:
        return DeviceAdapter(config)
    return None


def list_devices() -> List[str]:
    """列出所有已注册设备"""
    return DeviceRegistry.list_devices()


def create_device_from_json(path: str) -> DeviceAdapter:
    """从JSON文件创建设备"""
    config = DeviceRegistry.from_file(path)
    DeviceRegistry.register(config)
    return DeviceAdapter(config)


def save_device(name: str, path: str) -> bool:
    """保存设备配置"""
    return DeviceRegistry.save(name, path)


# ============ 使用示例 ============

def example_usage():
    """使用示例"""
    # 1. 初始化内置设备
    init_devices()
    
    # 2. 列出设备
    print("可用设备:", list_devices())
    
    # 3. 使用 v5 机器人
    adapter = use_device("v5_robot")
    if adapter:
        print(f"使用设备: {adapter.config.name}")
        print(f"串口: {adapter.get_serial_port()}")
        print(f"电机引脚: {[p.name for p in adapter.get_motor_pins()]}")
    
    # 4. 工具适配
    config = DeviceRegistry.get("v5_robot")
    
    wire_check_cfg = ToolAdapter.adapt_wire_check(config)
    print("\n连线检测配置:", wire_check_cfg)
    
    monitor_cfg = ToolAdapter.adapt_monitor(config)
    print("\n监控配置:", monitor_cfg)
    
    # 5. 自定义设备
    register_generic_robot(
        name="my_robot",
        serial_port="COM10",
        baud_rate=9600,
        max_current_ma=1500,
        description="我的自定义机器人"
    )
    print("\n自定义设备已注册:", list_devices())


# ============ 配置文件模板 ============

DEVICE_TEMPLATE = {
    "name": "my_device",
    "type": "robot",
    "description": "我的设备",
    "version": "1.0",
    "serial_port": "COM3",
    "baud_rate": 115200,
    "protocol": "uart",
    "max_current_ma": 2000,
    "voltage_range": [3.0, 4.2],
    "temp_limit_c": 80.0,
    "components": [
        {
            "name": "controller",
            "type": "controller",
            "protocol": "uart"
        },
        {
            "name": "imu",
            "type": "imu",
            "protocol": "i2c",
            "address": "0x68"
        },
        {
            "name": "motor",
            "type": "motor",
            "protocol": "pwm",
            "pins": [
                {"name": "PWM", "pin": 0, "mode": "output", "function": "speed"}
            ]
        }
    ]
}


if __name__ == "__main__":
    example_usage()
