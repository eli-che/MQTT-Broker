import json
import threading

lock = threading.Lock()

subscriptions = {}

connections = {}

retainedmessages = {}


def encode_variable_byte_integer(number):
    encoded_bytes = b""
    while True:
        encoded_byte = number % 128
        number //= 128
        # if there are more data to encode, set the top bit of this byte
        if number > 0:
            encoded_byte |= 128
        encoded_bytes += bytes([encoded_byte])
        if number <= 0:
            break
    return encoded_bytes

    # Helper functions
def encode_utf8_string(s):
    # Encodes a utf8 string with length at the beginning
    return len(s).to_bytes(2, byteorder="big") + s.encode("utf-8")

def int_to_bytes(n, length):
    # Converts an integer to bytes
    return n.to_bytes(length, byteorder="big")
    
class ClientConnection:
    def __init__(self, request, client_id):
        self.request = request
        self.client_id = client_id

    #  def close(self):
    # Close the TCP connection
    #    print("bana")
    #    self.request.send


    def PINGREQ(self):
        # Construct the PINGRE packet
        pingresp_packet = b"\xD0\x00"  # Control packet type: PINGREQ (0xC0)
        self.request.sendall(pingresp_packet)

    def connack(self):
        connack_response = b"\x20\x02\x00\x00"
        self.request.sendall(connack_response)

    def suback(self, packetid1, packetid2, return_codes):
        # Construct the SUBACK packet
        # 0x90 is the control packet type for SUBACK
        fixed_header = bytes([0x90, 0x03])
        # This is the fixed header for the SUBACK packet 3.9 SUBACK – Subscribe acknowledgement
        # after the fixed header we have the variable header which is the packet identifier
        # packet identifier is 2 bytes convert it for that in big endian format
        # variable_header = packet_identifier.to_bytes(2, byteorder='big')
        variable_header = bytes([packetid1, packetid2])
        # after the variable header we have the payload which is the return codes
        payload = bytes(return_codes)
        # construct the SUBACK packet
        suback_packet = fixed_header + variable_header + payload
        # print the suback packet to the console
        # create function to print the variable header and payload seperately
        # print(variable_header)

        #print("SUBACK: %s" % suback_packet)
        self.request.sendall(suback_packet)

    def unsuback(self, packetid1, packetid2, return_codes):
        # Construct the SUBACK packet
        # 0x90 is the control packet type for SUBACK
        fixed_header = bytes([0xB0, 0x03])
        # This is the fixed header for the UNSUBACK packet 3.9 UNSUBACK – UNSUB Subscribe acknowledgement
        # after the fixed header we have the variable header which is the packet identifier
        # packet identifier is 2 bytes convert it for that in big endian format
        # variable_header = packet_identifier.to_bytes(2, byteorder='big')
        variable_header = bytes([packetid1, packetid2])
        # after the variable header we have the payload which is the return codes
        payload = bytes(return_codes)
        # construct the UNSBUACK packet
        unsuback_packet = fixed_header + variable_header + payload
        # print the UNSUBACK packet to the console
        # create function to print the variable header and payload seperately
        # print(variable_header)

        #print("UNSUBACK: %s" % unsuback_packet)
        self.request.sendall(unsuback_packet)

    def server_publish(self, topic, message, packetIdentifier):

        # Fixed Header
        fixed_header = b"\x30"  # Assuming QoS 0, adjust if necessary

        # Variable Header
        variable_header = bytearray()
        variable_header.extend(encode_utf8_string(topic))
        variable_header.extend(int_to_bytes(packetIdentifier, 1))
        # variable_header.extend((0,))  # Additional byte

        # Payload
        payload = bytes(str(message), encoding="UTF-8")

        # Remaining Length calculation (variable header + payload)
        remaining_length = len(variable_header) + len(payload)
        remaining_length_encoded = encode_variable_byte_integer(remaining_length)

        # Construct the full packet
        publish_packet = bytearray()
        publish_packet += fixed_header
        publish_packet += remaining_length_encoded
        publish_packet += variable_header
        publish_packet += payload

        # Debug output
        # print("PUBLISH: %s" % publish_packet)
        # print("PUBLISH: ", repr(publish_packet))

        # Send to all clients subscribed to the topic
        with lock:
            for client_id, conn in connections.items():
                try:
                    if client_id in subscriptions.get(topic, []):
                        conn.request.sendall(publish_packet)
                except Exception as e:
                    print(f"Error sending to client {e}")
    
    def send_retained(self):
        # Iterate through all topics in the retainedmessages
        packetIdentifier = 0
        for topic, retained_message in retainedmessages.items():

            # Construct the PUBLISH packet for each retained message
            # Fixed Header
            fixed_header = b"\x30"  # Assuming QoS 0, adjust if necessary

            # Variable Header
            variable_header = bytearray()
            variable_header.extend(encode_utf8_string(topic))
            variable_header.extend(int_to_bytes(packetIdentifier, 1))
            # variable_header.extend((0,))  # Additional byte

            # Payload
            payload = bytes(str(retained_message), encoding="UTF-8")

            # Remaining Length calculation (variable header + payload)
            remaining_length = len(variable_header) + len(payload)
            remaining_length_encoded = encode_variable_byte_integer(remaining_length)

            # Construct the full packet
            publish_packet = bytearray()
            publish_packet += fixed_header
            publish_packet += remaining_length_encoded
            publish_packet += variable_header
            publish_packet += payload

            # Debug output
            # print("PUBLISH: %s" % publish_packet)
            # print("PUBLISH: ", repr(publish_packet))

            # Send to all clients subscribed to the topic
            with lock:
                for client_id, conn in connections.items():
                    try:
                        if client_id in subscriptions.get(topic, []):
                            conn.request.sendall(publish_packet)
                    except Exception as e:
                        print(f"Error sending to client {e}")

    def publish(self, data):
        # construct the publish packet and output the reciveed contents to the console
        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901093
        # Check if retain flag is set using bitwise AND "&" to check the least significant bit (right bit) of the first byte of the fixed header
        if data[0] & 1:
            retain = True
        else:
            retain = False

        # The second byte of the  header of the PUBLISH packet contains the remaning length of the variable header.
        variable_header_length = data[1]
        # Use the variable header length to receive the complete variable header
        incData = self.request.recv(variable_header_length)

        msb = incData[0]  # Assuming the MSB is the first byte of the variable header
        lsb = incData[1]  # Assuming the LSB is the second byte of the variable header
        # left shift the LSB into MSB, see below for illsutration
        # Original MSB: 1111 0000   (for illustration purposes, assuming an 8-bit MSB)
        # Original LSB: 0000 1111   (for illustration purposes, assuming an 8-bit LSB)
        # After left shift ZZ: 1111 0000 0000 0000   (MSB occupies bits 15 to 8, the left most bits illustrated)
        # Combined with LSB using bitwise OR "|"
        # 1111 0000 0000 1111   (Resulting 16-bit value)
        topic_length = (msb << 8) | lsb

        topic = incData[2 : 2 + topic_length]
        # packet_identifier = incData[2 + topic_length:4 + topic_length]
        # packetid = int.from_bytes(packet_identifier, byteorder='big')

        # The payload starts after the variable header
        payload = incData[2 + topic_length :]

        print("Topic: %s" % topic.decode("utf-8"))
        # print("Packet Identifier: %s" % packetid)
        print("Payload: %s" % payload.decode("utf-8"))

        messagedecoded = payload.decode("utf-8").replace("\x00", "")
        topicdecoded = topic.decode("utf-8")

        # delete any previously retained message for the topic
        if topicdecoded in retainedmessages:
            del retainedmessages[topicdecoded]
        # if retain flag is set, store the message as the new retained message for the topic
        if retain:
            retainedmessages[topicdecoded] = messagedecoded

        # Send to all clients subscribed to the topic
        self.server_publish(topicdecoded, messagedecoded, 0)

        publish_packet = b"\x40\x02\x00\x00"
        self.request.sendall(publish_packet)
        print("-----------------PUBLISH END-----------------")

    def subscribe(self, data):
        # Extract the variable header and payload from the SUBSCRIBE packet
        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901161

        # The first byte of the variable header of the SUBSCRIBE packet contains the length of the variable header.
        # DATA[1] represents the second byte of the SUBSCRIBE packet which contains Remaining Length field
        # This is the length of Variable Header plus the length of the Payload, encoded as a Variable Byte Integer.
        variable_header_length = data[1]
        # Use the variable header length to receive the complete variable header
        incData = self.request.recv(variable_header_length)
        msb = incData[0]  # Assuming the MSB is the first byte of the variable header
        lsb = incData[1]  # Assuming the LSB is the second byte of the variable header

        packetid1 = incData[0]
        packetid2 = incData[1]
        # left shift the LSB into MSB, see below for illsutration
        # Original MSB: 1111 0000   (for illustration purposes, assuming an 8-bit MSB)
        # Original LSB: 0000 1111   (for illustration purposes, assuming an 8-bit LSB)
        # After left shift ZZ: 1111 0000 0000 0000   (MSB occupies bits 15 to 8, the left most bits illustrated)
        # Combined with LSB using bitwise OR "|"
        # 1111 0000 0000 1111   (Resulting 16-bit value)
        packet_identifier = (msb << 8) | lsb
        # create a print statement to see the packet identifier value in the console for debugging purposes
        print("Packet Identifier: %s" % packet_identifier)

        # Extract next byte which is property length "The length of Properties in the SUBSCRIBE packet Variable Header encoded as a Variable Byte Integer."
        propertiesLength = incData[2]
        # properties = incData[3 : 3 + propertiesLength]

        # AFTER PROPERTIES IS WHERE WE HAVE THE PAYLOAD "TOPIC"
        # Which means the rest of the data the is left after. Which is everything after 3 + propertiesLength
        payload = incData[3 + propertiesLength :]

        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901168
        # the topic length is the first two bytes of the payload in the same MSB LSB format as above
        # to extract this we use the following code
        msb = payload[0]
        lsb = payload[1]
        topicLength = (msb << 8) | lsb

        # after that we have the topic name in byte 3 so we want to extract so our result is payload[2: 2 + topicLength]
        # farvirrande vissa program tycker topic barjor pa olika stallen?? barja pa 1:2+topiclength eller 2:2+topiclength
        # topic subscription data
        topic = payload[1 : 2 + topicLength]
        topicDecoded = topic.decode("utf-8")

        # if topicdecoded contaions a null character or \x then do topic = payload[2:2+topicLength] instead (Because of different program bug)
        if "'\\x0" in repr(topicDecoded):
            topic = payload[2 : 2 + topicLength]
            topicDecoded = topic.decode("utf-8")

        print("Topic: %s" % topicDecoded)

        # The Subscription Identifier is associated with any subscription created or modified as the result of this SUBSCRIBE packet.
        # If there is a Subscription Identifier, it is stored with the subscription.
        # If this property is not specified, then the absence of a Subscription Identifier is stored with the subscription.

        print(f"Client {self.client_id} subscribed to topic: {topicDecoded}")
        # Send a SUBACK response #PROBLEM HERE

        # convert topic to string
        # remove trailing null character from topic
        stringTopicDecoded = str(topicDecoded).replace("\x00", "")
        # convert self.client_id to string remove trailing null character from client id
        stringClientID = str(self.client_id).replace("\x00", "")

        # use lock here to prevent race condition, e.g if two clients subscribe to the same topic at the same time
        with lock:
            if stringTopicDecoded not in subscriptions.keys():
                subscriptions[stringTopicDecoded] = [stringClientID]
            else:
                if stringClientID not in subscriptions[stringTopicDecoded]:
                    subscriptions[stringTopicDecoded].append(stringClientID)
        # connections[self.clientIdentifier].SUBACK(packetIdentifier, 0)

        print(subscriptions)

        return_codes = [0x00]  # 0 is default for qos 0
        self.suback(packetid1, packetid2, return_codes)

        # Send retained messages
        self.send_retained()

        print("-----------------SUBSCRIBE END-----------------")

    def unsubscribe(self, data):

        variable_header_length = data[1]
        # Use the variable header length to receive the complete variable header
        incData = self.request.recv(variable_header_length)
        msb = incData[0]  # Assuming the MSB is the first byte of the variable header
        lsb = incData[1]  # Assuming the LSB is the second byte of the variable header
        packetid1 = incData[0]
        packetid2 = incData[1]
        # left shift the LSB into MSB, see below for illsutration
        # Original MSB: 1111 0000   (for illustration purposes, assuming an 8-bit MSB)
        # Original LSB: 0000 1111   (for illustration purposes, assuming an 8-bit LSB)
        # After left shift ZZ: 1111 0000 0000 0000   (MSB occupies bits 15 to 8, the left most bits illustrated)
        # Combined with LSB using bitwise OR "|"
        # 1111 0000 0000 1111   (Resulting 16-bit value)
        packet_identifier = (msb << 8) | lsb
        # create a print statement to see the packet identifier value in the console for debugging purposes
        print("Packet Identifier: %s" % packet_identifier)

        # Extract next byte which is property length "The length of Properties in the SUBSCRIBE packet Variable Header encoded as a Variable Byte Integer."
        propertiesLength = incData[2]
        properties = incData[3 : 3 + propertiesLength]

        # AFTER PROPERTIES IS WHERE WE HAVE THE PAYLOAD "TOPIC"
        # Which means the rest of the data the is left after. Which is after 3 + propertiesLength
        payload = incData[3 + propertiesLength :]

        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901168
        # the topic length is the first two bytes of the payload in the same MSB LSB format as above
        # to extract this we use the following code
        msb = payload[0]
        lsb = payload[1]
        topicLength = (msb << 8) | lsb

        # after that we have the topic name in byte 3 so we want to extract so our result is payload[2: 2 + topicLength]
        # farvirrande vissa program tycker topic barjor pa olika stallen?? barja pa 1:2+topiclength eller 2:2+topiclength
        # topic subscription data
        topic = payload[2 : 2 + topicLength]
        topicDecoded = topic.decode("utf-8")

        print("Topic: %s" % topicDecoded)

        # The Subscription Identifier is associated with any subscription created or modified as the result of this SUBSCRIBE packet.
        # If there is a Subscription Identifier, it is stored with the subscription.
        # If this property is not specified, then the absence of a Subscription Identifier is stored with the subscription.

        print(f"Client {self.client_id} unsubscribed from topic: {topicDecoded}")

        print(repr(topicDecoded))

        # lock here to prevent race condition
        with lock:
            if topicDecoded in subscriptions:
                # Check if the topic exists in subscriptions
                if self.client_id in subscriptions[topicDecoded]:
                    # Check if the client ID is in the list of clients for that topic
                    subscriptions[topicDecoded].remove(self.client_id)
                    print(f"Removed {self.client_id} from {topicDecoded}")
                    if not subscriptions[topicDecoded]:
                        del subscriptions[topicDecoded]
                else:
                    print(f"{self.client_id} not found in {topicDecoded}")
            else:
                print(f"{topicDecoded} not found in subscriptions")

        return_codes = [0x00]  # 0 is default for success
        self.suback(packetid1, packetid2, return_codes)

        print("-----------------UNSUBSCRIBE-----------------")
