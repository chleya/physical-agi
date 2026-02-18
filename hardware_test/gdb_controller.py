#!/usr/bin/env python3
"""
GDB Controller Module for OpenOCD Integration

This module provides a high-level interface for controlling GDB connected to
OpenOCD for embedded debugging. It supports breakpoint management, variable
inspection, memory operations, register access, and execution control.
"""

import subprocess
import re
import threading
import time
import socket
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class Breakpoint:
    """Represents a breakpoint in the target."""
    id: int
    file: str
    line: int
    address: int
    enabled: bool = True


class GDBController:
    """
    GDB Controller for OpenOCD-based debugging.
    
    This class provides methods to interact with GDB connected to an OpenOCD
    server for embedded target debugging.
    
    Attributes:
        openocd_path: Path to the OpenOCD executable.
        config_file: OpenOCD configuration file.
        gdb_process: subprocess.Popen instance for GDB.
        connected: Connection status flag.
    """
    
    def __init__(self, openocd_path: str = "openocd", config_file: str = None):
        """
        Initialize the GDB controller.
        
        Args:
            openocd_path: Path to the OpenOCD executable.
            config_file: OpenOCD configuration file path.
        """
        self.openocd_path = openocd_path
        self.config_file = config_file
        self.gdb_process: Optional[subprocess.Popen] = None
        self.connected = False
        self._lock = threading.Lock()
        self._output_thread: Optional[threading.Thread] = None
        self._output_buffer = []
        self._breakpoints: Dict[int, Breakpoint] = {}
        self._target = "127.0.0.1:3333"  # Default OpenOCD GDB server port
    
    def connect(self, target: str = "127.0.0.1:3333") -> bool:
        """
        Connect to the OpenOCD GDB server.
        
        Args:
            target: Target address in host:port format.
                   Default is 127.0.0.1:3333 (OpenOCD default GDB port).
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        with self._lock:
            if self.connected:
                self.disconnect()
            
            self._target = target
            
            # Start GDB with MI (Machine Interface) mode
            gdb_cmd = [
                "arm-none-eabi-gdb",  # Use appropriate GDB for your target
                "-q",  # Quiet mode
                "-i", "mi"  # MI interface mode
            ]
            
            try:
                self.gdb_process = subprocess.Popen(
                    gdb_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Start output reading thread
                self._output_thread = threading.Thread(
                    target=self._read_output,
                    daemon=True
                )
                self._output_thread.start()
                
                # Connect to target
                response = self._send_command(f"target remote {target}")
                if response and "^connected" in response or "Remote debugging" in response:
                    self.connected = True
                    # Disable pagination
                    self._send_command("set pagination off")
                    return True
                else:
                    self._cleanup()
                    return False
                    
            except Exception as e:
                print(f"Connection failed: {e}")
                self._cleanup()
                return False
    
    def disconnect(self) -> None:
        """
        Disconnect from the target and terminate GDB.
        """
        with self._lock:
            if self.connected:
                self._send_command("disconnect")
                self._send_command("quit")
            
            self._cleanup()
            self.connected = False
    
    def _cleanup(self) -> None:
        """Clean up GDB process and resources."""
        if self.gdb_process:
            try:
                self.gdb_process.terminate()
                self.gdb_process.wait(timeout=2)
            except Exception:
                try:
                    self.gdb_process.kill()
                except Exception:
                    pass
            self.gdb_process = None
        
        self._output_thread = None
        self._output_buffer = []
        self._breakpoints.clear()
    
    def _read_output(self) -> None:
        """Read and buffer GDB output in a separate thread."""
        while self.gdb_process and self.gdb_process.stdout:
            line = self.gdb_process.stdout.readline()
            if line:
                self._output_buffer.append(line.strip())
    
    def _send_command(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """
        Send a command to GDB and wait for response.
        
        Args:
            command: GDB command to send.
            timeout: Maximum time to wait for response.
        
        Returns:
            str: Response from GDB, or None on timeout.
        """
        if not self.gdb_process:
            return None
        
        with self._lock:
            self._output_buffer.clear()
            
            # Send command
            self.gdb_process.stdin.write(command + "\n")
            self.gdb_process.stdin.flush()
            
            # Wait for response
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self._output_buffer:
                    # Get all available output
                    response = "\n".join(self._output_buffer)
                    self._output_buffer.clear()
                    break
                time.sleep(0.05)
            
            return response if response else None
    
    def breakpoint_set(self, file: str, line: int) -> Optional[int]:
        """
        Set a breakpoint at the specified file and line.
        
        Args:
            file: Source file path.
            line: Line number.
        
        Returns:
            int: Breakpoint ID if successful, None otherwise.
        """
        command = f"break {file}:{line}"
        response = self._send_command(command)
        
        if response and "Breakpoint" in response:
            # Parse breakpoint ID from response
            match = re.search(r"Breakpoint\s+(\d+)", response)
            if match:
                bp_id = int(match.group(1))
                # Get breakpoint info
                info_response = self._send_command(f"info breakpoint {bp_id}")
                if info_response:
                    # Parse breakpoint details
                    addr_match = re.search(r"0x[0-9a-fA-F]+", info_response)
                    addr = int(addr_match.group(0), 16) if addr_match else 0
                    
                    bp = Breakpoint(
                        id=bp_id,
                        file=file,
                        line=line,
                        address=addr
                    )
                    self._breakpoints[bp_id] = bp
                    return bp_id
        
        return None
    
    def breakpoint_list(self) -> List[Breakpoint]:
        """
        List all set breakpoints.
        
        Returns:
            List[Breakpoint]: List of all breakpoints.
        """
        response = self._send_command("info breakpoint")
        
        breakpoints = []
        if response:
            # Parse breakpoint list
            lines = response.split("\n")
            for line in lines:
                if "Breakpoint" in line or "bkp" in line.lower():
                    match = re.search(r"(\d+).*?(\S+\.c?):(\d+)", line)
                    if match:
                        bp_id = int(match.group(1))
                        filename = match.group(2)
                        line_num = int(match.group(3))
                        
                        addr_match = re.search(r"0x[0-9a-fA-F]+", line)
                        addr = int(addr_match.group(0), 16) if addr_match else 0
                        
                        bp = Breakpoint(
                            id=bp_id,
                            file=filename,
                            line=line_num,
                            address=addr
                        )
                        breakpoints.append(bp)
                        self._breakpoints[bp_id] = bp
        
        return breakpoints
    
    def breakpoint_clear(self, id: int) -> bool:
        """
        Clear a breakpoint by ID.
        
        Args:
            id: Breakpoint ID to clear.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command(f"delete breakpoint {id}")
        
        if response is not None:
            self._breakpoints.pop(id, None)
            return True
        
        return False
    
    def step(self) -> bool:
        """
        Step one instruction.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command("step")
        return response is not None
    
    def next(self) -> bool:
        """
        Step one source line (skip functions).
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command("next")
        return response is not None
    
    def continue(self) -> bool:
        """
        Continue execution.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command("continue")
        return response is not None
    
    def halt(self) -> bool:
        """
        Halt execution.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command("interrupt")
        return response is not None
    
    def reset(self, mode: str = "halt") -> bool:
        """
        Reset the target.
        
        Args:
            mode: Reset mode - "halt", "run", or "init".
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command(f"monitor reset {mode}")
        return response is not None
    
    def variable_get(self, name: str) -> Optional[Any]:
        """
        Get the value of a variable.
        
        Args:
            name: Variable name.
        
        Returns:
            Variable value, or None if not found.
        """
        response = self._send_command(f"print {name}")
        
        if response:
            # Parse value from response
            match = re.search(r"\$\d+\s*=\s*(.+)", response)
            if match:
                value_str = match.group(1).strip()
                
                # Try to parse as integer
                try:
                    if value_str.startswith("0x"):
                        return int(value_str, 16)
                    elif value_str.isdigit():
                        return int(value_str)
                except ValueError:
                    pass
                
                # Return as string for other types
                return value_str
        
        return None
    
    def variable_set(self, name: str, value: Any) -> bool:
        """
        Set the value of a variable.
        
        Args:
            name: Variable name.
            value: Value to set.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if isinstance(value, str):
            response = self._send_command(f"set {name} = \"{value}\"")
        else:
            response = self._send_command(f"set {name} = {value}")
        
        return response is not None
    
    def memory_read(self, addr: int, size: int) -> bytes:
        """
        Read memory from the target.
        
        Args:
            addr: Memory address.
            size: Number of bytes to read.
        
        Returns:
            bytes: Read memory data.
        """
        # Use x command to examine memory
        format_str = f"/{size}x" if size <= 4 else "/x"
        response = self._send_command(f"x {format_str} 0x{addr:x}")
        
        if response:
            # Parse hex values from response
            values = re.findall(r"0x[0-9a-fA-F]+", response)
            result = bytearray()
            
            for val in values:
                try:
                    result.append(int(val, 16) & 0xFF)
                    if len(result) >= size:
                        break
                except ValueError:
                    continue
            
            return bytes(result)
        
        return b""
    
    def memory_write(self, addr: int, data: bytes) -> bool:
        """
        Write memory to the target.
        
        Args:
            addr: Memory address.
            data: Data bytes to write.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        # Write byte by byte
        for i, byte in enumerate(data):
            response = self._send_command(f"set *((unsigned char *)0x{addr + i:i}x) = {byte}")
            if response is None:
                return False
        
        return True
    
    def registers_read(self) -> Dict[str, int]:
        """
        Read all registers.
        
        Returns:
            Dict mapping register names to values.
        """
        response = self._send_command("info registers")
        registers = {}
        
        if response:
            lines = response.split("\n")
            for line in lines:
                # Match patterns like "r0             0x20000000       536870912"
                match = re.search(r"(\w+)\s+0x([0-9a-fA-F]+)", line)
                if match:
                    reg_name = match.group(1)
                    reg_value = int(match.group(2), 16)
                    registers[reg_name] = reg_value
        
        # Also try to get all registers with "info all-registers"
        all_regs_response = self._send_command("info all-registers")
        if all_regs_response:
            lines = all_regs_response.split("\n")
            for line in lines:
                match = re.search(r"(\w+)\s+0x([0-9a-fA-F]+)", line)
                if match:
                    reg_name = match.group(1)
                    if reg_name not in registers:
                        registers[reg_name] = int(match.group(2), 16)
        
        return registers
    
    def register_read(self, name: str) -> Optional[int]:
        """
        Read a specific register.
        
        Args:
            name: Register name (e.g., "r0", "pc", "sp").
        
        Returns:
            int: Register value, or None if not found.
        """
        response = self._send_command(f"print ${name}")
        
        if response:
            match = re.search(r"\$\d+\s*=\s*0x([0-9a-fA-F]+)", response)
            if match:
                return int(match.group(1), 16)
        
        return None
    
    def register_write(self, name: str, value: int) -> bool:
        """
        Write to a specific register.
        
        Args:
            name: Register name.
            value: Value to write.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command(f"set ${name} = {value}")
        return response is not None
    
    def backtrace(self) -> List[Dict[str, Any]]:
        """
        Get the current backtrace.
        
        Returns:
            List of frame dictionaries with 'function', 'file', 'line', 'address'.
        """
        response = self._send_command("backtrace")
        frames = []
        
        if response:
            lines = response.split("\n")
            for line in lines:
                if "#" in line:
                    # Match patterns like "#0  main () at main.c:10"
                    match = re.search(
                        r"#\d+\s+(\S+)\s+\((.*?)\)\s+at\s+(\S+):(\d+)",
                        line
                    )
                    if match:
                        frames.append({
                            "function": match.group(1),
                            "arguments": match.group(2),
                            "file": match.group(3),
                            "line": int(match.group(4)),
                            "address": 0  # Address not available in text mode
                        })
                    else:
                        # Try simpler pattern
                        match = re.search(r"#\d+\s+(\S+)\s+at\s+(\S+):(\d+)", line)
                        if match:
                            frames.append({
                                "function": match.group(1),
                                "file": match.group(2),
                                "line": int(match.group(3)),
                                "address": 0
                            })
        
        return frames
    
    def run_to_main(self) -> bool:
        """
        Run until main function is reached.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        # Set temporary breakpoint at main
        bp_id = self.breakpoint_set("*", 1)  # Will be updated when source is loaded
        
        if bp_id is None:
            return False
        
        # Try to find main and set breakpoint there
        main_bp = self.breakpoint_set("main", 1)
        
        # Continue execution
        result = self.continue()
        
        # Clean up temporary breakpoint
        self.breakpoint_clear(bp_id)
        
        return result
    
    def get_all_variables(self) -> Dict[str, Any]:
        """
        Get all local variables in the current scope.
        
        Returns:
            Dict mapping variable names to values.
        """
        response = self._send_command("info locals")
        variables = {}
        
        if response:
            lines = response.split("\n")
            for line in lines:
                if "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        var_value = parts[1].strip()
                        
                        # Try to convert to int
                        try:
                            if var_value.startswith("0x"):
                                variables[var_name] = int(var_value, 16)
                            elif var_value.isdigit():
                                variables[var_name] = int(var_value)
                            else:
                                variables[var_name] = var_value
                        except ValueError:
                            variables[var_name] = var_value
        
        return variables
    
    def get_current_location(self) -> Dict[str, Any]:
        """
        Get the current program location.
        
        Returns:
            Dict with 'file', 'line', 'function', and 'address'.
        """
        response = self._send_command("frame")
        
        if response:
            # Match patterns like "#0  main () at main.c:10"
            match = re.search(
                r"#\d+\s+(\S+)\s+\((.*?)\)\s+at\s+(\S+):(\d+)",
                response
            )
            if match:
                return {
                    "function": match.group(1),
                    "arguments": match.group(2),
                    "file": match.group(3),
                    "line": int(match.group(4))
                }
        
        return {}
    
    def load_elf(self, elf_path: str) -> bool:
        """
        Load an ELF file to the target.
        
        Args:
            elf_path: Path to the ELF file.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        response = self._send_command(f"load {elf_path}")
        return response is not None
    
    def add_symbol_file(self, symbols_path: str, offset: int = 0) -> bool:
        """
        Add a symbol file.
        
        Args:
            symbols_path: Path to the symbol file.
            offset: Load offset.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if offset:
            response = self._send_command(f"add-symbol-file {symbols_path} 0x{offset:x}")
        else:
            response = self._send_command(f"add-symbol-file {symbols_path}")
        
        return response is not None
    
    def monitor_command(self, command: str) -> Optional[str]:
        """
        Send a monitor command to OpenOCD.
        
        Args:
            command: Monitor command.
        
        Returns:
            str: Response from OpenOCD.
        """
        response = self._send_command(f"monitor {command}")
        return response
    
    def get_pc(self) -> Optional[int]:
        """
        Get the current program counter.
        
        Returns:
            int: Program counter value, or None.
        """
        return self.register_read("pc")
    
    def set_pc(self, value: int) -> bool:
        """
        Set the program counter.
        
        Args:
            value: New PC value.
        
        Returns:
            bool: True if successful.
        """
        return self.register_write("pc", value)
    
    def get_sp(self) -> Optional[int]:
        """
        Get the current stack pointer.
        
        Returns:
            int: Stack pointer value, or None.
        """
        return self.register_read("sp")
    
    def step_instruction(self) -> bool:
        """
        Step one instruction (alias for step()).
        
        Returns:
            bool: True if successful.
        """
        return self.step()
    
    def step_line(self) -> bool:
        """
        Step one source line (alias for next()).
        
        Returns:
            bool: True if successful.
        """
        return self.next()


# Usage Example
if __name__ == "__main__":
    # Example usage of the GDBController
    
    # Initialize the controller
    gdb_ctrl = GDBController(
        openocd_path="openocd",
        config_file="interface/stlink.cfg"
    )
    
    print("=" * 50)
    print("GDB Controller Usage Example")
    print("=" * 50)
    
    # Connect to OpenOCD GDB server
    print("\n1. Connecting to OpenOCD GDB server...")
    if gdb_ctrl.connect("127.0.0.1:3333"):
        print("   ✓ Connected successfully!")
    else:
        print("   ✗ Connection failed!")
        exit(1)
    
    # Load an ELF file (if you have one)
    # print("\n2. Loading ELF file...")
    # if gdb_ctrl.load_elf("path/to/your/program.elf"):
    #     print("   ✓ ELF loaded successfully!")
    # else:
    #     print("   ✗ Failed to load ELF file")
    
    # Set a breakpoint
    print("\n2. Setting breakpoint at main.c:10...")
    bp_id = gdb_ctrl.breakpoint_set("main.c", 10)
    if bp_id:
        print(f"   ✓ Breakpoint set (ID: {bp_id})")
    else:
        print("   ✗ Failed to set breakpoint")
    
    # List breakpoints
    print("\n3. Listing breakpoints...")
    breakpoints = gdb_ctrl.breakpoint_list()
    for bp in breakpoints:
        print(f"   - Breakpoint {bp.id}: {bp.file}:{bp.line}")
    
    # Run to main
    print("\n4. Running to main()...")
    if gdb_ctrl.run_to_main():
        print("   ✓ Reached main!")
    else:
        print("   ✗ Failed to run to main")
    
    # Get current location
    location = gdb_ctrl.get_current_location()
    if location:
        print(f"\n5. Current location: {location.get('function', 'unknown')} at {location.get('file', 'unknown')}:{location.get('line', '?')}")
    
    # Get all local variables
    print("\n6. Local variables:")
    variables = gdb_ctrl.get_all_variables()
    for name, value in variables.items():
        print(f"   - {name} = {value}")
    
    # Read registers
    print("\n7. Registers:")
    registers = gdb_ctrl.registers_read()
    for reg_name in ["r0", "r1", "r2", "r3", "sp", "lr", "pc"]:
        if reg_name in registers:
            print(f"   - {reg_name}: 0x{registers[reg_name]:08x}")
    
    # Read memory (example: read 16 bytes from address 0x20000000)
    print("\n8. Reading memory at 0x20000000 (16 bytes):")
    mem_data = gdb_ctrl.memory_read(0x20000000, 16)
    print(f"   Data: {mem_data.hex(' ').upper()}")
    
    # Get backtrace
    print("\n9. Backtrace:")
    backtrace = gdb_ctrl.backtrace()
    for i, frame in enumerate(backtrace):
        print(f"   #{i}: {frame.get('function', 'unknown')}() at {frame.get('file', '?')}:{frame.get('line', '?')}")
    
    # Step execution
    print("\n10. Stepping one instruction...")
    if gdb_ctrl.step_instruction():
        print("    ✓ Stepped!")
    
    # Get new location
    location = gdb_ctrl.get_current_location()
    if location:
        print(f"\n11. New location: {location.get('function', 'unknown')} at {location.get('file', 'unknown')}:{location.get('line', '?')}")
    
    # Clear breakpoint
    if bp_id:
        print(f"\n12. Clearing breakpoint {bp_id}...")
        if gdb_ctrl.breakpoint_clear(bp_id):
            print("    ✓ Breakpoint cleared!")
    
    # Continue execution
    print("\n13. Continuing execution...")
    gdb_ctrl.continue()
    
    # Halt and disconnect
    print("\n14. Halting execution...")
    gdb_ctrl.halt()
    
    print("\n15. Disconnecting...")
    gdb_ctrl.disconnect()
    print("    ✓ Disconnected!")
    
    print("\n" + "=" * 50)
    print("Example completed successfully!")
    print("=" * 50)
