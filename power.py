import asyncio
from kasa import Discover
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import os
import csv

# Load the environment variables from .env file
load_dotenv()

STANDARD_VOLTAGE = 120.0  # Standard US voltage
ACTIVE_STATES = {'PREPARE', 'RUNNING', 'RESUME'}  # States where we should log data
TERMINAL_STATES = {'FAILED', 'FINISH', 'STOP'}  # States that end monitoring
PAUSE_STATES = {'PAUSE'}  # States where we should pause logging

async def get_power_consumption(host: str, username: str, password: str, interval: int) -> None:
    try:
        print(f"\nConnecting to device at {host}...")
        device = await Discover.discover_single(
            host=host,
            username=username,
            password=password
        )
        
        if device is None:
            print(f"No device found at {host}")
            return

        # Initial device update
        await device.update()
        
        print(f"\n== Device Info for {device.alias} ({device.model}) ==")
        print(f"Host: {device.host}")
        print(f"MAC Address: {device.mac}")

        # Initialize variables
        total_energy = 0.0  # in watt-hours
        last_power = 0.0
        start_time = None
        csv_filename = None
        current_state = None  # Initial state can be any, not just "IDLE"
        is_logging = False
        paused_duration = timedelta(0)  # Track total paused duration
        pause_start_time = None
        last_log_time = None  # Add this to track the last successful log time
        last_runtime = timedelta(0)  # Store the last known runtime before pause

        print("\nWaiting for printer to start...")
        
        while True:
            try:
                # Check the latest_message.json for gcode_state
                if os.path.exists('latest_message.json') and os.path.getsize('latest_message.json') > 0:
                    with open('latest_message.json', 'r') as json_file:
                        data = json.load(json_file)
                        print_data = data.get("print", {})
                        new_state = print_data.get("gcode_state", current_state or "IDLE")
                else:
                    new_state = current_state or "IDLE"

                # State transition handling
                if new_state != current_state:
                    print(f"\nState changed: {current_state} -> {new_state}")
                    current_state = new_state

                # Handle different states
                if current_state in ACTIVE_STATES:
                    if not is_logging:
                        # Start new logging session if not already logging
                        if start_time is None:
                            start_time = datetime.now()
                            csv_filename = os.path.join('data', f"power_data_{start_time.strftime('%Y-%m-%d_%H.%M')}.csv")
                            # Create CSV file if it doesn't exist
                            if not os.path.exists(csv_filename):
                                with open(csv_filename, 'w', newline='') as csvfile:
                                    csvwriter = csv.writer(csvfile)
                                    csvwriter.writerow(["Timestamp", "Power (W)", "Current (A)", "Resistance (Ω)", 
                                                      "Energy (Wh)", "Runtime", "State"])
                            
                            print(f"\nStarting power monitoring...")
                            print(f"Data will be saved to {csv_filename}")
                            print("Press Ctrl+C to stop monitoring\n")
                            print("Timestamp\t\tPower (W)\tCurrent (A)\tResistance (Ω)\tEnergy (Wh)\tRuntime\tState")
                            print("-" * 120)
                        
                        is_logging = True

                    # Log data while in active states
                    await device.update()
                    current_time = datetime.now()
                    
                    if device.has_emeter:
                        emeter = device.modules.get("Energy")
                        if emeter and hasattr(emeter, 'current_consumption'):
                            # Get power consumption
                            power = emeter.current_consumption or 0.0
                            
                            # Calculate metrics
                            estimated_current = power / STANDARD_VOLTAGE if power > 0 else 0.0
                            resistance = (STANDARD_VOLTAGE ** 2) / power if power > 1.0 else float('inf')
                            
                            # Calculate energy
                            if last_log_time:
                                time_diff = (current_time - last_log_time).total_seconds() / 3600
                                if last_power > 0:
                                    avg_power = (last_power + power) / 2
                                    total_energy += (avg_power * time_diff)
                            
                            # Format runtime - calculate only from actual running time
                            runtime = current_time - start_time - paused_duration
                            runtime_str = f"{int(runtime.total_seconds() // 3600):02d}:{int((runtime.total_seconds() % 3600) // 60):02d}:{int(runtime.total_seconds() % 60):02d}"
                            
                            # Format resistance
                            resistance_str = f"{resistance:8.1f}" if resistance != float('inf') else "    ∞    "
                            
                            # Print current values
                            print(f"{current_time.strftime('%Y-%m-%d %H:%M:%S')}\t"
                                  f"{power:8.2f}\t"
                                  f"{estimated_current:8.3f}\t"
                                  f"{resistance_str}\t"
                                  f"{total_energy:8.2f}\t"
                                  f"{runtime_str}\t"
                                  f"{current_state}")
                            
                            # Save to CSV
                            with open(csv_filename, 'a', newline='') as csvfile:
                                csvwriter = csv.writer(csvfile)
                                csvwriter.writerow([
                                    current_time.strftime('%Y-%m-%d %H:%M:%S'),
                                    f"{power:.2f}",
                                    f"{estimated_current:.3f}",
                                    resistance_str.strip(),
                                    f"{total_energy:.2f}",
                                    runtime_str,
                                    current_state
                                ])
                            
                            last_power = power
                            last_log_time = current_time

                elif current_state in PAUSE_STATES:
                    if is_logging:
                        is_logging = False
                        pause_start_time = datetime.now()
                        # Store the last runtime before pausing
                        last_runtime = current_time - start_time - paused_duration
                        print(f"\nLogging paused at {pause_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                elif current_state in TERMINAL_STATES:
                    if start_time is not None:
                        # Generate final summary
                        duration = (datetime.now() - start_time - paused_duration).total_seconds() / 3600
                        print(f"\nMonitoring Summary:")
                        print(f"Final State: {current_state}")
                        print(f"Duration: {duration:.2f} hours")
                        print(f"Total Energy Consumed: {total_energy:.2f} Wh")
                        if duration > 0:
                            avg_power = total_energy/duration
                            print(f"Average Power: {avg_power:.2f} W")
                            average_resistance = (STANDARD_VOLTAGE ** 2)/avg_power if avg_power > 0 else float('inf')
                            resistance_str = f"{average_resistance:.1f}" if average_resistance != float('inf') else "∞"
                            print(f"Average Resistance: {resistance_str} Ω")
                        
                        # Save summary to JSON
                        summary = {
                            "Final State": current_state,
                            "Duration": f"{duration:.2f} hours",
                            "Total Energy Consumed": f"{total_energy:.2f} Wh",
                            "Average Power": f"{(total_energy/duration):.2f} W" if duration > 0 else "N/A",
                            "Average Resistance": f"{resistance_str} ohms"
                        }
                        json_filename = csv_filename.replace('.csv', '_summary.json')
                        with open(json_filename, 'w') as jsonfile:
                            json.dump(summary, jsonfile, indent=4)
                        print(f"\nData saved to {csv_filename}")
                        print(f"Summary saved to {json_filename}")

                        # Reset monitoring variables
                        start_time = None
                        total_energy = 0.0
                        last_power = 0.0
                        csv_filename = None
                        is_logging = False
                        paused_duration = timedelta(0)
                        pause_start_time = None
                        last_log_time = None
                        print("\nWaiting for new print job...")

                if pause_start_time and current_state in ACTIVE_STATES:
                    # Resume from pause
                    pause_end_time = datetime.now()
                    paused_duration += pause_end_time - pause_start_time
                    # Adjust start_time to maintain consistent runtime
                    start_time = current_time - last_runtime - paused_duration
                    pause_start_time = None
                    is_logging = True  # Resume logging

                await asyncio.sleep(interval)

            except json.JSONDecodeError as e:
                print(f"Error reading status file: {e}")
                await asyncio.sleep(1)
                continue

    except asyncio.CancelledError:
        print("\nMonitoring stopped by user")
        if start_time:
            # Generate summary similar to normal completion
            duration = (datetime.now() - start_time - paused_duration).total_seconds() / 3600
            print(f"\nMonitoring Summary:")
            print(f"Final State: {current_state}")
            print(f"Duration: {duration:.2f} hours")
            print(f"Total Energy Consumed: {total_energy:.2f} Wh")
            if duration > 0:
                avg_power = total_energy/duration
                print(f"Average Power: {avg_power:.2f} W")
                average_resistance = (STANDARD_VOLTAGE ** 2)/avg_power if avg_power > 0 else float('inf')
                resistance_str = f"{average_resistance:.1f}" if average_resistance != float('inf') else "∞"
                print(f"Average Resistance: {resistance_str} Ω")

            summary = {
                "Final State": current_state,
                "Duration": f"{duration:.2f} hours",
                "Total Energy Consumed": f"{total_energy:.2f} Wh",
                "Average Power": f"{(total_energy/duration):.2f} W" if duration > 0 else "N/A",
                "Average Resistance": f"{resistance_str} ohms"
            }
            json_filename = csv_filename.replace('.csv', '_summary.json')
            with open(json_filename, 'w') as jsonfile:
                json.dump(summary, jsonfile, indent=4)
            print(f"\nData saved to {csv_filename}")
            print(f"Summary saved to {json_filename}")
                
    except Exception as e:
        print(f"\nError getting power consumption: {str(e)}", file=sys.stderr)
        raise
    finally:
        if 'device' in locals():
            await device.disconnect()

async def main():
    # Get values from environment variables
    HOST = os.getenv("KASA_HOST", "104.38.175.55")
    USERNAME = os.getenv("KASA_USERNAME")
    PASSWORD = os.getenv("KASA_PASSWORD")
    INTERVAL = 1 # in sec, kept to 1 don't change it
    
    # Validate environment variables
    if not all([HOST, USERNAME, PASSWORD]):
        print("Error: Missing required environment variables. Please check your .env file.")
        print("Required variables: KASA_HOST, KASA_USERNAME, KASA_PASSWORD")
        sys.exit(1)
    
    try:
        await get_power_consumption(HOST, USERNAME, PASSWORD, INTERVAL)
    except KeyboardInterrupt:
        print("\nProgram terminated by user")

if __name__ == "__main__":
    asyncio.run(main())