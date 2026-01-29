#!/usr/bin/env python3
"""
Mutation testing script for the Regal POS Backend
Uses mutmut to perform mutation testing on the codebase
"""

import subprocess
import sys
import os
from pathlib import Path


def run_mutation_tests():
    """
    Run mutation testing on the codebase
    """
    print("Starting mutation testing...")

    # Check if mutmut is installed
    try:
        result = subprocess.run(["mutmut", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("mutmut not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "mutmut"])
    except FileNotFoundError:
        print("mutmut not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "mutmut"])

    # Run mutation testing
    cmd = [
        "mutmut",
        "run",
        "--paths-to-mutate=src/",  # Only mutate source code
        "--backup=false",  # Don't create backup files
        "--runner=python -m pytest tests/unit/",  # Use pytest to run tests
        "--tests-dir=tests/"
    ]

    print(f"Running mutation testing with command: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\nMutation testing completed!")

        # Show results
        print("\nMutation testing results:")
        subprocess.run(["mutmut", "results"])

        # Show surviving mutations
        print("\nSurviving mutations (need to be fixed):")
        subprocess.run(["mutmut", "show", "survived"])

        return True
    else:
        print(f"Mutation testing failed with return code: {result.returncode}")
        return False


def run_cosmic_ray_testing():
    """
    Alternative mutation testing with Cosmic Ray
    """
    print("Starting Cosmic Ray mutation testing...")

    # Check if cosmic-ray is installed
    try:
        result = subprocess.run(["cosmic-ray", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("cosmic-ray not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "cosmic-ray"])
    except FileNotFoundError:
        print("cosmic-ray not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "cosmic-ray"])

    # Create a cosmic-ray configuration if it doesn't exist
    if not os.path.exists("cosmic-ray-config.json"):
        config_content = {
            "module-path": "src",
            "timeout": 50,
            "test-command": "python -m pytest tests/unit/"
        }
        import json
        with open("cosmic-ray-config.json", "w") as f:
            json.dump(config_content, f, indent=2)

    # Commands for cosmic ray
    workdir = "cr-workdir"

    # Initialize work directory
    init_cmd = ["cosmic-ray", "init", "cosmic-ray-config.json", workdir]
    print(f"Initializing Cosmic Ray with: {' '.join(init_cmd)}")
    init_result = subprocess.run(init_cmd)

    if init_result.returncode != 0:
        print("Failed to initialize Cosmic Ray")
        return False

    # Execute the mutation testing
    exec_cmd = ["cosmic-ray", "exec", workdir]
    print(f"Executing Cosmic Ray with: {' '.join(exec_cmd)}")
    exec_result = subprocess.run(exec_cmd)

    if exec_result.returncode != 0:
        print("Cosmic Ray execution failed")
        return False

    # Show results
    print("\nCosmic Ray results:")
    subprocess.run(["cosmic-ray", "report", workdir])

    return True


def main():
    """
    Main function to run mutation testing
    """
    print("Regal POS Backend - Mutation Testing")
    print("=" * 40)

    success = True

    # Run mutmut testing
    print("\n1. Running mutmut testing...")
    if not run_mutation_tests():
        success = False

    # Run cosmic ray testing
    print("\n2. Running Cosmic Ray testing...")
    if not run_cosmic_ray_testing():
        success = False

    print("\n" + "=" * 40)
    if success:
        print("Mutation testing completed successfully!")
        print("Check the results and address any surviving mutations.")
    else:
        print("Mutation testing had failures. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()