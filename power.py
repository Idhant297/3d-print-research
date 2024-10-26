import asyncio
from kasa import Discover
import sys
from datetime import datetime

async def get_power_consumption(host: str, username: str, password: str, interval: int) -> None:
    try:
        device = await Discover.discover_single(
            host=host,
            username=username,
            password=password
        )
        
        if device is None:
            print(f"No device found at {host}")
            return

        while True:
            await device.update()
            
            if device.has_emeter:
                emeter = device.modules.get("Energy")
                if emeter and hasattr(emeter, 'current_consumption'):
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{current_time}] Current Consumption: {emeter.current_consumption:.2f} W")
                else:
                    print("Device does not support current consumption reading.")
                    break
            else:
                print("Device does not have energy monitoring capabilities.")
                break

            await asyncio.sleep(interval)

    except Exception as e:
        print(f"Error getting power consumption: {str(e)}", file=sys.stderr)
    finally:
        if 'device' in locals():
            await device.disconnect()
