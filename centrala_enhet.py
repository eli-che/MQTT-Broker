import socket
import threading



class MQTTConsole:
    def update_display(self, data):
        data = str(data)
        #iF DATA CONTAINS "temperature" THEN CLEAR THE CONSOLE
        if "temperature" in data:
            print("\033c", end="")
        #Set console color to blue
        print("\033[34m", end="")
        print(data)

    def run(self):
        central_unit_thread = threading.Thread(target=self.start_central_unit, daemon=True)
        central_unit_thread.start()
        central_unit_thread.join()
        

    def start_central_unit(self):
        central_unit = CentralUnit("localhost", 8000, "CentralUnit")
        central_unit.handlePublish(self.update_display)
  
        
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

class CentralUnit:
    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id  # Define client_id before calling sendConnectPacket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.sendConnectPacket()  # Now self.client_id is already defined
        
    def sendConnectPacket(self):
        packet_type = 0x10
        remaining_length = 10 + 2 + len(self.client_id)
        variable_header = b"\x00\x04MQTT\x05\x02\x00\x3C"  # Protocol Name, Level, Flags, Keep Alive
        payload = encode_utf8_string(self.client_id)
        packet = bytes([packet_type]) + encode_variable_byte_integer(remaining_length) + variable_header + payload
        self.socket.sendall(packet)
        self.handleConnack()

    def handleConnack(self):
        connack_resp = self.socket.recv(4)
        if connack_resp[0] == 0x20 and connack_resp[1] == 0x02 and connack_resp[3] == 0x00:
            print("Connected to MQTT Broker")
            self.subscribeToTopics()
        else:
            print("Failed to connect to MQTT Broker")

    def subscribeToTopics(self):
        topics = ["temperature", "humidity", "wind_speed", "rainfall"]
        for topic in topics:
            self.sendSubscribePacket(topic)

    def sendSubscribePacket(self, topic):
        packet = bytearray([0x82])  # Packet type: SUBSCRIBE
        packet_id = 1
        remain_len = 5 + len(topic)  # Remaining length
        packet += bytearray([remain_len, 0x00, packet_id])  # Remaining length, Packet ID
        packet += bytearray([0x00, len(topic)])  # Topic length
        packet += bytearray(topic.encode('utf-8'))  # Topic
        packet += bytearray([0x00])  # QoS level 0
        self.socket.send(packet)
        self.handleSuback(packet_id)

    def handleSuback(self, packet_id):
        suback_resp = self.socket.recv(5)
        if suback_resp[0] == 0x90:
            packet_id_high = suback_resp[2]
            packet_id_low = suback_resp[3]
            received_packet_id = (packet_id_high << 8) | packet_id_low
            if received_packet_id == packet_id and suback_resp[4] == 0x00:
                print(f"Subscribed to topic with packet ID {packet_id}")
            else:
                print(f"Failed to subscribe to topic with packet ID {packet_id}")
                
    def handlePublish(self, update_gui_callback):
        # Hantera inkommande PUBLISH-paket
        while True:
            try:
                publish_resp = self.socket.recv(1024)
                if publish_resp[0] == 0x30:  # PUBLISH Packet type
                    topic_len = (publish_resp[2] << 8) | publish_resp[3]
                    topic = publish_resp[4:4+topic_len].decode('utf-8')
                    message = publish_resp[4+topic_len:].decode('utf-8')
                    data = (f"Data received from {topic}: {message}")
                    update_gui_callback(data)
            except KeyboardInterrupt:
                print("Disconnecting from MQTT Broker")
                self.sendDisconnectPacket()
                self.socket.close()
                break
            
    def sendDisconnectPacket(self):
        # Skapa och skicka DISCONNECT-paket
        packet = bytearray([0xE0, 0x00])  # Packet type: DISCONNECT, Remaining Length: 0
        self.socket.send(packet)
        print("Sent DISCONNECT packet to MQTT Broker")

# Skapa och starta centralenheten

console = MQTTConsole()
console.run()