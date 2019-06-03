import os


def getHosts(data):
    hosts = {}
    for item in data:
        hosts[item[1]] = item[0]
    return hosts


if __name__ == "__main__":
    os.system("arp -v | grep ether | awk '{print $1,$3}' > data.txt")

    data = []

    with open("data.txt") as fp:
        for line in fp:
            line = line.split()
            data.append(line)

    hosts = getHosts(data)
    print(hosts)

    os.system("rm -f data.txt")
