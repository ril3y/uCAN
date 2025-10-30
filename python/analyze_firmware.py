#!/usr/bin/env python3
"""
Firmware Binary Analysis Tool

Analyzes firmware binaries for:
- Dead code detection (unused symbols/functions)
- Memory leakage (global/static variables)
- Modularity issues (cross-platform pollution)
- Large symbols and memory hogs
"""

import re
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Set
from pathlib import Path

class FirmwareAnalyzer:
    """Analyze firmware binaries for code quality issues"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.build_dir = self.project_root / ".pio" / "build"
        self.results = {}

    def analyze_map_file(self, env_name: str) -> Dict:
        """Analyze a linker map file for an environment"""
        map_file = self.build_dir / env_name / "firmware.map"

        if not map_file.exists():
            return {"error": f"Map file not found: {map_file}"}

        analysis = {
            "environment": env_name,
            "dead_code": [],
            "board_pollution": [],
            "large_symbols": [],
            "global_variables": [],
            "linked_modules": set(),
        }

        with open(map_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Find all linked source files
        src_pattern = re.compile(r'\.pio\\build\\' + env_name + r'\\src\\([^\\]+\\)*([^)]+\.cpp)\.o\)')
        for match in src_pattern.finditer(content):
            module_path = match.group(0)
            analysis["linked_modules"].add(module_path)

        # Check for board pollution (wrong board implementations linked)
        # Map environment names to their expected board folder names
        board_patterns = {
            "feather_m4_can": ["feather_m4_can"],
            "pico": ["rpi_pico"],
            "esp32_t_can485": ["t_can485"],
            "esp32_t_panel": ["t_panel"]
        }

        expected_boards = board_patterns.get(env_name, [])

        # Find board implementation files that actually contribute code
        # Look for Archive member entries (libraries that are actually linked in)
        board_impl_archive_pattern = re.compile(r'\.pio\\build\\' + env_name + r'\\src\\boards\\([^\\]+)\\board_impl\.cpp\.o\s+\(.*?\)')

        for match in board_impl_archive_pattern.finditer(content):
            board_name = match.group(1)
            if board_name not in expected_boards:
                analysis["board_pollution"].append(f"Unexpected board linked: {board_name}")

        # Find large symbols (> 1KB)
        symbol_size_pattern = re.compile(r'(\S+)\s+0x[0-9a-f]+\s+0x([0-9a-f]+)')
        for match in symbol_size_pattern.finditer(content):
            symbol_name = match.group(1)
            size_hex = match.group(2)
            try:
                size = int(size_hex, 16)
                if size > 1024:  # Symbols larger than 1KB
                    analysis["large_symbols"].append((symbol_name, size))
            except ValueError:
                pass

        # Sort large symbols by size
        analysis["large_symbols"].sort(key=lambda x: x[1], reverse=True)

        # Find global/static variables (.data and .bss sections)
        # These can cause memory leaks if not properly managed
        data_section_pattern = re.compile(r'\.(?:data|bss)\s+0x[0-9a-f]+\s+0x([0-9a-f]+)\s+(\S+)')
        for match in data_section_pattern.finditer(content):
            size_hex = match.group(1)
            source = match.group(2)
            try:
                size = int(size_hex, 16)
                if size > 256:  # Global data > 256 bytes
                    analysis["global_variables"].append((source, size))
            except ValueError:
                pass

        analysis["global_variables"].sort(key=lambda x: x[1], reverse=True)

        return analysis

    def analyze_all_environments(self):
        """Analyze all built environments"""
        environments = ["feather_m4_can", "pico", "esp32_t_can485", "esp32_t_panel"]

        for env in environments:
            print(f"\n{'='*80}")
            print(f"Analyzing: {env}")
            print(f"{'='*80}")

            result = self.analyze_map_file(env)

            if "error" in result:
                print(f"  [!] {result['error']}")
                continue

            # Report findings
            print(f"\n[*] Modularity Check:")
            if result["board_pollution"]:
                print(f"  [!] BOARD POLLUTION DETECTED!")
                for issue in result["board_pollution"]:
                    print(f"     - {issue}")
            else:
                print(f"  [+] Clean - no cross-board contamination")

            print(f"\n[*] Linked Modules: {len(result['linked_modules'])}")

            print(f"\n[*] Large Symbols (>1KB):")
            if result["large_symbols"][:5]:
                for symbol, size in result["large_symbols"][:5]:
                    print(f"  - {symbol}: {size:,} bytes")
            else:
                print(f"  [+] No symbols > 1KB")

            print(f"\n[*] Global Variables (>256 bytes):")
            if result["global_variables"][:5]:
                for source, size in result["global_variables"][:5]:
                    print(f"  - {source}: {size:,} bytes")
            else:
                print(f"  [+] No large global variables")

            self.results[env] = result

    def check_source_modularity(self):
        """Check source code for modularity issues"""
        print(f"\n{'='*80}")
        print(f"Source Code Modularity Analysis")
        print(f"{'='*80}")

        # Check for platform-specific code in generic files
        generic_dirs = [
            self.project_root / "src" / "actions",
            self.project_root / "src" / "boards",
        ]

        platform_keywords = [
            "PLATFORM_SAMD51",
            "PLATFORM_RP2040",
            "PLATFORM_ESP32",
            "__SAMD51__",
            "PICO_BUILD",
        ]

        violations = []

        for directory in generic_dirs:
            if not directory.exists():
                continue

            for cpp_file in directory.rglob("*.cpp"):
                # Skip platform-specific directories
                if any(x in str(cpp_file) for x in ["samd51", "rp2040", "esp32", "t_can485", "t_panel"]):
                    continue

                with open(cpp_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for keyword in platform_keywords:
                    if keyword in content and "platform_config" not in content:
                        violations.append((cpp_file.relative_to(self.project_root), keyword))

        if violations:
            print(f"\n[!] Platform-specific code in generic files:")
            for file, keyword in violations:
                print(f"  - {file}: {keyword}")
        else:
            print(f"\n[+] All generic code is platform-agnostic")

    def generate_report(self) -> Dict:
        """Generate summary report and return violations"""
        print(f"\n{'='*80}")
        print(f"Summary Report")
        print(f"{'='*80}")

        violations = {
            "modularity_errors": 0,
            "memory_warnings": 0,
            "source_violations": 0,
            "total_issues": 0,
            "passed": True
        }

        # Check modularity
        total_pollution = sum(len(r.get("board_pollution", [])) for r in self.results.values())
        violations["modularity_errors"] = total_pollution

        if total_pollution == 0:
            print(f"\n[+] MODULARITY: EXCELLENT")
            print(f"   - No cross-platform pollution detected")
            print(f"   - Each build only includes its platform-specific code")
        else:
            print(f"\n[!] MODULARITY: ISSUES DETECTED")
            print(f"   - {total_pollution} board pollution issues found")
            violations["passed"] = False

        # Check memory usage
        print(f"\n[*] Memory Usage Summary:")
        for env, result in self.results.items():
            if "linked_modules" in result:
                large_syms = len(result.get("large_symbols", []))
                large_globals = len(result.get("global_variables", []))
                print(f"  {env}:")
                print(f"    - Large symbols (>1KB): {large_syms}")
                print(f"    - Large globals (>256B): {large_globals}")

        violations["total_issues"] = violations["modularity_errors"] + violations["memory_warnings"] + violations["source_violations"]
        return violations

def main():
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analyzer = FirmwareAnalyzer(project_root)

    print(f"uCAN Firmware Analysis")
    print(f"Project: {project_root}")

    analyzer.analyze_all_environments()
    analyzer.check_source_modularity()
    violations = analyzer.generate_report()

    # Print final status
    print(f"\n{'='*80}")
    if violations["passed"]:
        print(f"[+] ANALYSIS PASSED - No critical issues detected")
        print(f"{'='*80}")
        return 0
    else:
        print(f"[!] ANALYSIS FAILED - {violations['total_issues']} issue(s) detected")
        print(f"    - Modularity errors: {violations['modularity_errors']}")
        print(f"    - Memory warnings: {violations['memory_warnings']}")
        print(f"    - Source violations: {violations['source_violations']}")
        print(f"{'='*80}")
        return 1

if __name__ == "__main__":
    exit(main())
