import asyncio
from kasa import Discover
import sys
from datetime import datetime
from dotenv import load_dotenv
import os

# Load the environment variables from .env file
load_dotenv()

STANDARD_VOLTAGE = 120.0  # Standard US voltage

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

        # Initialize counters for energy tracking
        total_energy = 0.0  # in watt-hours
        last_power = 0.0
        start_time = datetime.now()
        
        print("\nStarting power monitoring...")
        print("Press Ctrl+C to stop monitoring\n")
        print("Timestamp\t\tPower (W)\tCurrent (A)\tResistance (Ω)\tEnergy (Wh)\tRuntime")
        print("-" * 100)

        while True:
            await device.update()
            current_time = datetime.now()
            
            if device.has_emeter:
                emeter = device.modules.get("Energy")
                if emeter and hasattr(emeter, 'current_consumption'):
                    # Get power consumption
                    power = emeter.current_consumption or 0.0
                    
                    # Calculate estimated current (P = V * I, so I = P/V)
                    estimated_current = power / STANDARD_VOLTAGE if power > 0 else 0.0
                    
                    # Calculate resistance (R = V/I = V²/P)
                    # We use V²/P instead of V/I to avoid division by zero when current is very small
                    resistance = (STANDARD_VOLTAGE ** 2) / power if power > 1.0 else float('inf')
                    
                    # Calculate energy used since last reading
                    time_diff = (current_time - start_time).total_seconds() / 3600  # convert to hours
                    if last_power > 0:
                        # Use average power between readings for more accurate energy calculation
                        avg_power = (last_power + power) / 2
                        total_energy += (avg_power * interval / 3600)  # convert to watt-hours
                    
                    # Format runtime
                    runtime = current_time - start_time
                    hours = int(runtime.total_seconds() // 3600)
                    minutes = int((runtime.total_seconds() % 3600) // 60)
                    seconds = int(runtime.total_seconds() % 60)
                    runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    # Print the values
                    # Use "∞" for infinite resistance when power is very low
                    resistance_str = f"{resistance:8.1f}" if resistance != float('inf') else "    ∞    "
                    print(f"{current_time.strftime('%Y-%m-%d %H:%M:%S')}\t"
                          f"{power:8.2f}\t"
                          f"{estimated_current:8.3f}\t"
                          f"{resistance_str}\t"
                          f"{total_energy:8.2f}\t"
                          f"{runtime_str}")
                    
                    last_power = power
                else:
                    print("Device does not support current consumption reading.")
                    break
            else:
                print("Device does not have energy monitoring capabilities.")
                break

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        print("\nMonitoring stopped by user")
        if 'start_time' in locals():
            duration = (datetime.now() - start_time).total_seconds() / 3600  # hours
            print(f"\nMonitoring Summary:")
            print(f"Duration: {duration:.2f} hours")
            print(f"Total Energy Consumed: {total_energy:.2f} Wh")
            if duration > 0:
                print(f"Average Power: {(total_energy/duration):.2f} W")
                average_resistance = (STANDARD_VOLTAGE ** 2)/(total_energy/duration) if total_energy > 0 else float('inf')
                if average_resistance != float('inf'):
                    print(f"Average Resistance: {average_resistance:.1f} Ω")
                else:
                    print("Average Resistance: ∞ Ω")
                
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
    INTERVAL = 2
    
    # Validate environment variables
    if not all([HOST, USERNAME, PASSWORD]):
        print("Error: Missing required environment variables. Please check your .env file.")
        print("Required variables: KASA_HOST, KASA_USERNAME, KASA_PASSWORD")
        print("Optional variables: KASA_INTERVAL (defaults to 1)")
        sys.exit(1)
    
    try:
        await get_power_consumption(HOST, USERNAME, PASSWORD, INTERVAL)
    except KeyboardInterrupt:
        print("\nProgram terminated by user")

if __name__ == "__main__":
    asyncio.run(main())