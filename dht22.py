
import time
import board
import adafruit_dht

# DHT22 connected to GPIO4 (physical pin 7)
dht = adafruit_dht.DHT22(board.D4)

try:
    while True:
        try:
            temperature = dht.temperature
            humidity = dht.humidity

            if temperature is not None and humidity is not None:
                print(f"Temperature: {temperature:.1f} °C")
                print(f"Humidity:    {humidity:.1f} %")
                print("-" * 30)

        except RuntimeError as error:
            # DHT22 readings occasionally fail; try again
            print(f"Reading error: {error}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nProgram stopped.")

finally:
    dht.exit()
