import socket
import struct
import time
import random

def encode_variable_byte_integer(number):
    encoded_bytes = b""
    while True:
        encoded_byte = number % 128
        number //= 128
        if number > 0:
            encoded_byte |= 128
        encoded_bytes += bytes([encoded_byte])
        if number <= 0:
            break
    return encoded_bytes

def encode_utf8_string(s):
    return len(s).to_bytes(2, byteorder="big") + s.encode("utf-8")

class MQTTClient:
    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.client_socket = None
        self.connected = False
    
    def handleConnack(self):
        connack_resp = self.client_socket.recv(4)
        if connack_resp[0] == 0x20 and connack_resp[1] == 0x02 and connack_resp[3] == 0x00:
            print("Connected to MQTT Broker")
        else:
            print("Failed to connect to MQTT Broker")
            
    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        packet_type = 0x10
        remaining_length = 10 + 2 + len(self.client_id)
        variable_header = b"\x00\x04MQTT\x05\x02\x00\x3C"  # Protocol Name, Level, Flags, Keep Alive
        payload = encode_utf8_string(self.client_id)
        packet = bytes([packet_type]) + encode_variable_byte_integer(remaining_length) + variable_header + payload
        self.client_socket.sendall(packet)
        self.connected = True
        self.handleConnack()

    def publish(self, topic, message):
        if self.connected:
            packet_type = 0x30
            topic_encoded = encode_utf8_string(topic)
            payload = message.encode('utf-8')
            remaining_length = len(topic_encoded) + len(payload)
            packet = bytes([packet_type]) + encode_variable_byte_integer(remaining_length) + topic_encoded + payload
            self.client_socket.sendall(packet)

    def disconnect(self):
        if self.connected:
            packet_type = 0xE0
            remaining_length = 0
            packet = bytes([packet_type]) + encode_variable_byte_integer(remaining_length)
            self.client_socket.close()
            self.connected = False


    def publish_temperature(self):
        temperature = random.randint(-20, 35)  #
        self.publish('temperature', f'Temperatur {temperature}C')

    def publish_humidity(self):
        humidity = random.randint(0, 100) 
        self.publish('humidity', f'Luftfuktighet {humidity}')

    def publish_wind_speed(self):
        wind_speed = random.uniform(0, 100)  
        self.publish('wind_speed', f'Vindhastighet {wind_speed:.2f} km/h')

    def publish_rainfall(self):
        rainfall = random.uniform(0, 50) 
        self.publish('rainfall', f'Regnmangd {rainfall:.2f} mm')

if __name__ == "__main__":
    host = 'localhost'
    port = 8000
    mqtt_client = MQTTClient(host, port, 'client123')
    mqtt_client.connect()

    try:
        while True:
            mqtt_client.publish_temperature()
            mqtt_client.publish_humidity()
            mqtt_client.publish_wind_speed()
            mqtt_client.publish_rainfall()
            time.sleep(1) 
    except KeyboardInterrupt:    
        mqtt_client.disconnect()
