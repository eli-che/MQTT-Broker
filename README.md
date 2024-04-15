# MQTT-Broker
 
#Ett Internet protokoll baserat på MQTT dokumentation byggt från grunden och demonstrerat som en smart väderstation.

Syftet med 'Smart Väderstation med MQTT' är att skapa ett proof of concfept för en, tillförlitlig och interaktiv väderstation som använder MQTT-protokollet för att samla, överföra och visa väderdata i realtid.
Projektet består av flera nyckelkomponenter: sensorer som simulerar in väderdata, en MQTT-broker som fungerar som ett kommunikationscentrum, och en central enhet som visar data för användarna. Dessa delar arbetar ihop för att ge en omfattande översikt av det aktuella väderförhållandet.

MQTT-brokerns huvudsakliga funktion är att agera som en MQTT server som hantera meddelanden som skickas mellan de olika delarna av vårt väderstationssystem samt tar hand om retention och liknande. Den tar emot data från sensorerna, behandlar dessa data och skickar dem vidare till den centrala enheten för visning." Brokern är också kompatibel med MQTT V5 och tidigare versioner. Den kan även hantera externa mqtt clienter för att visa väder data.

Sensorerna fungerar som en simulering av olika sensorer i en väderstation. Dess huvuduppgift är att samla in data som temperatur, luftfuktighet och vindhastighet. Efter att ha samlat in dessa data, tar 'sensors.py' hand om att skicka dem till MQTT-brokern.

centrala_enhet.py är utformad för att fungera som en central enhet i vårt väderstationssystem. Dess primära funktion är att ta emot och visa väderdata som saimuleras av sensorerna och skickas via MQTT-brokern." När det mottar data, som till exempel temperatur eller luftfuktighet, visar det denna information i en konsol. Detta gör det möjligt för användare att se väderförhållandena i realtid."
