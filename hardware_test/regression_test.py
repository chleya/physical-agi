"""
Automatic Regression Test Module for Hardware Testing
=====================================================
Provides automated build, flash, test execution, and result comparison.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class RegressionTester:
    """
    Automated regression testing for hardware firmware.

    Supports:
    - Automated build and flash operations
    - Configurable test sequences
    - Baseline comparison and result tracking
    - Report generation
    """

    # Default test sequence definitions
    DEFAULT_TEST_SEQUENCE = [
        {"name": "power_on_test", "description": "Power-on self test", "timeout": 10},
        {"name": "memory_test", "description": "Memory integrity test", "timeout": 30},
        {"name": "sensor_calibration", "description": "Sensor calibration", "timeout": 60},
        {"name": "communication_test", "description": "Communication interface test", "timeout": 45},
        {"name": "motor_response_test", "description": "Motor response test", "timeout": 90},
        {"name": "thermal_test", "description": "Thermal performance test", "timeout": 120},
        {"name": "stress_test", "description": "Stress/load test", "timeout": 180},
        {"name": "integration_test", "description": "Full system integration test", "timeout": 240},
    ]

    def __init__(self, config_file: str):
        """
        Initialize the regression tester with a configuration file.

        Args:
            config_file: Path to JSON configuration file
        """
        self.config = self._load_config(config_file)
        self.baseline: Dict[str, Any] = {}
        self.test_results: Dict[str, Any] = {}
        self.current_results: Dict[str, Any] = {}

        # Extract config parameters
        self.project_root = self.config.get("project_root", ".")
        self.build_command = self.config.get("build_command", "make")
        self.build_args = self.config.get("build_args", [])
        self.flash_command = self.config.get("flash_command", "make")
        self.flash_args = self.config.get("flash_args", ["flash"])
        self.test_timeout = self.config.get("test_timeout", 300)
        self.results_dir = self.config.get("results_dir", "test_results")

        # Test sequence (use custom or default)
        self.test_sequence = self.config.get(
            "test_sequence", self.DEFAULT_TEST_SEQUENCE
        )

        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with open(config_file, 'r') as f:
            return json.load(f)

    def load_baseline(self, baseline_path: str) -> bool:
        """
        Load baseline test results for comparison.

        Args:
            baseline_path: Path to baseline JSON file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(baseline_path, 'r') as f:
                self.baseline = json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading baseline: {e}")
            return False

    def save_baseline(self, path: str) -> bool:
        """
        Save current test results as baseline.

        Args:
            path: Path to save baseline file

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(path, 'w') as f:
                json.dump(self.baseline, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving baseline: {e}")
            return False

    def build(self) -> bool:
        """
        Build the firmware/project.

        Returns:
            True if build succeeded, False otherwise
        """
        print(f"Building project in {self.project_root}...")

        try:
            cmd = [self.build_command] + self.build_args
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )

            if result.returncode == 0:
                print("Build succeeded")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                print(f"Build failed with code {result.returncode}")
                if result.stderr:
                    print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("Build timed out")
            return False
        except Exception as e:
            print(f"Build error: {e}")
            return False

    def flash(self, device_id: str) -> bool:
        """
        Flash firmware to device.

        Args:
            device_id: Device identifier (e.g., COM port, device path)

        Returns:
            True if flash succeeded, False otherwise
        """
        print(f"Flashing firmware to device {device_id}...")

        try:
            # Build flash command with device ID
            cmd = [self.flash_command] + [arg.format(device_id=device_id)
                                         for arg in self.flash_args]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )

            if result.returncode == 0:
                print("Flash succeeded")
                return True
            else:
                print(f"Flash failed with code {result.returncode}")
                if result.stderr:
                    print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("Flash timed out")
            return False
        except Exception as e:
            print(f"Flash error: {e}")
            return False

    def run_tests(self) -> Dict[str, Any]:
        """
        Execute the full test sequence.

        Returns:
            Dictionary containing test results
        """
        print("Starting test sequence execution...")
        self.current_results = {
            "timestamp": datetime.now().isoformat(),
            "test_sequence": [],
            "summary": {
                "total": len(self.test_sequence),
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total_duration": 0
            }
        }

        start_time = time.time()

        for test in self.test_sequence:
            test_name = test["name"]
            test_desc = test.get("description", "")
            timeout = test.get("timeout", 60)

            print(f"\nRunning: {test_name} - {test_desc}")

            test_result = self._run_single_test(test_name, timeout)

            self.current_results["test_sequence"].append(test_result)

            if test_result["status"] == "passed":
                self.current_results["summary"]["passed"] += 1
            elif test_result["status"] == "failed":
                self.current_results["summary"]["failed"] += 1
            else:
                self.current_results["summary"]["skipped"] += 1

        self.current_results["summary"]["total_duration"] = time.time() - start_time

        # Save results
        self._save_test_results()

        print(f"\nTest sequence complete: "
              f"{self.current_results['summary']['passed']}/"
              f"{self.current_results['summary']['total']} passed")

        return self.current_results

    def _run_single_test(self, test_name: str, timeout: int) -> Dict[str, Any]:
        """
        Run a single test case.

        Args:
            test_name: Name of the test to run
            timeout: Test timeout in seconds

        Returns:
            Test result dictionary
        """
        result = {
            "name": test_name,
            "status": "failed",
            "duration": 0,
            "metrics": {},
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }

        start_time = time.time()

        try:
            # Simulate test execution (replace with actual test logic)
            # This is where you would call the actual test harness
            test_passed, metrics, errors = self._execute_test_harness(
                test_name, timeout
            )

            result["status"] = "passed" if test_passed else "failed"
            result["metrics"] = metrics
            result["errors"] = errors

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))

        result["duration"] = time.time() - start_time

        return result

    def _execute_test_harness(self, test_name: str,
                               timeout: int) -> Tuple[bool, Dict, List[str]]:
        """
        Execute the actual test harness for a given test.

        Override this method with actual test implementation.

        Args:
            test_name: Name of the test
            timeout: Test timeout

        Returns:
            Tuple of (passed, metrics, errors)
        """
        # Placeholder: Simulate test execution
        # Replace with actual test logic
        time.sleep(0.1)  # Simulate quick test

        # Generate simulated metrics
        metrics = {
            "execution_time_ms": 100,
            "iterations": 10,
            "success_rate": 100.0
        }

        return True, metrics, []

    def _save_test_results(self):
        """Save test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.results_dir,
            f"test_results_{timestamp}.json"
        )

        with open(filename, 'w') as f:
            json.dump(self.current_results, f, indent=2)

        print(f"Results saved to {filename}")

    def compare_results(self, current: Dict[str, Any],
                        baseline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare current test results with baseline.

        Args:
            current: Current test results
            baseline: Baseline test results

        Returns:
            Comparison result dictionary
        """
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "baseline_timestamp": baseline.get("timestamp", "unknown"),
            "current_timestamp": current.get("timestamp", "unknown"),
            "test_comparisons": [],
            "summary": {
                "total_tests": 0,
                "improved": 0,
                "degraded": 0,
                "stable": 0,
                "new_tests": 0,
                "removed_tests": 0
            }
        }

        current_tests = {t["name"]: t for t in current.get("test_sequence", [])}
        baseline_tests = {t["name"]: t for t in baseline.get("test_sequence", [])}

        all_tests = set(current_tests.keys()) | set(baseline_tests.keys())

        for test_name in all_tests:
            test_comp = {
                "name": test_name,
                "status": "stable",
                "current_value": None,
                "baseline_value": None,
                "change_pct": 0
            }

            if test_name in current_tests and test_name in baseline_tests:
                # Compare existing tests
                current_metrics = current_tests[test_name].get("metrics", {})
                baseline_metrics = baseline_tests[test_name].get("metrics", {})

                # Compare key metric (execution time as example)
                current_val = current_metrics.get("execution_time_ms")
                baseline_val = baseline_metrics.get("execution_time_ms")

                test_comp["current_value"] = current_val
                test_comp["baseline_value"] = baseline_val

                if current_val is not None and baseline_val is not None:
                    if current_val < baseline_val:
                        test_comp["status"] = "improved"
                        comparison["summary"]["improved"] += 1
                    elif current_val > baseline_val:
                        test_comp["status"] = "degraded"
                        comparison["summary"]["degraded"] += 1
                    else:
                        comparison["summary"]["stable"] += 1

                    test_comp["change_pct"] = (
                        ((current_val - baseline_val) / baseline_val * 100)
                        if baseline_val else 0
                    )

            elif test_name in current_tests:
                test_comp["status"] = "new"
                comparison["summary"]["new_tests"] += 1
            else:
                test_comp["status"] = "removed"
                comparison["summary"]["removed_tests"] += 1

            comparison["test_comparisons"].append(test_comp)
            comparison["summary"]["total_tests"] += 1

        # Overall status
        if comparison["summary"]["degraded"] > 0:
            comparison["overall_status"] = "REGRESSION DETECTED"
        elif comparison["summary"]["improved"] > 0:
            comparison["overall_status"] = "IMPROVEMENTS FOUND"
        else:
            comparison["overall_status"] = "STABLE"

        return comparison

    def generate_report(self, test_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable test report.

        Args:
            test_result: Test results dictionary

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 60,
            "REGRESSION TEST REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Test Timestamp: {test_result.get('timestamp', 'N/A')}",
            "",
            "-" * 60,
            "SUMMARY",
            "-" * 60,
            f"Total Tests: {test_result['summary']['total']}",
            f"Passed: {test_result['summary']['passed']}",
            f"Failed: {test_result['summary']['failed']}",
            f"Skipped: {test_result['summary']['skipped']}",
            f"Duration: {test_result['summary']['total_duration']:.2f}s",
            "",
            "-" * 60,
            "TEST DETAILS",
            "-" * 60,
        ]

        for test in test_result.get("test_sequence", []):
            status_icon = "✓" if test["status"] == "passed" else "✗"
            report_lines.append(
                f"{status_icon} {test['name']}: {test['status'].upper()}"
            )
            report_lines.append(f"  Duration: {test['duration']:.2f}s")

            if test.get("metrics"):
                for key, value in test["metrics"].items():
                    report_lines.append(f"  {key}: {value}")

            if test.get("errors"):
                for error in test["errors"]:
                    report_lines.append(f"  ERROR: {error}")

            report_lines.append("")

        # Baseline comparison if available
        if self.baseline:
            report_lines.extend([
                "-" * 60,
                "BASELINE COMPARISON",
                "-" * 60,
            ])

            comparison = self.compare_results(test_result, self.baseline)
            report_lines.append(f"Overall Status: {comparison['overall_status']}")
            report_lines.append(f"Baseline: {comparison['baseline_timestamp']}")
            report_lines.append(f"Improved: {comparison['summary']['improved']}")
            report_lines.append(f"Degraded: {comparison['summary']['degraded']}")
            report_lines.append(f"Stable: {comparison['summary']['stable']}")

        report_lines.extend([
            "",
            "=" * 60,
            "END OF REPORT",
            "=" * 60,
        ])

        report_text = "\n".join(report_lines)

        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.results_dir, f"report_{timestamp}.txt")
        with open(report_path, 'w') as f:
            f.write(report_text)

        print(f"Report saved to {report_path}")

        return report_text

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Execute the complete regression test pipeline.

        Returns:
            Dictionary containing all pipeline results
        """
        print("=" * 60)
        print("STARTING REGRESSION TEST PIPELINE")
        print("=" * 60)

        pipeline_result = {
            "pipeline_start": datetime.now().isoformat(),
            "steps": {},
            "overall_status": "unknown"
        }

        # Step 1: Build
        print("\n[Step 1/4] Building...")
        build_success = self.build()
        pipeline_result["steps"]["build"] = {
            "success": build_success,
            "timestamp": datetime.now().isoformat()
        }

        if not build_success:
            pipeline_result["overall_status"] = "BUILD_FAILED"
            pipeline_result["pipeline_end"] = datetime.now().isoformat()
            return pipeline_result

        # Step 2: Run tests
        print("\n[Step 2/4] Running tests...")
        test_results = self.run_tests()
        pipeline_result["steps"]["tests"] = {
            "results": test_results,
            "timestamp": datetime.now().isoformat()
        }

        # Step 3: Compare with baseline if available
        if self.baseline:
            print("\n[Step 3/4] Comparing with baseline...")
            comparison = self.compare_results(test_results, self.baseline)
            pipeline_result["steps"]["comparison"] = {
                "result": comparison,
                "timestamp": datetime.now().isoformat()
            }
        else:
            pipeline_result["steps"]["comparison"] = {
                "result": None,
                "message": "No baseline loaded for comparison"
            }

        # Step 4: Generate report
        print("\n[Step 4/4] Generating report...")
        report = self.generate_report(test_results)
        pipeline_result["steps"]["report"] = {
            "path": None,  # Will be set by generate_report
            "timestamp": datetime.now().isoformat()
        }

        # Overall status
        if test_results["summary"]["failed"] > 0:
            pipeline_result["overall_status"] = "TESTS_FAILED"
        elif self.baseline:
            comp = pipeline_result["steps"]["comparison"]["result"]
            if comp and comp["summary"]["degraded"] > 0:
                pipeline_result["overall_status"] = "REGRESSION_DETECTED"
            else:
                pipeline_result["overall_status"] = "PASSED"
        else:
            pipeline_result["overall_status"] = "PASSED"

        pipeline_result["pipeline_end"] = datetime.now().isoformat()

        print("\n" + "=" * 60)
        print(f"PIPELINE COMPLETE - Status: {pipeline_result['overall_status']}")
        print("=" * 60)

        return pipeline_result


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Example configuration
    example_config = {
        "project_root": ".",
        "build_command": "make",
        "build_args": ["all"],
        "flash_command": "make",
        "flash_args": ["flash", "DEVICE_ID={device_id}"],
        "test_timeout": 300,
        "results_dir": "test_results",
        "test_sequence": [
            {"name": "power_on_test", "description": "Power-on self test", "timeout": 10},
            {"name": "memory_test", "description": "Memory integrity test", "timeout": 30},
            {"name": "sensor_calibration", "description": "Sensor calibration", "timeout": 60},
            {"name": "communication_test", "description": "Communication interface test", "timeout": 45},
            {"name": "motor_response_test", "description": "Motor response test", "timeout": 90},
        ]
    }

    # Save example config
    config_path = "regression_test_config.json"
    with open(config_path, 'w') as f:
        json.dump(example_config, f, indent=2)

    print(f"Example config saved to {config_path}")
    print("\nTo use this module:")
    print("""
    # Initialize tester
    tester = RegressionTester("config.json")

    # Load baseline (optional)
    tester.load_baseline("baseline_results.json")

    # Run full pipeline
    results = tester.run_full_pipeline()

    # Or run individual steps
    # tester.build()
    # tester.flash("COM3")
    # results = tester.run_tests()
    # report = tester.generate_report(results)
    """)
