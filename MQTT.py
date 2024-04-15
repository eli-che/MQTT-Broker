# Created according to documentation of MQTT V5
# https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
# https://docs.python.org/3/library/socketserver.html

# Let's start by creating a TCP socket server
from enum import Enum
import socketserver

import threading

from clientreply import ClientConnection, connections, subscriptions

# Let's also import JSON and Time for retaining messages


lock = threading.Lock()


class MQTTtypes(Enum):
    EMPTY = 0
    CONNECT = 1
    CONNACK = 2
    PUBLISH = 3
    PUBACK = 4
    PUBREC = 5
    PUBREL = 6
    PUBCOMP = 7
    SUBSCRIBE = 8
    SUBACK = 9
    UNSUBSCRIBE = 10
    UNSUBACK = 11
    PINGREQ = 12
    PINGRESP = 13
    DISCONNECT = 14
    AUTH = 15


class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle_PINGREQ(self, conn):
        # Call the PINGREQ method on the ClientConnection instance
        conn.PINGREQ()

    def handle_PUBLISH(self, data, conn):
        # Call the publish method on the ClientConnection instance
        conn.publish(data)

    def handle_UNSUBSCRIBE(self, data, conn):
        # Call the publish method on the ClientConnection instance
        conn.unsubscribe(data)

    def handle_SUBSCRIBE(self, data, conn):
        conn.subscribe(data)

    def handle(self):
        # Handle incoming TCP packets
        print(
            "TCP connection recieved from ",
            self.client_address[0],
            ":",
            self.client_address[1],
        )
        try:
            while True:
                # retrieve the expected 2 bytes from the MQTT control packet
                data = self.request.recv(2)
                if not data:
                    # Connection closed by the remote host
                    print("Connection closed by remote host")
                    break

                if not data:
                    break

                # The first byte of each MQTT packet represents the control packet type and some control flags.
                # This byte is commonly referred to as the "fixed header."
                byte = data[0]
                # Since one byte has 8 bits and we need the first 4 bits to determine the purpose
                # Connect, Publish, Subcribe, etc.
                # Extract the first (upper) 4 bits
                MqttType = byte >> 4
                # Extract the last (lower) 4 bits
                MqttFlags = byte & 0x0F
                print("--------******************************--------")
                print(
                    "MQTT Fixed Header Type: %s (%s)" % (MqttType, MQTTtypes(MqttType))
                )
                
                # Should return MQTT PUBREL at first as acknowledgement of reciving the PUBREC from server.

                # Check what kind of MQTT header it is (connect, subscribe, publish, etc)

                match MQTTtypes(MqttType):
                    case MQTTtypes.CONNECT:
                        #Handle connection serverside
                        self.Connect_Handle(data)

                    case MQTTtypes.PINGREQ:
                        conn = ClientConnection(self.request, self.client_id)
                        self.handle_PINGREQ(conn)

                    case MQTTtypes.SUBSCRIBE:
                        conn = ClientConnection(self.request, self.client_id)
                        self.handle_SUBSCRIBE(data, conn)
    
                    case MQTTtypes.UNSUBSCRIBE:
                        conn = ClientConnection(self.request, self.client_id)
                        self.handle_UNSUBSCRIBE(data, conn)

                    case MQTTtypes.PUBLISH:
                        conn = ClientConnection(self.request, self.client_id)
                        self.handle_PUBLISH(data, conn)

                    case MQTTtypes.DISCONNECT:
                        #We will not bother to do anything with the disconnect packet payload data so we will just skip straight to closing the connection
                        #close the socket connection
                        print("Disconnecting client: ", self.client_id)
                        conn = ClientConnection(self.request, self.client_id)
                        with lock:
                            if conn.client_id in connections:
                                connections.pop(conn.client_id)
                                for topic in list(subscriptions.keys()):
                                    # Check if the client ID is in the current topic's list
                                    if self.client_id in subscriptions[topic]:
                                        subscriptions[topic].remove(self.client_id)

                                        # Optional: Remove the key if the list becomes empty
                                        if not subscriptions[topic]:
                                            del subscriptions[topic]
                        print("-----------------DISCONNECT END-----------------")

                    case _:
                        break

        except OSError as e:
            # Handle the specific error (10054)
            if e.errno == 10054:
                print("Connection closed by remote host")
                # Take appropriate actions such as closing the socket and attempting to reconnect
                #with lock:
                    #if conn.client_id in connections:
                        #connections.pop(conn.client_id)

                # ...
            else:
                # Handle other OSError cases
                print(f"OSError: {e}")
                with lock:
                    if conn.client_id in connections:
                        connections.pop(conn.client_id)
                        # conn.close()

    def Connect_Handle(self, data):
        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901036
        # The first two bytes of the variable header of the CONNECT packet contains the length of the variable header.
        incData = self.request.recv(data[1])
        # extract the first 6 bytes of the variable header
        ProtocolName = incData[:6]
        # Compare protocol name with MQTT to see if it is correct, if not raise error and disconnect client from server check documentation above for more info.
        if ProtocolName == b"\x00\x04MQTT":
            print("Correct protocol name")
        else:
            print("Incorrect protocol name")
            raise ProtocolError(f"Incorrect protocol name provided: {ProtocolName}")
        # extract the next byte of the variable header which is the protocol version number and check if it is correct, if not raise error and disconnect client from server check documentation above for more info.
        protocolVersion = incData[6]
        print("Protocol version: %s" % protocolVersion)

        if protocolVersion == 0x05:
            print("Supported protocol")
        else:
            print("Protocol partially Supported")

        # extract the next byte of the variable header which is the connect flags and check if it is correct, if not raise error and disconnect client from server check documentation above for more info.
        connectFlags = incData[7]
        # The Server MUST validate that the reserved flag in the CONNECT packet is set to 0 [MQTT-3.1.2-3].
        if connectFlags & 0x01:
            raise ProtocolError("Reserved flag not set to 0")

        cleanSessionFlag = connectFlags & 0x02
        # check if clean session flag is set to 1 or 0
        if not cleanSessionFlag:
            print("Clean session flag set to 0")
            # Keep alive is the next 2 bytes of the variable header (8 and 9))
            keepAlive = int.from_bytes(incData[8:10], byteorder="big")
            print("Keep Alive: %s seconds" % keepAlive)

        # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901059
        # The ClientID MUST be present and is the first field in the CONNECT packet Payload
        # The Client Identifier (Client ID) identifies the Client to the Server. Each Client connecting to the Server has a unique Client ID. The Client ID MUST be used by Clients and by Servers to identify state that they hold relating to this MQTT Session between the Client and the Server. The Client ID MUST be a UTF-8 Encoded String as defined in Section 1.5.3 [MQTT-3.1.3-1]. The Server MUST allow Client IDs which are between 1 and 23 UTF-8 encoded bytes in length, and that contain only the characters "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" [MQTT-3.1.3-2]. The Server MAY allow ClientId’s that contain more than 23 encoded bytes. The Server MAY allow zero-length ClientId. If the Server allows a zero-length ClientId, it MUST treat this as a special case and assign a unique ClientId to that Client. It MUST then process the CONNECT packet as if the Client had provided that unique ClientId [MQTT-3.1.3-3].
        # If the Server returns a Server Keep Alive on the CONNACK packet, the Client MUST use that value instead of the value it sent as the Keep Alive

        if protocolVersion == 0x04:
            # Extract the length of the Client ID (2 bytes)
            msb = incData[10]
            lsb = incData[11]
            client_id_length = (msb << 8) | lsb
            # Extract the Client ID based on the length
            client_id = incData[12 : 12 + client_id_length].decode("utf-8")

        else:
            propertiesLength = incData[10]
            # dataAfterProperties
            dataAfterProperties = incData[11 + propertiesLength :]
            msb = dataAfterProperties[0]
            lsb = dataAfterProperties[1]
            client_id_length = (msb << 8) | lsb
            client_id = dataAfterProperties[2 : 2 + client_id_length].decode("utf-8")

        # some weird character is added to the end of the client id so we need to remove it, depends on client used.
        self.client_id = client_id
        print("Client ID:", client_id)

        # Create a ClientConnection instance
        conn = ClientConnection(self.request, self.client_id)

        # Add the connection to the connections dictionary
        with lock:
            connections[conn.client_id] = conn

        # Send CONNACK to the client
        conn.connack()
        print("-----------------CONNECT END-----------------")
    #  if not cleanSessionFlag:
    #       keep_alive_thread = threading.Thread(target=send_pingreq_periodically, args=(conn, keepAlive))
    #       keep_alive_thread.start()


class Server(socketserver.ThreadingTCPServer):
    # multithread to be able to handle multiple clients synchronously
    # https://docs.python.org/3/library/socketserver.html for more info on socketserver and threading in python
    daemon_threads = True
    allow_reuse_address = True


def ServerInstance(host, port):
    # Create a server instance and start it
    with Server((host, port), MyTCPHandler) as server:
        try:
            print("-----------------STARTING SERVER-----------------")
            print("Starting server on ", host, ":", port)
            print("-----------------STARTING SERVER END-----------------")
            # Start the server and keep it running until keyboard interrupt is recieved (CTRL+C)
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
            print("Server Stopped")


ServerInstance("localhost", 8000)
