from html.parser import HTMLParser
from urllib.request import urlopen
import json, time
from blinkpy.blinkpy import Blink
from blinkpy.auth import Auth

blink = Blink()
# https://pypi.org/project/blinkpy/
auth = Auth({"username": "admin@example.com", "password": "horsebatterystapler"}, no_prompt=False)
trusted_mac_addresses = ["aa:bb:cc:dd:ee:ff"]
blink.auth = auth
blink.start()

# all this shit below here is to parse my router's device list properly. i love proper object notation, and tried to do this without regex. ;p
in_table = False
this_device = []
row_name = ""
last_tag = ""
device_list = {}
class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        global in_table, this_device, row_name, last_tag, device_list
        if tag == "table":
            in_table = True
        if in_table:
            last_tag = tag
            # print("Encountered a start tag:", tag)

    def handle_endtag(self, tag):
        global in_table, this_device, row_name, last_tag, device_list
        if tag == "table":
            in_table = False
        if tag == "table" or tag == "hr":
            this_mac = None
            this_data = {}
            ipv6_addr = False
            ipv6_data = {}
            # print(this_device)
            for x, y in this_device:
                if this_mac == None:
                    if x == "MAC Address":
                        this_mac = y
                    else:
                        raise ValueError
                elif ipv6_addr != False:
                    if x == "Type":
                        ipv6_data[x] = y
                    if x == "Valid Lifetime":
                        ipv6_data[x] = y
                    if x == "Preferred Lifetime":
                        ipv6_data[x] = y
                        if "IPv6" not in this_data:
                            this_data["IPv6"] = {}
                        this_data["IPv6"][ipv6_addr] = ipv6_data
                        ipv6_addr = False
                        ipv6_data = {}
                elif x == "IPv6 Address":
                    ipv6_addr = y
                elif x == "Status":
                    this_data[x] = True if y == "on" else False
                elif x == "IPv4 Address / Name":
                    dat = y.split('\n / ', 1)
                    this_data["IPv4 Address"] = dat[0]
                    this_data["Name"] = dat[1]
                else:
                    this_data[x] = y
            # print(this_data)
            device_list[this_mac] = this_data
            # print("======= END DEVICE INFO =======")
            this_device = []
        # if in_table:
        #     print("Encountered an end tag :", tag)

    def handle_data(self, data):
        global in_table, this_device, row_name, last_tag, device_list
        data = data.strip()
        if in_table:
            # print("Encountered some data  :", data)
            if data != "":
                if last_tag == "th":
                    row_name = data
                elif last_tag == "td":
                    this_device.append((row_name, data))
                    # print(f'{row_name}: {data}')

parser = MyHTMLParser()

def get_devices():
    global parser, device_list
    parser.feed(urlopen('http://192.168.1.254/cgi-bin/devices.ha').read().decode())
    # print(f'look at how nice this json is: {json.dumps(device_list, indent=4)}')
    return(device_list)

def main():
    global trusted_mac_addresses
    last_arm_state = None
    while True:
        try:
            arm_state = True
            device_data = get_devices()
            for mac in trusted_mac_addresses:
                if mac in device_data:
                    # for each trusted mac address, if it's online set arm status to false, then break out of for-loop
                    if device_data[mac]["Status"]:
                        arm_state = False
                        break
            if arm_state != last_arm_state:
                print(f'Setting camera arm state to {arm_state}')
                # simply loop all cameras and arm/disarm them.
                for name, camera in blink.cameras.items():
                    blink.sync[name].arm = arm_state
                last_arm_state = arm_state
            time.sleep(5)
        except Exception as e:
            pass


if __name__ == '__main__':
    main()
